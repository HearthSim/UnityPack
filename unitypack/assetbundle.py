import lzma
import struct
from io import BytesIO

from .asset import Asset
from .enums import CompressionType
from .utils import BinaryReader, OffsetReader, lz4_decompress

from collections import namedtuple


SIGNATURE_RAW = "UnityRaw"
SIGNATURE_WEB = "UnityWeb"
SIGNATURE_FS = "UnityFS"


class AssetBundle:
	ChunkInfo = namedtuple('ChunkInfo', ['compressed_size', 'decompressed_size'])

	def __init__(self, environment):
		self.environment = environment
		self.assets = []

	def __repr__(self):
		return "<%s>" % (self.__class__.__name__)

	@property
	def is_unityfs(self):
		return self.signature == SIGNATURE_FS

	@property
	def compressed(self):
		return self.signature == SIGNATURE_WEB

	def load(self, file):
		buf = BinaryReader(file, endian=">")
		self.path = file.name

		# Verify that the format starts with b"Unity"
		position = buf.tell()
		if buf.read(5) != b"Unity":
			raise NotImplementedError("File does not start with b'Unity': %r" % self.path)
		buf.seek(position)

		self.signature = buf.read_string()
		self.format_version = buf.read_int()
		self.unity_version = buf.read_string()
		self.generator_version = buf.read_string()

		if self.is_unityfs:
			self.load_unityfs(buf)
		elif self.signature in (SIGNATURE_RAW, SIGNATURE_WEB):
			self.load_raw(buf)
		else:
			raise NotImplementedError("Unrecognized file signature %r in %r" % (self.signature, self.path))

	def load_raw(self, buf):
		# Bundle File metadata:

		self.file_size = buf.read_uint()
		self.header_size = buf.read_int()

		self.total_chunk_count = buf.read_int()
		num_chunk_infos = buf.read_int()

		chunk_info = []
		for _ in range(num_chunk_infos):
			compressed = buf.read_uint()
			decompressed = buf.read_uint()
			chunk_info.append(self.ChunkInfo(compressed, decompressed))
		self.chunk_info = chunk_info

		if self.format_version >= 2:
			self.bundle_size = buf.read_uint()
		else:
			self.bundle_size = self.file_size

		if self.format_version >= 3:
			# Size of uncompressed bundle metadata header
			self.metadata_header_size = buf.read_uint()
		else:
			self.metadata_header_size = None

		_padding = buf.read_byte()
		assert buf.tell() == self.header_size

		# Packaged Bundle metadata:
		databuf = OffsetReader(buf.buf, endian=">")

		if self.compressed:
			databuf = BinaryReader(lzma.LZMAFile(filename=databuf), endian=">")
		self._databuf = databuf

		num_assets = databuf.read_int()
		assets = []
		for _ in range(num_assets):
			name = databuf.read_string()
			offset = databuf.read_uint()
			size = databuf.read_uint()
			assets.append((name, offset, size))

		for asset in assets:
			self.assets.append(Asset.from_bundle(self, databuf, *asset))

		if not self.metadata_header_size:
			# NB: This won't include any padding.
			self.metadata_header_size = databuf.tell()

	def read_compressed_data(self, buf, compression):
		data = buf.read(self.ciblock_size)
		if compression == CompressionType.NONE:
			return data

		if compression in (CompressionType.LZ4, CompressionType.LZ4HC):
			return lz4_decompress(data, self.uiblock_size)

		raise NotImplementedError("Unimplemented compression method: %r" % (compression))

	def load_unityfs(self, buf):
		self.file_size = buf.read_int64()
		self.ciblock_size = buf.read_uint()
		self.uiblock_size = buf.read_uint()
		flags = buf.read_uint()
		compression = CompressionType(flags & 0x3F)
		eof_metadata = flags & 0x80
		if eof_metadata:
			orig_pos = buf.tell()
			buf.seek(-self.ciblock_size, 2)
		data = self.read_compressed_data(buf, compression)
		if eof_metadata:
			buf.seek(orig_pos)

		blk = BinaryReader(BytesIO(data), endian=">")
		self.guid = blk.read(16)
		num_blocks = blk.read_int()
		blocks = []
		for i in range(num_blocks):
			busize, bcsize = blk.read_int(), blk.read_int()
			bflags = blk.read_int16()
			blocks.append(ArchiveBlockInfo(busize, bcsize, bflags))

		num_nodes = blk.read_int()
		nodes = []
		for i in range(num_nodes):
			ofs = blk.read_int64()
			size = blk.read_int64()
			status = blk.read_int()
			name = blk.read_string()
			nodes.append((ofs, size, status, name))

		storage = ArchiveBlockStorage(blocks, buf)
		for ofs, size, status, name in nodes:
			storage.seek(ofs)
			asset = Asset.from_bundle(self, BinaryReader(storage, endian=">"))
			asset.name = name
			self.assets.append(asset)


class ArchiveBlockInfo:
	def __init__(self, usize, csize, flags):
		self.uncompressed_size = usize
		self.compressed_size = csize
		self.flags = flags

	def __repr__(self):
		return "<%s: %d %d %r %r>" % (
			self.__class__.__name__,
			self.uncompressed_size, self.compressed_size,
			self.compressed, self.compression_type
		)

	@property
	def compressed(self):
		return self.compression_type != CompressionType.NONE

	@property
	def compression_type(self):
		return CompressionType(self.flags & 0x3f)

	def decompress(self, buf):
		if not self.compressed:
			return buf
		ty = self.compression_type
		if ty == CompressionType.LZMA:
			props, dict_size = struct.unpack("<BI", buf.read(5))
			lc = props % 9
			props = int(props / 9)
			pb = int(props / 5)
			lp = props % 5
			dec = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[{
				"id": lzma.FILTER_LZMA1,
				"dict_size": dict_size,
				"lc": lc,
				"lp": lp,
				"pb": pb,
			}])
			res = dec.decompress(buf.read())
			return BytesIO(res)
		if ty in (CompressionType.LZ4, CompressionType.LZ4HC):
			res = lz4_decompress(buf.read(self.compressed_size), self.uncompressed_size)
			return BytesIO(res)
		raise NotImplementedError("Unimplemented compression method: %r" % (ty))


class ArchiveBlockStorage:
	def __init__(self, blocks, stream):
		self.blocks = blocks
		self.stream = stream
		self.cursor = 0
		self.basepos = stream.tell()
		self.maxpos = sum([b.uncompressed_size for b in blocks])
		self.sought = False
		self.current_block = None
		self.current_block_start = 0
		self.current_stream = None
		self._seek(0)

	def read(self, size=-1):
		buf = bytearray()
		while size != 0 and self.cursor < self.maxpos:
			if not self.in_current_block(self.cursor):
				self.seek_to_block(self.cursor)
			part = self.current_stream.read(size)
			if size > 0:
				if len(part) == 0:
					raise EOFError()
				size -= len(part)
			self.cursor += len(part)
			buf += part
		return bytes(buf)

	def seek(self, offset, whence=0):
		new_cursor = 0
		if whence == 1:
			new_cursor = offset + self.cursor
		elif whence == 2:
			new_cursor = self.maxpos + offset
		else:
			new_cursor = offset
		if self.cursor != new_cursor:
			self._seek(new_cursor)

	def tell(self):
		return self.cursor

	def _seek(self, new_cursor):
		self.cursor = new_cursor
		if not self.in_current_block(new_cursor):
			self.seek_to_block(new_cursor)
		self.current_stream.seek(new_cursor - self.current_block_start)

	def in_current_block(self, pos):
		if self.current_block is None:
			return False
		end = self.current_block_start + self.current_block.uncompressed_size
		return self.current_block_start <= pos and pos < end

	def seek_to_block(self, pos):
		baseofs = 0
		ofs = 0
		for b in self.blocks:
			if ofs + b.uncompressed_size > pos:
				self.current_block = b
				break
			baseofs += b.compressed_size
			ofs += b.uncompressed_size
		else:
			self.current_block = None
			self.current_stream = BytesIO(b"")
			return

		self.current_block_start = ofs
		self.stream.seek(self.basepos + baseofs)
		buf = BytesIO(self.stream.read(self.current_block.compressed_size))
		self.current_stream = self.current_block.decompress(buf)
