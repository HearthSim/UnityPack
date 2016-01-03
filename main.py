#!/usr/bin/env python
import os
import struct
import sys
from enum import IntEnum
from io import BytesIO


SIGNATURE_WEB = "UnityWeb"
SIGNATURE_RAW = "UnityRaw"


class UnityClass(IntEnum):
	TextAsset = 49
	AssetBundle = 142


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

	def read_int16(self):
		return struct.unpack(self.endian + "h", self.read(2))[0]

	def read_int(self):
		return struct.unpack(self.endian + "i", self.read(4))[0]

	def read_uint(self):
		return struct.unpack(self.endian + "I", self.read(4))[0]

	def read_int64(self):
		return struct.unpack(self.endian + "q", self.read(8))[0]

	def align(self):
		old = self.tell()
		new = (old + 3) & -4
		if new > old:
			self.seek(new - old, os.SEEK_CUR)


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


class ObjectInfo:
	def __init__(self, format):
		self.format = format

	def __repr__(self):
		return "<%s %i>" % (self.type.name, self.class_id)

	def load(self, buf):
		self.byte_start = buf.read_uint()
		self.size = buf.read_uint()
		self.type = UnityClass(buf.read_uint())
		self.class_id = buf.read_uint()

		if self.format <= 10:
			self.is_destroyed = bool(buf.read_int16())
		elif self.format >= 11:
			self.unk0 = buf.read_int16()

			if self.format >= 15:
				self.unk1 = buf.read_byte()


class Asset:
	def __init__(self):
		self.objects = {}

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.name)

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

		self.num_objects = buf.read_uint()
		for i in range(self.num_objects):
			if self.format >= 14:
				buf.align()
				path_id = buf.read_int64()
			else:
				path_id = buf.read_int()

			obj = ObjectInfo(self.format)
			obj.load(buf)

			if path_id in self.objects:
				raise ValueError("Duplicate asset object: %r" % (obj))

			self.objects[path_id] = obj

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
			for id, obj in asset.objects.items():
				print(obj)


if __name__ == "__main__":
	main()
