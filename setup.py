#!/usr/bin/env python3

import unitypack
from setuptools import setup, find_packages


setup(
	name="unitypack",
	version=unitypack.__version__,
	packages=find_packages(),
	package_data={"": ["classes.json", "strings.dat", "structs.dat"]},
	scripts=["bin/unityextract", "bin/unity2yaml"],
)
