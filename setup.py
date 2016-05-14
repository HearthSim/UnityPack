#!/usr/bin/env python3

import unitypack
from setuptools import setup, find_packages


CLASSIFIERS = [
	"Development Status :: 4 - Beta",
	"Intended Audience :: Developers",
	"License :: OSI Approved :: MIT License",
	"Programming Language :: Python",
	"Programming Language :: Python :: 3",
	"Programming Language :: Python :: 3.4",
	"Programming Language :: Python :: 3.5",
]


setup(
	name="unitypack",
	version=unitypack.__version__,
	author=unitypack.__author__,
	author_email=unitypack.__email__,
	description="Python implementation of the .unity3d format",
	download_url="https://github.com/HearthSim/python-unitypack/tarball/master",
	license="MIT",
	url="https://github.com/HearthSim/python-unitypack",
	classifiers=CLASSIFIERS,
	packages=find_packages(),
	package_data={"": ["classes.json", "strings.dat", "structs.dat"]},
	scripts=["bin/unityextract", "bin/unity2yaml"],
)
