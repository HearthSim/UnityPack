#!/usr/bin/env python
import sys


SIGNATURE_WEB = "UnityWeb"
SIGNATURE_RAW = "UnityRaw"


class AssetBundle:
	@classmethod
	def from_path(cls, path):
		ret = cls()
		ret.file = open(path, "r")
		return ret

	def __init__(self):
		self.file = None

	def __del__(self):
		if self.file:
			self.file.close()

	@property
	def files(self):
		return []


def main():
	files = sys.argv[1:]
	for file in files:
		bundle = AssetBundle.from_path(file)
		print(bundle.files)


if __name__ == "__main__":
	main()
