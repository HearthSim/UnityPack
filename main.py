#!/usr/bin/env python
import struct
import sys
from io import BytesIO


SIGNATURE_WEB = "UnityWeb"
SIGNATURE_RAW = "UnityRaw"


class BinaryReader:
	def __init__(self, buf, endian="<"):
		self.buf = buf
		self.endian = endian

	def read_string(self, encoding="utf-8"):
		ret = []
		c = b""
		while c != b"\0":
			ret.append(c)
			c = self.read(1)
			if not c:
				raise ValueError("Unterminated string: %r" % (ret))
		return b"".join(ret).decode(encoding)

	def read(self, *args):
		return self.buf.read(*args)

	def seek(self, *args):
		return self.buf.seek(*args)

	def tell(self):
		return self.buf.tell()

	def read_byte(self):
		return struct.unpack(self.endian + "b", self.read(1))[0]

	def read_int(self):
		return struct.unpack(self.endian + "i", self.read(4))[0]

	def read_uint(self):
		return struct.unpack(self.endian + "I", self.read(4))[0]


class TypeTree:
	def load_blob(self, buf):
		self.nodes = buf.read_uint()
		self.buffer_bytes = buf.read_uint()
		node_data = BytesIO(buf.read(24 * self.nodes))
		local_buffer = BytesIO(buf.read(self.buffer_bytes))
		# todo the rest...


class TypeMetadata:
	def load(self, buf):
		offset = buf.tell()
		self.generator_version = buf.read_string()
		self.target_platform = buf.read_uint()

		assert self.target_platform == 5  # Windows. RuntimePlatform?

		# if format >= 13
		self.has_type_trees = bool(buf.read_byte())
		self.num_types = buf.read_int()

		hashes = {}
		trees = {}

		for i in range(self.num_types):
			class_id = buf.read_int()  # TODO get unity class
			if class_id < 0:
				hash = buf.read(0x20)
			else:
				hash = buf.read(0x10)

			hashes[class_id] = hash

			if self.has_type_trees:
				tree = TypeTree()
				tree.load_blob(buf)
				trees[class_id] = tree


class Asset:
	def __init__(self):
		self.objects = {}

	def __repr__(self):
		return "<Asset %s>" % (self.name)

	def read_header(self, buf):
		offset = buf.tell()
		self.name = buf.read_string()
		self.header_size = buf.read_uint()
		self.size = buf.read_uint()

		buf.seek(offset + self.header_size)
		self.file_size = buf.read_uint()
		self.format = buf.read_uint()
		self.data_offset = buf.read_uint()
		self.endianness = buf.read_uint()

		if self.endianness == 0:
			buf.endian = "<"

		assert self.format >= 9

		self.tree = TypeMetadata()
		self.tree.load(buf)

		buf.seek(offset + self.data_offset)
		self.data = BytesIO(buf.read(self.size))


class AssetBundle:
	@classmethod
	def from_path(cls, path):
		ret = cls()
		ret.load_file(path)
		return ret

	def __init__(self):
		self.file = None
		self.assets = []

	def __del__(self):
		if self.file:
			self.file.close()

	def load_file(self, path):
		file = open(path, "rb")
		self.file = file
		self.read_header()

	def read_header(self):
		buf = BinaryReader(self.file, endian=">")
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
			asset.read_header(buf)
			self.assets.append(asset)


def main():
	files = sys.argv[1:]
	for file in files:
		bundle = AssetBundle.from_path(file)
		print(bundle)
		for asset in bundle.assets:
			print(asset)
			for obj in asset.objects:
				print(obj)


if __name__ == "__main__":
	main()
