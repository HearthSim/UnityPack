import struct
from enum import IntEnum
from io import BytesIO
from . import dds


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


def argb_to_rgba(data, width, height):
	pixels = len(data) // 16
	data = BytesIO(data)
	ret = bytearray()

	for i in range(pixels):
		a, r, g, b = struct.unpack("<4I", data.read(16))
		ret += struct.pack("<4I", r, g, b, a)

	return ret


class Texture2D:
	def __init__(self, data):
		if data:
			self.name = data["m_Name"]
			self.data = data["image data"]
			self.height = data["m_Height"]
			self.width = data["m_Width"]
			self.lightmap_format = data["m_LightmapFormat"]
			self.texture_settings = data["m_TextureSettings"]
			self.color_space = data["m_ColorSpace"]
			self.is_readable = data["m_IsReadable"]
			self.read_allowed = data["m_ReadAllowed"]
			self.format = TextureFormat(data["m_TextureFormat"])
			self.texture_dimension = data["m_TextureDimension"]
			self.mipmap = data["m_MipMap"]
			self.complete_image_size = data["m_CompleteImageSize"]

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
		elif self.format in (TextureFormat.RGB24, TextureFormat.RGBA32):
			codec = lambda data, w, h: data
		elif self.format == TextureFormat.ARGB32:
			codec = argb_to_rgba
		else:
			raise NotImplementedError("Unimplemented format %r" % (self.format))

		return codec(self.data, self.width, self.height)

	@property
	def image(self):
		from PIL import Image

		if self.format == TextureFormat.RGB24:
			mode = "RGB"
		else:
			mode = "RGBA"

		size = (self.width, self.height)
		img = Image.frombytes(mode, size, bytes(self.decoded_data))

		return img
