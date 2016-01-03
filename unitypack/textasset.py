class TextAsset:
	def __init__(self, data=None):
		if data:
			self.path = data["m_PathName"]
			self.name = data["m_Name"]
			self.script = data["m_Script"]
		else:
			self.path = ""
			self.name = ""
			self.path = ""

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.name)
