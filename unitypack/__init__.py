__author__ = "Jerome Leclanche"
__email__ = "jerome@leclan.ch"
__version__ = "0.6.1"


def load(file, env=None):
	from .environment import UnityEnvironment

	if env is None:
		env = UnityEnvironment()
	return env.load(file)
