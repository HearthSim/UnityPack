from io import BytesIO
from .enums import RuntimePlatform
from .resources import get_resource, STRINGS_DAT
from .utils import BinaryReader


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

		num_fields = buf.read_uint()
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
			depth = buf.read_ubyte()

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
			with open(get_resource("structs.dat"), "rb") as f:
				cls.default_instance.load(BinaryReader(f), format=15)
		return cls.default_instance

	def __init__(self, asset):
		self.type_trees = {}
		self.hashes = {}
		self.asset = asset
		self.generator_version = ""
		self.target_platform = None

	def load(self, buf, format=None):
		if format is None:
			format = self.asset.format
		self.generator_version = buf.read_string()
		self.target_platform = RuntimePlatform(buf.read_uint())

		if format >= 13:
			has_type_trees = buf.read_boolean()
			num_types = buf.read_int()

			for i in range(num_types):
				class_id = buf.read_int()
				if class_id < 0:
					hash = buf.read(0x20)
				else:
					hash = buf.read(0x10)

				self.hashes[class_id] = hash

				if has_type_trees:
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
