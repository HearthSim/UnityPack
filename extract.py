#!/usr/bin/env python
import os
import sys
import unitypack
from PIL import ImageOps
from fsb5 import FSB5


SUPPORTED_FORMATS = (
	"AudioClip",
	"Shader",
	"TextAsset",
	"Texture2D",
)


def get_output_path(filename):
	basedir = "out"
	path = os.path.join(basedir, filename)
	dirs = os.path.dirname(path)
	if not os.path.exists(dirs):
		os.makedirs(dirs)
	return path


def write_to_file(filename, contents, mode="w"):
	path = get_output_path(filename)
	with open(path, mode) as f:
		written = f.write(contents)

	print("Written %i bytes to %r" % (written, path))


def handle_asset(asset):
	print(asset)
	for id, obj in asset.objects.items():
		if obj.type not in SUPPORTED_FORMATS:
			print("Skipping %r" % (obj))
			continue

		d = obj.read()

		if obj.type == "AudioClip":
			if not d.data:
				# eg. StreamedResource not available
				continue
			af = FSB5(d.data)
			for i, sample in enumerate(af.samples):
				if i > 0:
					filename = "%s-%i.%s" % (d.name, i, af.get_sample_extension())
				else:
					filename = "%s.%s" % (d.name, af.get_sample_extension())
				write_to_file(filename, af.rebuild_sample(sample), mode="wb")

		elif obj.type == "Shader":
			write_to_file(d.name + ".cg", d.script)

		elif obj.type == "TextAsset":
			write_to_file(d.name + ".txt", d.script)

		elif obj.type == "Texture2D":
			filename = d.name + ".png"
			if not d.image:
				print("WARNING: %s is an empty image" % (filename))
				write_to_file(filename, "")
			else:
				print("Decoding %r" % (d))
				img = ImageOps.flip(d.image)
				path = get_output_path(d.name + ".png")
				img.save(path)


def main():
	files = sys.argv[1:]
	for file in files:
		if file.endswith(".assets"):
			with open(file, "rb") as f:
				asset = unitypack.Asset.from_file(f)
			handle_asset(asset)
			continue

		with open(file, "rb") as f:
			bundle = unitypack.load(f)

		for asset in bundle.assets:
			handle_asset(asset)


if __name__ == "__main__":
	main()
