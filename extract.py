#!/usr/bin/env python
import sys
import unitypack


def main():
	files = sys.argv[1:]
	for file in files:
		bundle = unitypack.AssetBundle.from_path(file)
		print(bundle)
		for asset in bundle.assets:
			print(asset)
			for id, obj in asset.objects.items():
				if obj.type != "TextAsset":
					continue
				print(obj)
				print(obj.read())


if __name__ == "__main__":
	main()
