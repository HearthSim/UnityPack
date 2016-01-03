#!/usr/bin/env python
import struct
import sys
from io import BytesIO


SIGNATURE_WEB = "UnityWeb"
SIGNATURE_RAW = "UnityRaw"


class BinaryReader:
	def __init__(self, buf):
		self.buf = buf

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

	def read_int(self):
		return struct.unpack(">i", self.read(4))[0]

	def read_uint(self):
		return struct.unpack(">I", self.read(4))[0]


class Asset:
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

		assert self.endianness == 0
		assert self.format >= 9

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

	@property
	def files(self):
		return []

	def load_file(self, path):
		file = open(path, "rb")
		self.file = file
		self.read_header()

	def read_header(self):
		buf = BinaryReader(self.file)
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
		print(bundle.files)


if __name__ == "__main__":
	main()
