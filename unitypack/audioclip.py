from enum import IntEnum
from .object import Object, field


class AudioFormat(IntEnum):
	UNKNOWN = 0
	ACC = 1
	AIFF = 2
	IT = 10
	MOD = 12
	MPEG = 13
	OGGVORBIS = 14
	S3M = 17
	WAV = 20
	XM = 21
	XMA = 22
	VAG = 23
	AUDIOQUEUE = 24


class AudioClip(Object):
	bits_per_sample = field("m_BitsPerSample")
	channels = field("m_Channels")
	compression_format = field("m_CompressionFormat")
	frequency = field("m_Frequency")
	is_tracker_format = field("m_IsTrackerFormat")
	legacy3d = field("m_Legacy3D")
	length = field("m_Length")
	load_in_background = field("m_LoadInBackground")
	load_type = field("m_LoadType")
	preload_audio_data = field("m_PreloadAudioData")
	subsound_index = field("m_SubsoundIndex")
	resource = field("m_Resource")
