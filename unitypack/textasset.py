class ScriptAsset:
	def __init__(self, data=None):
		if data is None:
			data = {}
		self.data = data

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.name)

	@property
	def name(self):
		return self.data["m_Name"]

	@property
	def script(self):
		return self.data["m_Script"]


class TextAsset(ScriptAsset):
	@property
	def path(self):
		return self.data["m_PathName"]


class Shader(ScriptAsset):
	@property
	def dependencies(self):
		return self.data["m_Dependencies"]
