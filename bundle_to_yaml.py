#!/usr/bin/env python
import os
import sys
import unitypack
import yaml
from argparse import ArgumentParser


def handle_asset(asset):
	for id, obj in asset.objects.items():
		d = obj.read()

		print(yaml.dump(d))


def asset_representer(dumper, data):
	return dumper.represent_scalar("!asset", data.name)
yaml.add_representer(unitypack.Asset, asset_representer)


def objectpointer_representer(dumper, data):
	return dumper.represent_sequence("!PPtr", [data.file_id, data.path_id])
yaml.add_representer(unitypack.ObjectPointer, objectpointer_representer)


def unityobj_representer(dumper, data):
	return dumper.represent_mapping("!unitypack:%s" % (data.__class__.__name__), data._obj)


def shader_representer(dumper, data):
	return dumper.represent_mapping("!unitypack:stripped:Shader", {data.name: None})


def textasset_representer(dumper, data):
	return dumper.represent_mapping("!unitypack:stripped:TextAsset", {data.name: None})


def texture2d_representer(dumper, data):
	return dumper.represent_mapping("!unitypack:stripped:Texture2D", {data.name: None})


def mesh_representer(dumper, data):
	return dumper.represent_mapping("!unitypack:stripped:Mesh", {data.name: None})


def movietexture_representer(dumper, data):
	obj = data._obj.copy()
	obj["m_MovieData"] = "<stripped>"
	return dumper.represent_mapping("!unitypack:stripped:MovieTexture", obj)


def main():
	p = ArgumentParser()
	p.add_argument("files", nargs="+")
	p.add_argument("-s", "--strip", action="store_true", help="Strip extractable data")
	args = p.parse_args(sys.argv[1:])

	for k, v in unitypack.engine.__dict__.items():
		if isinstance(v, type) and issubclass(v, unitypack.engine.object.Object):
			yaml.add_representer(v, unityobj_representer)

	if args.strip:
		yaml.add_representer(unitypack.engine.mesh.Mesh, mesh_representer)
		yaml.add_representer(unitypack.engine.movie.MovieTexture, movietexture_representer)
		yaml.add_representer(unitypack.engine.text.Shader, shader_representer)
		yaml.add_representer(unitypack.engine.text.TextAsset, textasset_representer)
		yaml.add_representer(unitypack.engine.texture.Texture2D, texture2d_representer)

	for file in args.files:
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
