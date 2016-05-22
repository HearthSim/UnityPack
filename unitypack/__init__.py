import os
import json
import logging
import lzma
from binascii import hexlify
from io import BytesIO
from urllib.parse import urlparse
from uuid import UUID
from . import engine as UnityEngine
from .enums import RuntimePlatform
from .utils import BinaryReader


__author__ = "Jerome Leclanche"
__email__ = "jerome@leclan.ch"
__version__ = "0.4"


SIGNATURE_WEB = "UnityWeb"
SIGNATURE_RAW = "UnityRaw"


def get_asset(name):
	return os.path.join(os.path.dirname(__file__), name)


with open(get_asset("strings.dat"), "rb") as f:
	STRINGS_DAT = f.read()


with open(get_asset("classes.json"), "r") as f:
	UNITY_CLASSES = json.load(f)


def UnityClass(i):
	return UNITY_CLASSES.get(str(i), "<Unknown #%i>" % (i))


def load_object(type, obj):
	clsname = type.type
	if hasattr(UnityEngine, clsname):
		obj = getattr(UnityEngine, clsname)(obj)

	return obj


class TypeTree:
	NULL = "(null)"

	def __init__(self, format):
		self.children = []
		self.version = 0
		self.is_array = False
		self.size = 0
		self.index = 0
		self.flags = 0
		self.type = self.NULL
		self.name = self.NULL
		self.format = format

	def __repr__(self):
		return "<%s %s (size=%r, index=%r, is_array=%r, flags=%r)>" % (
			self.type, self.name, self.size, self.index, self.is_array, self.flags
		)

	@property
	def post_align(self):
		return bool(self.flags & 0x4000)

	def load(self, buf):
		if self.format == 10 or self.format >= 12:
			self.load_blob(buf)
		else:
			self.load_old(buf)

	def load_old(self, buf):
		self.type = buf.read_string()
		self.name = buf.read_string()
		self.size = buf.read_int()
		self.index = buf.read_int()
		self.is_array = bool(buf.read_int())
		self.version = buf.read_int()
		self.flags = buf.read_int()

		num_fields = buf.read_int()
		for i in range(num_fields):
			tree = TypeTree(self.format)
			tree.load(buf)
			self.children.append(tree)

	def load_blob(self, buf):
		num_nodes = buf.read_uint()
		self.buffer_bytes = buf.read_uint()
		node_data = BytesIO(buf.read(24 * num_nodes))
		self.data = buf.read(self.buffer_bytes)

		parents = [self]

		buf = BinaryReader(node_data)

		for i in range(num_nodes):
			version = buf.read_int16()
			depth = buf.read_byte()

			if depth == 0:
				curr = self
			else:
				while len(parents) > depth:
					parents.pop()
				curr = TypeTree(self.format)
				parents[-1].children.append(curr)
				parents.append(curr)

			curr.version = version
			curr.is_array = buf.read_byte()
			curr.type = self.get_string(buf.read_int())
			curr.name = self.get_string(buf.read_int())
			curr.size = buf.read_int()
			curr.index = buf.read_uint()
			curr.flags = buf.read_int()

	def get_string(self, offset):
		if offset < 0:
			offset &= 0x7fffffff
			data = STRINGS_DAT
		elif offset < self.buffer_bytes:
			data = self.data
		else:
			return self.NULL
		return data[offset:].partition(b"\0")[0].decode("utf-8")


class TypeMetadata:
	default_instance = None

	@classmethod
	def default(cls, asset):
		if not cls.default_instance:
			cls.default_instance = cls(asset)
			with open(get_asset("structs.dat"), "rb") as f:
				cls.default_instance.load(BinaryReader(f), format=15)
		return cls.default_instance

	def __init__(self, asset):
		self.type_trees = {}
		self.hashes = {}
		self.asset = asset

	def load(self, buf, format=None):
		if format is None:
			format = self.asset.format
		offset = buf.tell()
		self.generator_version = buf.read_string()
		self.target_platform = RuntimePlatform(buf.read_uint())

		if format >= 13:
			self.has_type_trees = buf.read_boolean()
			self.num_types = buf.read_int()

			for i in range(self.num_types):
				class_id = buf.read_int()
				if class_id < 0:
					hash = buf.read(0x20)
				else:
					hash = buf.read(0x10)

				self.hashes[class_id] = hash

				if self.has_type_trees:
					tree = TypeTree(format)
					tree.load(buf)
					self.type_trees[class_id] = tree

		else:
			num_fields = buf.read_int()
			for i in range(num_fields):
				class_id = buf.read_int()
				tree = TypeTree(format)
				tree.load(buf)
				self.type_trees[class_id] = tree


class ObjectInfo:
	def __init__(self, asset):
		self.asset = asset

	def __repr__(self):
		return "<%s %i>" % (self.type, self.class_id)

	@property
	def type(self):
		if self.type_id > 0:
			return UnityClass(self.type_id)
		elif self.type_id not in self.asset.typenames:
			script = self.read()["m_Script"]
			if script:
				try:
					typename = script.resolve()["m_ClassName"]
				except NotImplementedError:
					typename = script.type.type[5:-1]  # Capture type name in PPtr<...>
			else:
				typename = self.asset.tree.type_trees[-150].type
			self.asset.typenames[self.type_id] = typename
		return self.asset.typenames[self.type_id]

	@property
	def type_tree(self):
		if self.type_id < 0:
			type_trees = self.asset.tree.type_trees
			if self.type_id in type_trees:
				return type_trees[self.type_id]
			elif self.class_id in type_trees:
				return type_trees[self.class_id]
			return TypeMetadata.default(self.asset).type_trees[self.class_id]
		return self.asset.types[self.type_id]

	def load(self, buf):
		self.path_id = self.read_id(buf)
		self.data_offset = buf.read_uint() + self.asset.data_offset
		self.size = buf.read_uint()
		self.type_id = buf.read_int()
		self.class_id = buf.read_int16()

		if self.asset.format <= 10:
			self.is_destroyed = bool(buf.read_int16())
		elif self.asset.format >= 11:
			self.unk0 = buf.read_int16()

			if self.asset.format >= 15:
				self.unk1 = buf.read_byte()

	def read_id(self, buf):
		if self.asset.long_object_ids:
			return buf.read_int64()
		else:
			return self.asset.read_id(buf)

	def read(self):
		buf = BinaryReader(self.asset.data)
		buf.seek(self.data_offset)
		return self.read_value(self.type_tree, buf)

	def read_value(self, type, buf):
		align = False
		t = type.type
		first_child = type.children[0] if type.children else TypeTree(self.asset.format)
		if t == "bool":
			result = buf.read_boolean()
		elif t == "UInt8":
			result = buf.read_byte()
		elif t == "SInt16":
			result = buf.read_int16()
		elif t == "UInt16":
			result = buf.read_uint16()
		elif t == "SInt64":
			result = buf.read_int64()
		elif t == "UInt64":
			result = buf.read_int64()
		elif t in ("UInt32", "unsigned int"):
			result = buf.read_uint()
		elif t in ("SInt32", "int"):
			result = buf.read_int()
		elif t == "float":
			buf.align()
			result = buf.read_float()
		elif t == "string":
			size = buf.read_uint()
			result = buf.read_string(size)
			align = type.children[0].post_align
		else:
			if type.is_array:
				first_child = type

			if t.startswith("PPtr<"):
				result = ObjectPointer(type, self.asset)
				result.load(buf)
				if not result:
					result = None

			elif first_child and first_child.is_array:
				align = first_child.post_align
				size = buf.read_uint()
				array_type = first_child.children[1]
				if array_type.type in ("char", "UInt8"):
					result = buf.read(size)
				else:
					result = []
					for i in range(size):
						result.append(self.read_value(array_type, buf))
			else:
				result = {}

				for child in type.children:
					result[child.name] = self.read_value(child, buf)

				result = load_object(type, result)
				if t == "StreamedResource":
					if self.asset.bundle:
						result.asset = self.asset.bundle.environment.get_asset(result.source)
					else:
						logging.warning("StreamedResource not available without bundle")
						result.asset = None

		if align or type.post_align:
			buf.align()

		return result


class ObjectPointer:
	def __init__(self, type, asset):
		self.type = type
		self.source_asset = asset

	def __bool__(self):
		return not (self.file_id == 0 and self.path_id == 0)

	def load(self, buf):
		self.file_id = buf.read_int()
		self.path_id = self.source_asset.read_id(buf)

	def __repr__(self):
		return "%s(file_id=%r, path_id=%r)" % (
			self.__class__.__name__, self.file_id, self.path_id
		)

	@property
	def asset(self):
		ret = self.source_asset.asset_refs[self.file_id]
		if isinstance(ret, AssetRef):
			ret = ret.resolve()
		return ret

	@property
	def object(self):
		return self.asset.objects[self.path_id]

	def resolve(self):
		return self.object.read()


class Asset:
	@classmethod
	def from_bundle(cls, bundle, buf):
		ret = cls()
		offset = buf.tell()
		if not bundle.compressed:
			ret.name = buf.read_string()
			header_size = buf.read_uint()
			size = buf.read_uint()
		else:
			header_size = bundle.asset_header_size

		# FIXME: this offset needs to be explored more
		ofs = buf.tell()
		if bundle.compressed:
			dec = lzma.LZMADecompressor()
			data = dec.decompress(buf.read())
			data = BytesIO(data[header_size:])
		else:
			if ret.is_resource:
				buf.seek(offset + header_size - 4 - len(ret.name))
			else:
				buf.seek(offset + header_size - 4)
			data = BytesIO(buf.read())
		ret.data = BinaryReader(data, endian=">")
		buf.seek(ofs)
		ret.bundle = bundle
		return ret

	@classmethod
	def from_file(cls, file):
		ret = cls()
		ret.name = file.name
		ret.data = BinaryReader(BytesIO(file.read()), endian=">")
		ret.load(ret.data)
		return ret

	def __init__(self):
		self.objects = {}
		self.adds = []
		self.asset_refs = [self]
		self.types = {}
		self.typenames = {}
		self.bundle = None
		self.name = ""
		self.long_object_ids = False

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.name)

	@property
	def is_resource(self):
		return self.name.endswith(".resource")

	def load(self, buf):
		self.metadata_size = buf.read_uint()
		self.file_size = buf.read_uint()
		self.format = buf.read_uint()
		self.data_offset = buf.read_uint()

		if self.format >= 9:
			self.endianness = buf.read_uint()
			if self.endianness == 0:
				buf.endian = "<"

		self.tree = TypeMetadata(self)
		self.tree.load(buf)

		if 7 <= self.format <= 13:
			self.long_object_ids = bool(buf.read_uint())

		num_objects = buf.read_uint()
		for i in range(num_objects):
			if self.format >= 14:
				buf.align()
			obj = ObjectInfo(self)
			obj.load(buf)
			self.register_object(obj)

		if self.format >= 11:
			num_adds = buf.read_uint()
			for i in range(num_adds):
				if self.format >= 14:
					buf.align()
				id = self.read_id(buf)
				self.adds.append((id, buf.read_int()))

		if self.format >= 6:
			num_refs = buf.read_uint()
			for i in range(num_refs):
				ref = AssetRef(self)
				ref.load(buf)
				self.asset_refs.append(ref)

		unk_string = buf.read_string()
		assert not unk_string, repr(unk_string)

	def read_id(self, buf):
		if self.format >= 14:
			return buf.read_int64()
		else:
			return buf.read_int()

	def register_object(self, obj):
		if obj.type_id in self.tree.type_trees:
			self.types[obj.type_id] = self.tree.type_trees[obj.type_id]
		elif obj.type_id not in self.types:
			trees = TypeMetadata.default(self).type_trees
			if obj.class_id in trees:
				self.types[obj.type_id] = trees[obj.class_id]
			else:
				logging.warning("%r absent from structs.dat", obj.class_id)
				self.types[obj.type_id] = None

		if obj.path_id in self.objects:
			raise ValueError("Duplicate asset object: %r (path_id=%r)" % (obj, obj.path_id))

		self.objects[obj.path_id] = obj

	def pretty(self):
		ret = []
		for id, tree in self.tree.type_trees.items():
			ret.append("%i:" % (id))
			for child in tree.children:
				ret.append("\t" + repr(child))
		return "\n".join(ret)


class AssetRef:
	def __init__(self, source):
		self.source = source

	def load(self, buf):
		self.asset_path = buf.read_string()
		self.guid = UUID(hexlify(buf.read(16)).decode("utf-8"))
		self.type = buf.read_int()
		self.file_path = buf.read_string()
		self.asset = None

	def resolve(self):
		return self.source.bundle.environment.get_asset(self.file_path)

	def __repr__(self):
		return "<%s (asset_path=%r, guid=%r, type=%r, file_path=%r)>" % (
			self.__class__.__name__, self.asset_path, self.guid, self.type, self.file_path
		)


class AssetBundle:
	def __init__(self, environment):
		self.environment = environment
		self.assets = []

	@property
	def compressed(self):
		return self.signature == SIGNATURE_WEB

	def load(self, file):
		buf = BinaryReader(file, endian=">")
		self.path = file.name

		self.signature = buf.read_string()
		self.format_version = buf.read_int()
		self.unity_version = buf.read_string()
		self.generator_version = buf.read_string()
		self.file_size = buf.read_uint()
		self.header_size = buf.read_int()

		self.file_count = buf.read_int()
		self.bundle_count = buf.read_int()

		if self.format_version >= 2:
			self.bundle_size = buf.read_uint()  # without header_size

			if self.format_version >= 3:
				self.uncompressed_bundle_size = buf.read_uint()  # without header_size

		if self.header_size >= 60:
			self.compressed_file_size = buf.read_uint()  # with header_size
			self.asset_header_size = buf.read_uint()

		assert self.signature in (SIGNATURE_RAW, SIGNATURE_WEB)

		_ = buf.read_int()
		_ = buf.read_byte()
		self.name = buf.read_string()

		# Preload assets
		buf.seek(self.header_size)
		if not self.compressed:
			self.num_assets = buf.read_int()
		else:
			self.num_assets = 1
		for i in range(self.num_assets):
			asset = Asset.from_bundle(self, buf)
			if not asset.is_resource:
				asset.load(asset.data)
			self.assets.append(asset)


class UnityEnvironment:
	def __init__(self):
		self.bundles = {}

	def load(self, file):
		for bundle in self.bundles.values():
			if os.path.abspath(file.name) == os.path.abspath(bundle.path):
				return bundle
		ret = AssetBundle(self)
		ret.load(file)
		self.bundles[ret.name.lower()] = ret
		return ret

	def discover(self, name):
		for bundle in list(self.bundles.values()):
			dirname = os.path.dirname(os.path.abspath(bundle.path))
			for filename in os.listdir(dirname):
				basename = os.path.splitext(os.path.basename(filename))[0]
				if name.lower() == "cab-" + basename.lower():
					with open(os.path.join(dirname, filename), "rb") as f:
						self.load(f)

	def get_asset(self, url):
		if not url:
			return None
		u = urlparse(url)
		assert u.scheme == "archive"

		archive, name = os.path.split(u.path.lstrip("/").lower())

		if archive not in self.bundles:
			self.discover(archive)

			# Still didn't find it? Give up...
			if archive not in self.bundles:
				raise NotImplementedError("Cannot find %r in %r" % (archive, self.bundles))

		bundle = self.bundles[archive]

		for asset in bundle.assets:
			if asset.name.lower() == name:
				return asset
		raise KeyError("No such asset: %r" % (name))


def load(file, env=None):
	if env is None:
		env = UnityEnvironment()
	return env.load(file)
