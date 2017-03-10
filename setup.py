#!/usr/bin/env python3

from setuptools import setup, find_packages


setup(
	name="unitypack",
	packages=find_packages(),
	package_data={"": ["classes.json", "strings.dat", "structs.dat"]},
	scripts=["bin/unityextract", "bin/unity2yaml"],
	install_requires=[
		"decrunch",
		"fsb5",
		"lz4",
		"Pillow",
	],
)
