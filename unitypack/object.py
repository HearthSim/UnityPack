import logging
from collections import OrderedDict
from io import BytesIO
from . import engine as UnityEngine
from .resources import UnityClass
from .type import TypeMetadata, TypeTree
from .utils import BinaryReader


def load_object(type, obj):
	clsname = type.type
	if hasattr(UnityEngine, clsname):
		obj = getattr(UnityEngine, clsname)(obj)

	return obj


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
			elif self.type_id in self.asset.tree.type_trees:
				typename = self.asset.tree.type_trees[self.type_id].type
			else:
				typename = str(self.type_id)
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
		if self.asset.format < 17:
			self.type_id = buf.read_int()
			self.class_id = buf.read_int16()
		else:
			type_id = buf.read_int()
			class_id = self.asset.tree.class_ids[type_id]
			self.type_id = class_id
			self.class_id = class_id
		if self.asset.format <= 10:
			self.is_destroyed = bool(buf.read_int16())
		if self.asset.format >= 11 and self.asset.format <= 16:
			self.unk0 = buf.read_int16()

		if self.asset.format >= 15 and self.asset.format <= 16:
			self.unk1 = buf.read_byte()

	def read_id(self, buf):
		if self.asset.long_object_ids:
			return buf.read_int64()
		else:
			return self.asset.read_id(buf)

	def read(self):
		buf = self.asset._buf
		buf.seek(self.asset._buf_ofs + self.data_offset)
		object_buf = buf.read(self.size)
		return self.read_value(self.type_tree, BinaryReader(BytesIO(object_buf)))

	def read_value(self, type, buf):
		align = False
		expected_size = type.size
		pos_before = buf.tell()
		t = type.type
		first_child = type.children[0] if type.children else TypeTree(self.asset.format)
		if t == "bool":
			result = buf.read_boolean()
		elif t == "SInt8":
			result = buf.read_byte()
		elif t == "UInt8":
			result = buf.read_ubyte()
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
			elif t == "pair":
				assert len(type.children) == 2
				first = self.read_value(type.children[0], buf)
				second = self.read_value(type.children[1], buf)
				result = (first, second)
			else:
				result = OrderedDict()

				for child in type.children:
					result[child.name] = self.read_value(child, buf)

				result = load_object(type, result)
				if t == "StreamedResource":
					result.asset = self.resolve_streaming_asset(result.source)
				elif t == "StreamingInfo":
					result.asset = self.resolve_streaming_asset(result.path)

		# Check to make sure we read at least as many bytes the tree says.
		# We allow reading more for the case of alignment.
		pos_after = buf.tell()
		actual_size = pos_after - pos_before
		if expected_size > 0 and actual_size < expected_size:
			raise ValueError("Expected read_value(%r) to read %r bytes, but only read %r bytes" % (type, expected_size, actual_size))

		if align or type.post_align:
			buf.align()

		return result

	def resolve_streaming_asset(self, path):
		if len(path) > 0:
			return self.asset.get_asset(path)


class ObjectPointer:
	def __init__(self, type, asset):
		self.type = type
		self.source_asset = asset

	def __repr__(self):
		return "%s(file_id=%r, path_id=%r)" % (
			self.__class__.__name__, self.file_id, self.path_id
		)

	def __bool__(self):
		return not (self.file_id == 0 and self.path_id == 0)

	@property
	def asset(self):
		from .asset import AssetRef

		ret = self.source_asset.asset_refs[self.file_id]
		if isinstance(ret, AssetRef):
			ret = ret.resolve()
		return ret

	@property
	def object(self):
		return self.asset.objects[self.path_id]

	def load(self, buf):
		self.file_id = buf.read_int()
		self.path_id = self.source_asset.read_id(buf)

	def resolve(self):
		return self.object.read()
