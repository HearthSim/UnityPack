from enum import IntEnum
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


class AnimatorCullingMode(IntEnum):
	AlwaysAnimate = 0
	CullUpdateTransforms = 1
	CullCompletely = 2
	BasedOnRenderers = 1


class AnimatorUpdateMode(IntEnum):
	Normal = 0
	AnimatePhysics = 1
	unscaledTime = 2


class Animator(Behaviour):
	allow_constant_clip_sampling_optimization = field("m_AllowConstantClipSamplingOptimization", bool)
	apply_root_motion = field("m_ApplyRootMotion", bool)
	avatar = field("m_Avatar")
	controller = field("m_Controller")
	culling_mode = field("m_CullingMode", AnimatorCullingMode)
	has_transform_hierarchy = field("m_HasTransformHierarchy", bool)
	linear_velocity_binding = field("m_LinearVelocityBlending", bool)
	update_mode = field("m_UpdateMode", AnimatorUpdateMode)
