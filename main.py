#!/usr/bin/env python
import struct
import sys


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
			c = self.buf.read(1)
			if not c:
				raise ValueError("Unterminated string: %r" % (ret))
		return b"".join(ret).decode(encoding)

	def read_int(self):
		return struct.unpack(">i", self.buf.read(4))[0]

	def read_uint(self):
		return struct.unpack(">I", self.buf.read(4))[0]


class AssetBundle:
	@classmethod
	def from_path(cls, path):
		ret = cls()
		ret.load_file(path)
		return ret

	def __init__(self):
		self.file = None

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

		buf.buf.read(1)


def main():
	files = sys.argv[1:]
	for file in files:
		bundle = AssetBundle.from_path(file)
		print(bundle.files)


if __name__ == "__main__":
	main()
