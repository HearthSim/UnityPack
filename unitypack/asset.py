import os
import logging
import lzma
from binascii import hexlify
from io import BytesIO
from uuid import UUID
from .object import ObjectInfo
from .type import TypeMetadata
from .utils import BinaryReader


class Asset:
	@classmethod
	def from_bundle(cls, bundle, buf):
		ret = cls()
		ret.bundle = bundle
		ret.environment = bundle.environment
		offset = buf.tell()
		ret._buf = BinaryReader(buf, endian=">")

		if bundle.is_unityfs:
			ret._buf_ofs = buf.tell()
			return ret

		if not bundle.compressed:
			ret.name = buf.read_string()
			header_size = buf.read_uint()
			buf.read_uint()  # size
		else:
			header_size = bundle.asset_header_size

		# FIXME: this offset needs to be explored more
		ofs = buf.tell()
		if bundle.compressed:
			dec = lzma.LZMADecompressor()
			data = dec.decompress(buf.read())
			ret._buf = BinaryReader(BytesIO(data[header_size:]), endian=">")
			ret._buf_ofs = 0
			buf.seek(ofs)
		else:
			ret._buf_ofs = offset + header_size - 4
			if ret.is_resource:
				ret._buf_ofs -= len(ret.name)

		return ret

	@classmethod
	def from_file(cls, file, environment=None):
		ret = cls()
		ret.name = file.name
		ret._buf_ofs = file.tell()
		ret._buf = BinaryReader(file)
		base_path = os.path.abspath(os.path.dirname(file.name))
		if environment is None:
			from .environment import UnityEnvironment
			ret.environment = UnityEnvironment(base_path=base_path)
		return ret

	def get_asset(self, path):
		if ":" in path:
			return self.environment.get_asset(path)
		return self.environment.get_asset_by_filename(path)

	def __init__(self):
		self._buf_ofs = None
		self._objects = {}
		self.adds = []
		self.asset_refs = [self]
		self.types = {}
		self.typenames = {}
		self.bundle = None
		self.name = ""
		self.long_object_ids = False
		self.tree = TypeMetadata(self)
		self.loaded = False

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.name)

	@property
	def objects(self):
		if not self.loaded:
			self.load()
		return self._objects

	@property
	def is_resource(self):
		return self.name.endswith(".resource")

	def load(self):
		if self.is_resource:
			self.loaded = True
			return

		buf = self._buf
		buf.seek(self._buf_ofs)

		self.metadata_size = buf.read_uint()
		self.file_size = buf.read_uint()
		self.format = buf.read_uint()
		self.data_offset = buf.read_uint()

		if self.format >= 9:
			self.endianness = buf.read_uint()
			if self.endianness == 0:
				buf.endian = "<"

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
		self.loaded = True

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

		if obj.path_id in self._objects:
			raise ValueError("Duplicate asset object: %r (path_id=%r)" % (obj, obj.path_id))

		self._objects[obj.path_id] = obj

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

	def __repr__(self):
		return "<%s (asset_path=%r, guid=%r, type=%r, file_path=%r)>" % (
			self.__class__.__name__, self.asset_path, self.guid, self.type, self.file_path
		)

	def load(self, buf):
		self.asset_path = buf.read_string()
		self.guid = UUID(hexlify(buf.read(16)).decode("utf-8"))
		self.type = buf.read_int()
		self.file_path = buf.read_string()
		self.asset = None

	def resolve(self):
		return self.source.get_asset(self.file_path)
