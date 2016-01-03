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
		c = ""
		while c != b"\0":
			c = self.buf.read(1)
			if not c:
				raise ValueError("Unterminated string: %r" % (ret))
			ret.append(c)
		return b"".join(ret).decode(encoding)


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


def main():
	files = sys.argv[1:]
	for file in files:
		bundle = AssetBundle.from_path(file)
		print(bundle.files)


if __name__ == "__main__":
	main()
