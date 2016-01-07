import os
import json
from binascii import hexlify
from io import BytesIO
from uuid import UUID
from .audioclip import AudioClip
from .textasset import TextAsset, Shader
from .texture2d import Texture2D
from .utils import BinaryReader


SIGNATURE_WEB = "UnityWeb"
SIGNATURE_RAW = "UnityRaw"


def get_asset(name):
	return os.path.join(os.path.dirname(__file__), name)


with open(get_asset("strings.dat"), "rb") as f:
	STRINGS_DAT = f.read()


with open(get_asset("classes.json"), "r") as f:
	UNITY_CLASSES = json.load(f)


def UnityClass(i):
	return UNITY_CLASSES[str(i)]


class TypeTree:
	NULL = "(null)"

	def __init__(self):
		self.children = []
		self.version = 0
		self.is_array = False
		self.size = 0
		self.index = 0
		self.flags = 0
		self.type = self.NULL
		self.name = self.NULL

	def __repr__(self):
		return "<%s %s (size=%r, index=%r, is_array=%r, flags=%r)>" % (
			self.type, self.name, self.size, self.index, self.is_array, self.flags
		)

	@property
	def post_align(self):
		return self.flags & 0x4000

	def load_blob(self, buf):
		self.num_nodes = buf.read_uint()
		self.buffer_bytes = buf.read_uint()
		node_data = BytesIO(buf.read(24 * self.num_nodes))
		self.data = buf.read(self.buffer_bytes)

		parents = [self]

		buf = BinaryReader(node_data)

		for i in range(self.num_nodes):
			version = buf.read_int16()
			depth = buf.read_byte()
			is_array = buf.read_byte()
			type_offset = buf.read_int()
			name_offset = buf.read_int()
			size = buf.read_int()
			index = buf.read_uint()
			flags = buf.read_int()

			type = self.get_string(type_offset)
			name = self.get_string(name_offset)

			if depth == 0:
				curr = self
			else:
				while len(parents) > depth:
					parents.pop()
				curr = TypeTree()
				parents[-1].children.append(curr)
				parents.append(curr)

			curr.type = type
			curr.name = name
			curr.size = size
			curr.index = index
			curr.is_array = is_array
			curr.version = version
			curr.flags = flags

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
	def default(cls):
		if not cls.default_instance:
			cls.default_instance = cls()
			with open(get_asset("structs.dat"), "rb") as f:
				cls.default_instance.load(BinaryReader(f))
		return cls.default_instance

	def __init__(self):
		self.type_trees = {}
		self.hashes = {}

	def load(self, buf):
		offset = buf.tell()
		self.generator_version = buf.read_string()
		self.target_platform = buf.read_uint()

		assert self.target_platform == 5  # Windows. RuntimePlatform?

		# if format >= 13
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
				tree = TypeTree()
				tree.load_blob(buf)
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
		else:
			return "<N/A>"

	def load(self, buf):
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

	def read(self):
		type = self.asset.types[self.type_id]
		buf = BinaryReader(self.asset.data)
		buf.seek(self.data_offset)
		return self.read_value(type, buf)

	def read_value(self, type, buf):
		align = False
		t = type.type
		first_child = type.children[0] if type.children else TypeTree()
		if t == "bool":
			result = buf.read_boolean()
		elif t == "UInt8":
			result = buf.read_byte()
		elif t == "UInt16":
			result = buf.read_int16()
		elif t == "UInt64":
			result = buf.read_int64()
		elif t == "unsigned int":
			result = buf.read_uint()
		elif t == "int":
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
				file_id = buf.read_int()
				if self.asset.format >= 14:
					path_id = buf.read_int64()
				else:
					path_id = buf.read_int()

				if file_id == 0:
					other = self.asset
				else:
					other = self.asset.asset_refs[file_id - 1].asset

				if path_id:
					result = {"_type": "Class", "classAsset": other, "classPathId": path_id}
				else:
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

				if t == "AudioClip":
					result = AudioClip(result)
				elif t == "TextAsset":
					result = TextAsset(result)
				elif t == "Shader":
					result = Shader(result)
				elif t == "Texture2D":
					result = Texture2D(result)

		if align or type.post_align:
			buf.align()

		return result


class Asset:
	def __init__(self):
		self.objects = {}
		self.adds = []
		self.asset_refs = []
		self.types = {}

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.name)

	def load(self, buf):
		offset = buf.tell()
		self.name = buf.read_string()
		self.header_size = buf.read_uint()
		self.size = buf.read_uint()
		self.meta_end = buf.tell()

		# Skip resource asset files
		if self.name.endswith("resource"):
			return

		buf.seek(offset + self.header_size - 4)
		self.data = BytesIO(buf.read(self.size))
		self.prepare()

	def prepare(self):
		buf = BinaryReader(self.data, endian=">")

		self.metadata_size = buf.read_uint()
		self.file_size = buf.read_uint()
		self.format = buf.read_uint()
		self.data_offset = buf.read_uint()
		self.endianness = buf.read_uint()

		if self.endianness == 0:
			buf.endian = "<"

		assert self.format >= 9

		self.tree = TypeMetadata()
		self.tree.load(buf)

		self.num_objects = buf.read_uint()
		for i in range(self.num_objects):
			if self.format >= 14:
				buf.align()
				path_id = buf.read_int64()
			else:
				path_id = buf.read_int()

			obj = ObjectInfo(self)
			obj.load(buf)

			if obj.type in self.tree.type_trees:
				self.types[obj.type_id] = self.tree.type_trees[obj.type_id]
			elif obj.type not in self.types:
				self.types[obj.type_id] = TypeMetadata.default().type_trees[obj.class_id]

			if path_id in self.objects:
				raise ValueError("Duplicate asset object: %r" % (obj))

			self.objects[path_id] = obj

		if self.format >= 11:
			num_adds = buf.read_uint()
			for i in range(num_adds):
				if self.format >= 14:
					buf.align()
					id = buf.read_int64()
				else:
					id = buf.read_int()
				self.adds.append((id, buf.read_int()))

		self.num_refs = buf.read_uint()
		for i in range(self.num_refs):
			ref = AssetRef()
			ref.load(buf)
			self.asset_refs.append(ref)

		unk_string = buf.read_string()
		assert not unk_string, unk_string


class AssetRef:
	def load(self, buf):
		self.asset_path = buf.read_string()
		self.guid = UUID(hexlify(buf.read(16)).decode("utf-8"))
		self.type = buf.read_int()
		self.file_path = buf.read_string()
		self.asset = None  # TODO loadrefs

	def __repr__(self):
		return "<%s (asset_path=%r, guid=%r, type=%r, file_path=%r)>" % (
			self.__class__.__name__, self.asset_path, self.guid, self.type, self.file_path
		)


class AssetBundle:
	def __init__(self):
		self.assets = []

	def load(self, file):
		buf = BinaryReader(file, endian=">")

		self.signature = buf.read_string()
		self.format_version = buf.read_int()
		self.unity_version = buf.read_string()
		self.generator_version = buf.read_string()
		self.file_size = buf.read_uint()
		self.header_size = buf.read_int()

		self.file_count = buf.read_int()
		self.bundle_count = buf.read_int()

		if self.format_version >= 2:
			self.complete_file_size = buf.read_uint()

			if self.format_version >= 3:
				self.data_header_size = buf.read_uint()

		if self.header_size >= 60:
			self.uncompressed_file_size = buf.read_uint()
			self.bundle_header_size = buf.read_uint()

		assert self.signature == SIGNATURE_RAW

		# Preload assets
		buf.seek(self.header_size)
		self.num_assets = buf.read_int()
		for i in range(self.num_assets):
			asset = Asset()
			asset.load(buf)
			self.assets.append(asset)
			buf.seek(asset.meta_end)


def load(file):
	ret = AssetBundle()
	ret.load(file)
	return ret
