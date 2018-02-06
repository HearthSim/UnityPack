import pkg_resources


__version__ = pkg_resources.require("unitypack")[0].version


def load(file, env=None):
	from .environment import UnityEnvironment

	if env is None:
		env = UnityEnvironment()
	return env.load(file)


def load_from_file(file, env=None):
	from .environment import UnityEnvironment

	if env is None:
		env = UnityEnvironment()
	return env.get_asset_by_filename(file)
