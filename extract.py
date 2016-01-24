#!/usr/bin/env python
import fsb5
import os
import sys
import unitypack
from PIL import ImageOps


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
			audio = fsb5.FSB5(d.data)
			assert len(audio.samples) == 1
			try:
				write_to_file(d.name + "." + audio.get_sample_extension(), audio.rebuild_sample(audio.samples[0]), mode="wb")
			except (ValueError, NotImplementedError, OSError) as e:
				print('Got error: "%s" while rebuilding audio sample. Writing raw fsb instead' % e)
				write_to_file(d.name + ".fsb", d.data, mode="wb")

		elif obj.type == "Shader":
			write_to_file(d.name + ".cg", d.script)

		elif obj.type == "TextAsset":
			write_to_file(d.name + ".txt", d.script)

		elif obj.type == "Texture2D":
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
