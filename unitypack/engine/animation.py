from .component import Behaviour
from .object import Object, field


class Animation(Behaviour):
	animate_physics = field("m_AnimatePhysics", bool)
	culling_type = field("m_CullingType")
	play_automatically = field("m_PlayAutomatically", bool)
	wrap_mode = field("m_WrapMode")
	animation = field("m_Animation")
	animations = field("m_Animations")


class Motion(Object):
	pass


class AnimationClip(Motion):
	pass
