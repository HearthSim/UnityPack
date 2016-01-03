import struct


class BinaryReader:
	def __init__(self, buf, endian="<"):
		self.buf = buf
		self.endian = endian

	def align(self):
		old = self.tell()
		new = (old + 3) & -4
		if new > old:
			self.seek(new - old, os.SEEK_CUR)

	def read(self, *args):
		return self.buf.read(*args)

	def read_string(self, encoding="utf-8"):
		ret = []
		c = b""
		while c != b"\0":
			ret.append(c)
			c = self.read(1)
			if not c:
				raise ValueError("Unterminated string: %r" % (ret))
		return b"".join(ret).decode(encoding)

	def seek(self, *args):
		return self.buf.seek(*args)

	def tell(self):
		return self.buf.tell()

	def read_byte(self):
		return struct.unpack(self.endian + "b", self.read(1))[0]

	def read_int16(self):
		return struct.unpack(self.endian + "h", self.read(2))[0]

	def read_int(self):
		return struct.unpack(self.endian + "i", self.read(4))[0]

	def read_uint(self):
		return struct.unpack(self.endian + "I", self.read(4))[0]

	def read_int64(self):
		return struct.unpack(self.endian + "q", self.read(8))[0]
