import os
from urllib.parse import urlparse

from .asset import Asset
from .assetbundle import AssetBundle


class UnityEnvironment:
	def __init__(self, base_path=""):
		self.bundles = []
		self.assets = {}
		self.asset_mapping = {}
		self.base_path = base_path
		self.files = []

	def __del__(self):
		for f in self.files:
			f.close()

	def __repr__(self):
		return "%s(base_path=%r)" % (self.__class__.__name__, self.base_path)

	def load(self, file):
		for bundle in self.bundles:
			if os.path.abspath(file.name) == os.path.abspath(bundle.path):
				return bundle
		ret = AssetBundle(self)
		ret.load(file)
		self.bundles.append(ret)
		for asset in ret.assets:
			name = asset.name.lower()
			self.assets[name] = asset
			self.asset_mapping[name] = ret
		return ret

	def discover(self, name):
		for bundle in self.bundles:
			dirname = os.path.dirname(os.path.abspath(bundle.path))
			for filename in os.listdir(dirname):
				basename = os.path.splitext(os.path.basename(filename))[0]
				if name.lower() == "cab-" + basename.lower():
					f = open(os.path.join(dirname, filename), "rb")
					self.files.append(f)
					self.load(f)

	def get_asset_by_filename(self, name):
		if name not in self.assets:
			path = os.path.join(self.base_path, name)
			if os.path.exists(path):
				f = open(path, "rb")
				self.files.append(f)
				self.assets[name] = Asset.from_file(f)
			else:
				self.discover(name)
				self.populate_assets()
				if name not in self.assets:
					raise KeyError("No such asset: %r" % (name))
		return self.assets[name]

	def populate_assets(self):
		for bundle in self.bundles:
			for asset in bundle.assets:
				asset_name = asset.name.lower()
				if asset_name not in self.assets:
					self.assets[asset_name] = asset

	def get_asset(self, url):
		if not url:
			return None

		u = urlparse(url)
		if u.scheme == "archive":
			archive, name = os.path.split(u.path.lstrip("/").lower())
		else:
			raise NotImplementedError("Unsupported scheme: %r" % (u.scheme))

		if archive not in self.asset_mapping:
			self.discover(archive)

			# Still didn't find it? Give up...
			if archive not in self.asset_mapping:
				raise NotImplementedError("Cannot find %r in %r" % (archive, self.asset_mapping))

		bundle = self.asset_mapping[archive]

		for asset in bundle.assets:
			if asset.name.lower() == name:
				return asset
		raise KeyError("No such asset: %r" % (name))
