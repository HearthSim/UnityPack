from .object import Object, field


class TextAsset(Object):
	path = field("m_PathName")
	script = field("m_Script")


class Shader(Object):
	dependencies = field("m_Dependencies")
	script = field("m_Script")
