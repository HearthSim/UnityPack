from .object import Object, field


class Component(Object):
	game_object = field("m_GameObject")


class Behaviour(Component):
	enabled = field("m_Enabled", bool)


class Transform(Component):
	pass
