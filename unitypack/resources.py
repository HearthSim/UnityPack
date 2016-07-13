import os
import json


def get_resource(name):
	return os.path.join(os.path.dirname(__file__), name)


with open(get_resource("strings.dat"), "rb") as f:
	STRINGS_DAT = f.read()


with open(get_resource("classes.json"), "r") as f:
	UNITY_CLASSES = json.load(f)


def UnityClass(i):
	return UNITY_CLASSES.get(str(i), "<Unknown #%i>" % (i))
