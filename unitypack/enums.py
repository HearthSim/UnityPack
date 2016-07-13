from enum import IntEnum


class CompressionType(IntEnum):
	NONE = 0
	LZMA = 1
	LZ4 = 2
	LZ4HC = 3
	LZHAM = 4


class NodeFlags(IntEnum):
	Default = 0
	Directory = 1
	Deleted = 2
	SerializedFile = 3


class RuntimePlatform(IntEnum):
	OSXEditor = 0
	OSXPlayer = 1
	WindowsPlayer = 2
	OSXWebPlayer = 3
	OSXDashboardPlayer = 4
	WindowsWebPlayer = 5
	WindowsEditor = 7
	IPhonePlayer = 8
	PS3 = 9
	XBOX360 = 10
	Android = 11
	NaCl = 12
	LinuxPlayer = 13
	FlashPlayer = 15
	WebGLPlayer = 17
	MetroPlayerX86 = 18
	WSAPlayerX86 = 18
	MetroPlayerX64 = 19
	WSAPlayerX64 = 19
	MetroPlayerARM = 20
	WSAPlayerARM = 20
	WP8Player = 21
	BB10Player = 22
	BlackBerryPlayer = 22
	TizenPlayer = 23
	PSP2 = 24
	PS4 = 25
	PSM = 26
	PSMPlayer = 26
	XboxOne = 27
	SamsungTVPlayer = 28
