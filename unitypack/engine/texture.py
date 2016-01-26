import struct
from enum import IntEnum
from io import BytesIO
from .object import Object, field
from .. import dds


class TextureFormat(IntEnum):
	Alpha8 = 1
	ARGB4444 = 2
	RGB24 = 3
	RGBA32 = 4
	ARGB32 = 5
	RGB565 = 7

	# Direct3D
	DXT1 = 10
	DXT5 = 12

	RGBA4444 = 13
	BGRA32 = 14

	# PowerVR
	PVRTC_RGB2 = PVRTC_2BPP_RGB = 30
	PVRTC_RGBA2 = PVRTC_2BPP_RGBA = 31
	PVRTC_RGB4 = PVRTC_4BPP_RGB = 32
	PVRTC_RGBA4 = PVRTC_4BPP_RGBA = 33

	# Ericsson (Android)
	ETC_RGB4 = 34
	ATC_RGB4 = 35
	ATC_RGBA8 = 36

	# Adobe ATF
	ATF_RGB_DXT1 = 38
	ATF_RGBA_JPG = 39
	ATF_RGB_JPG = 40

	# Ericsson
	EAC_R = 41
	EAC_R_SIGNED = 42
	EAC_RG = 43
	EAC_RG_SIGNED = 44
	ETC2_RGB = 45
	ETC2_RGBA1 = 46
	ETC2_RGBA8 = 47

	# OpenGL / GLES
	ASTC_RGB_4x4 = 48
	ASTC_RGB_5x5 = 49
	ASTC_RGB_6x6 = 50
	ASTC_RGB_8x8 = 51
	ASTC_RGB_10x10 = 52
	ASTC_RGB_12x12 = 53
	ASTC_RGBA_4x4 = 54
	ASTC_RGBA_5x5 = 55
	ASTC_RGBA_6x6 = 56
	ASTC_RGBA_8x8 = 57
	ASTC_RGBA_10x10 = 58
	ASTC_RGBA_12x12 = 59

	@property
	def pixel_format(self):
		if self == TextureFormat.RGB24:
			return "RGB"
		elif self == TextureFormat.ARGB32:
			return "ARGB"
		elif self == TextureFormat.RGB565:
			return "RGBA;15"
		elif self == TextureFormat.Alpha8:
			return "A"
		elif self == TextureFormat.RGBA4444:
			return "RGBA;4B"
		elif self == TextureFormat.ARGB4444:
			return "RGBA;4B"
		return "RGBA"


IMPLEMENTED_FORMATS = (
	TextureFormat.Alpha8,
	TextureFormat.ARGB4444,
	TextureFormat.RGBA4444,
	TextureFormat.RGB565,
	TextureFormat.RGB24,
	TextureFormat.RGBA32,
	TextureFormat.ARGB32,
	TextureFormat.DXT1,
	TextureFormat.DXT5,
)


class Sprite(Object):
	border = field("m_Border")
	extrude = field("m_Extrude")
	offset = field("m_Offset")
	rd = field("m_RD")
	rect = field("m_Rect")
	pixels_per_unit = field("m_PixelsToUnits")


class Material(Object):
	pass


class Texture(Object):
	height = field("m_Height")
	width = field("m_Width")


class Texture2D(Texture):
	data = field("image data")
	lightmap_format = field("m_LightmapFormat")
	texture_settings = field("m_TextureSettings")
	color_space = field("m_ColorSpace")
	is_readable = field("m_IsReadable")
	read_allowed = field("m_ReadAllowed")
	format = field("m_TextureFormat", TextureFormat)
	texture_dimension = field("m_TextureDimension")
	mipmap = field("m_MipMap")
	complete_image_size = field("m_CompleteImageSize")

	def __repr__(self):
		return "<%s %s (%s %ix%i)>" % (
			self.__class__.__name__, self.name, self.format.name, self.width, self.height
		)

	@property
	def decoded_data(self):
		if self.format == TextureFormat.DXT1:
			codec = dds.dxt1
		elif self.format == TextureFormat.DXT5:
			codec = dds.dxt5
		else:
			return self.data

		return codec(self.data, self.width, self.height)

	@property
	def image(self):
		from PIL import Image

		if self.format not in IMPLEMENTED_FORMATS:
			raise NotImplementedError("Unimplemented format %r" % (self.format))

		size = (self.width, self.height)
		raw_mode = self.format.pixel_format
		mode = "RGB" if raw_mode == "RGB" else "RGBA"
		data = bytes(self.decoded_data)

		if not data and size == (0, 0):
			return None

		return Image.frombytes(mode, size, data, "raw", raw_mode)
