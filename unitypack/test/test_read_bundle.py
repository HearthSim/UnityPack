from .. import *
import unittest
from .. import load
from pathlib import Path

def get_bundle_fixture(name):
	return Path(__file__).parent / 'fixtures' / 'bundles' / name

class TestReadAssetBundle(unittest.TestCase):
	def test_single_text_file(self):
		with get_bundle_fixture("single-text-file-2019.3.13f1-no-compression").open("rb") as f:
			bundle = load(f)
		self.assertEqual(bundle.name, "CAB-2c069a3745be5cfe0c630ceac750b567")
		self.assertFalse(bundle.compressed)
		self.assertEqual(len(bundle.assets), 1)
		asset = bundle.assets[0]
		self.assertEqual(len(asset.objects), 2)
		obj = list(asset.objects.items())[0][1]
		self.assertEqual(obj.type, "TextAsset")
		data = obj.read()
		self.assertEqual(data.name, "example")
		self.assertEqual(data.bytes, "ligma\n")

if __name__ == '__main__':
	unittest.main()

