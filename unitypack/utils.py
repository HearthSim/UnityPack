import struct
from os import SEEK_CUR
from io import BytesIO
from six.moves import xrange  # pylint: disable=redefined-builtin
from six import byte2int

def uncompress(src): #from https://gist.github.com/weigon/43e217e69418875a55b31b1a5c89662d
	"""uncompress a block of lz4 data.

	:param bytes src: lz4 compressed data (LZ4 Blocks)
	:returns: uncompressed data
	:rtype: bytearray

	.. seealso:: http://cyan4973.github.io/lz4/lz4_Block_format.html
	"""
	src = BytesIO(src)

	# if we have the original size, we could pre-allocate the buffer with
	# bytearray(original_size), but then we would have to use indexing
	# instad of .append() and .extend()
	dst = bytearray()
	min_match_len = 4

	def get_length(src, length):
		"""get the length of a lz4 variable length integer."""
		if length != 0x0f:
			return length

		while True:
			read_buf = src.read(1)
			if len(read_buf) != 1:
				raise Exception("EOF at length read")
			len_part = byte2int(read_buf)

			length += len_part

			if len_part != 0xff:
				break

		return length

	while True:
		# decode a block
		read_buf = src.read(1)
		if len(read_buf) == 0:
			raise Exception("EOF at reading literal-len")
		token = byte2int(read_buf)

		literal_len = get_length(src, (token >> 4) & 0x0f)

		# copy the literal to the output buffer
		read_buf = src.read(literal_len)

		if len(read_buf) != literal_len:
			raise Exception("not literal data")
		dst.extend(read_buf)

		read_buf = src.read(2)
		if len(read_buf) == 0:
			if token & 0x0f != 0:
				raise Exception("EOF, but match-len > 0: %u" % (token % 0x0f, ))
			break

		if len(read_buf) != 2:
			raise Exception("premature EOF")

		offset = byte2int([read_buf[0]]) | (byte2int([read_buf[1]]) << 8)

		if offset == 0:
			raise Exception("offset can't be 0")

		match_len = get_length(src, (token >> 0) & 0x0f)
		match_len += min_match_len

		# append the sliding window of the previous literals
		for _ in xrange(match_len):
			dst.append(dst[-offset])

	return dst


def lz4_decompress(data, size):
	return uncompress(data)


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

	def read_int64(self) -> int:
		return struct.unpack(self.endian + "q", self.read(8))[0]
