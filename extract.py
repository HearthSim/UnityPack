#!/usr/bin/env python
import os
import pickle
import sys
import unitypack
from unitypack.export import OBJMesh
from argparse import ArgumentParser
from PIL import ImageOps
from fsb5 import FSB5


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


def handle_asset(asset, handle_formats):
	for id, obj in asset.objects.items():
		if obj.type not in handle_formats:
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
				try:
					sample = af.rebuild_sample(sample)
				except ValueError as e:
					print("WARNING: Could not extract %r (%s)" % (d, e))
					continue
				write_to_file(filename, sample, mode="wb")

		elif obj.type == "MovieTexture":
			filename = d.name + ".ogv"
			write_to_file(filename, d.movie_data, mode="wb")

		elif obj.type == "Shader":
			write_to_file(d.name + ".cg", d.script)

		elif obj.type == "Mesh":
			try:
				mesh_data = OBJMesh(d).export()
				write_to_file(d.name + ".obj", mesh_data, mode="w")
			except NotImplementedError as e:
				print("WARNING: Could not extract %r (%s)" % (d, e))
				mesh_data = pickle.dumps(d._obj)
				write_to_file(d.name + ".Mesh.pickle", mesh_data, mode="wb")

		elif obj.type == "TextAsset":
			if isinstance(d.script, bytes):
				write_to_file(d.name + ".bin", d.script, mode="wb")
			else:
				write_to_file(d.name + ".txt", d.script)

		elif obj.type == "Texture2D":
			filename = d.name + ".png"
			image = d.image
			if image is None:
				print("WARNING: %s is an empty image" % (filename))
				write_to_file(filename, "")
			else:
				print("Decoding %r" % (d))
				img = ImageOps.flip(image)
				path = get_output_path(filename)
				img.save(path)


def main():
	p = ArgumentParser()
	p.add_argument("files", nargs="+")
	p.add_argument("--all", action="store_true")
	p.add_argument("--audio", action="store_true")
	p.add_argument("--images", action="store_true")
	p.add_argument("--models", action="store_true")
	p.add_argument("--shaders", action="store_true")
	p.add_argument("--text", action="store_true")
	p.add_argument("--video", action="store_true")
	args = p.parse_args(sys.argv[1:])

	format_args = {
		"audio": "AudioClip",
		"images": "Texture2D",
		"models": "Mesh",
		"shaders": "Shader",
		"text": "TextAsset",
		"video": "MovieTexture",
	}
	handle_formats = []
	for a, classname in format_args.items():
		if args.all or getattr(args, a):
			handle_formats.append(classname)

	for file in args.files:
		if file.endswith(".assets"):
			with open(file, "rb") as f:
				asset = unitypack.Asset.from_file(f)
			handle_asset(asset, handle_formats)
			continue

		with open(file, "rb") as f:
			bundle = unitypack.load(f)

		for asset in bundle.assets:
			handle_asset(asset, handle_formats)


if __name__ == "__main__":
	main()
