#!/usr/bin/env python
import os
import sys
import unitypack


def write_to_file(filename, contents):
	basedir = "out"

	if not os.path.exists(basedir):
		os.makedirs(basedir)

	path = os.path.join(basedir, filename)
	with open(path, "w") as f:
		written = f.write(contents)

	print("Written %i bytes to %r" % (written, path))


def main():
	files = sys.argv[1:]
	for file in files:
		with open(file, "rb") as f:
			bundle = unitypack.load(f)

		for asset in bundle.assets:
			print(asset)
			for id, obj in asset.objects.items():
				if obj.type != "TextAsset":
					continue
				d = obj.read()
				write_to_file(d["m_Name"] + ".txt", d["m_Script"])


if __name__ == "__main__":
	main()
