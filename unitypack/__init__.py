import pkg_resources


__version__ = pkg_resources.require("unitypack")[0].version


def load(file, env=None):
	from .environment import UnityEnvironment

	if env is None:
		env = UnityEnvironment()
	return env.load(file)
