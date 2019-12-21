from _thread import RLock
from binascii import crc32
from io import DEFAULT_BUFFER_SIZE
from os import SEEK_CUR
import struct


def lz4_decompress(data, size):
	try:
		from lz4.block import decompress
	except ImportError:
		raise RuntimeError("python-lz4 >= 0.9 is required to read UnityFS files")

	return decompress(data, size)


def extract_audioclip_samples(d) -> dict:
	"""
	Extract all the sample data from an AudioClip and
	convert it from FSB5 if needed.
	"""
	ret = {}

	if not d.data:
		# eg. StreamedResource not available
		return {}

	try:
		from fsb5 import FSB5
	except ImportError as e:
		raise RuntimeError("python-fsb5 is required to extract AudioClip")

	af = FSB5(d.data)
	for i, sample in enumerate(af.samples):
		if i > 0:
			filename = "%s-%i.%s" % (d.name, i, af.get_sample_extension())
		else:
			filename = "%s.%s" % (d.name, af.get_sample_extension())
		try:
			sample = af.rebuild_sample(sample)
		except ValueError as e:
			print("WARNING: Could not extract %r (%s)" % (d, e))
			continue
		ret[filename] = sample

	return ret


class BinaryReader:
	def __init__(self, buf, endian="<"):
		self.buf = buf
		self.endian = endian

	def align(self):
		old = self.tell()
		new = (old + 3) & -4
		if new > old:
			self.seek(new - old, SEEK_CUR)

	def read(self, *args):
		return self.buf.read(*args)

	def seekable(self):
		return self.buf.seekable()

	def seek(self, *args):
		return self.buf.seek(*args)

	def tell(self):
		return self.buf.tell()

	def read_string(self, size=None, encoding="utf-8"):
		if size is None:
			ret = self.read_cstring()
		else:
			ret = struct.unpack(self.endian + "%is" % (size), self.read(size))[0]
		try:
			return ret.decode(encoding)
		except UnicodeDecodeError:
			return ret

	def read_cstring(self) -> bytes:
		ret = []
		c = b""
		while c != b"\0":
			ret.append(c)
			c = self.read(1)
			if not c:
				raise ValueError("Unterminated string: %r" % (ret))
		return b"".join(ret)

	def read_boolean(self) -> bool:
		return bool(struct.unpack(self.endian + "b", self.read(1))[0])

	def read_byte(self) -> int:
		return struct.unpack(self.endian + "b", self.read(1))[0]

	def read_ubyte(self) -> int:
		return struct.unpack(self.endian + "B", self.read(1))[0]

	def read_int16(self) -> int:
		return struct.unpack(self.endian + "h", self.read(2))[0]

	def read_uint16(self) -> int:
		return struct.unpack(self.endian + "H", self.read(2))[0]

	def read_int(self) -> int:
		return struct.unpack(self.endian + "i", self.read(4))[0]

	def read_uint(self) -> int:
		return struct.unpack(self.endian + "I", self.read(4))[0]

	def read_float(self) -> float:
		return struct.unpack(self.endian + "f", self.read(4))[0]

	def read_double(self) -> float:
		return struct.unpack(self.endian + "d", self.read(8))[0]

	def read_int64(self) -> int:
		return struct.unpack(self.endian + "q", self.read(8))[0]


class OffsetReader(BinaryReader):
	"""
	Create a BinaryReader class that records the current offset of buf,
	and treats this offset as the new SEEK_SET position, translating
	seek() and tell() requests as appropriate.
	"""
	def __init__(self, buf, endian=">"):
		super().__init__(buf, endian)
		self._offset = buf.tell()

	def seek(self, offset, whence=0):
		if whence == 0:
			self.buf.seek(offset + self._offset, whence)
		else:
			# SEEK_CUR: This is just a DX, it relays as-is
			# SEEK_END: This is a DX from the end, which has no Adjustment.
			self.buk.seek(offset, whence)

	def tell(self):
		return self.buf.tell() - self._offset


def stream_crc32(f, size, crc=0):
	"""
	Compute the crc32 of data found within a stream, chunking the data
	carefully to avoid excessive memory consumption while the checksum
	is computed.

	:param f: Source stream.
	:param size: How many bytes to read from the stream.
	:param crc: Prior CRC, if any. Defaults to 0.
	:return: CRC32, as an integer returned by binascii.crc32().
	"""
	_crc = crc
	while True:
		if size <= 0:
			break
		chunksize = min(DEFAULT_BUFFER_SIZE, size)

		data = f.read(chunksize)
		if not data:
			raise Exception("Unexpected EOF")
		size = size - len(data)
		_crc = crc32(data, _crc)
	return _crc


# This was borrowed from Python 3.8; by Carl Meyer.
_NOT_FOUND = object()

class cached_property:
	def __init__(self, func):
		self.func = func
		self.attrname = None
		self.__doc__ = func.__doc__
		self.lock = RLock()

	def __set_name__(self, owner, name):
		if self.attrname is None:
			self.attrname = name
		elif name != self.attrname:
			raise TypeError(
				"Cannot assign the same cached_property to two different names "
				f"({self.attrname!r} and {name!r})."
			)

	def __get__(self, instance, owner=None):
		if instance is None:
			return self
		if self.attrname is None:
			raise TypeError(
				"Cannot use cached_property instance without calling __set_name__ on it.")
		try:
			cache = instance.__dict__
		except AttributeError:  # not all objects have __dict__ (e.g. class defines slots)
			msg = (
				f"No '__dict__' attribute on {type(instance).__name__!r} "
				f"instance to cache {self.attrname!r} property."
			)
			raise TypeError(msg) from None
		val = cache.get(self.attrname, _NOT_FOUND)
		if val is _NOT_FOUND:
			with self.lock:
				# check if another thread filled cache while we awaited lock
				val = cache.get(self.attrname, _NOT_FOUND)
				if val is _NOT_FOUND:
					val = self.func(instance)
					try:
						cache[self.attrname] = val
					except TypeError:
						msg = (
							f"The '__dict__' attribute on {type(instance).__name__!r} instance "
							f"does not support item assignment for caching {self.attrname!r} property."
						)
						raise TypeError(msg) from None
		return val
