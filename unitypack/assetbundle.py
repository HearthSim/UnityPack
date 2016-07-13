from io import BytesIO
from .asset import Asset
from .enums import CompressionType
from .utils import BinaryReader, lz4_decompress


SIGNATURE_RAW = "UnityRaw"
SIGNATURE_WEB = "UnityWeb"
SIGNATURE_FS = "UnityFS"


class AssetBundle:
	def __init__(self, environment):
		self.environment = environment
		self.assets = []

	def __repr__(self):
		if hasattr(self, "name"):
			return "<%s %r>" % (self.__class__.__name__, self.name)
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

		self.signature = buf.read_string()
		self.format_version = buf.read_int()
		self.unity_version = buf.read_string()
		self.generator_version = buf.read_string()

		if self.is_unityfs:
			self.load_unityfs(buf)
		else:
			assert self.signature in (SIGNATURE_RAW, SIGNATURE_WEB), self.signature
			self.load_raw(buf)

	def load_raw(self, buf):
		self.file_size = buf.read_uint()
		self.header_size = buf.read_int()

		self.file_count = buf.read_int()
		self.bundle_count = buf.read_int()

		if self.format_version >= 2:
			self.bundle_size = buf.read_uint()  # without header_size

			if self.format_version >= 3:
				self.uncompressed_bundle_size = buf.read_uint()  # without header_size

		if self.header_size >= 60:
			self.compressed_file_size = buf.read_uint()  # with header_size
			self.asset_header_size = buf.read_uint()

		buf.read_int()
		buf.read_byte()
		self.name = buf.read_string()

		# Preload assets
		buf.seek(self.header_size)
		if not self.compressed:
			num_assets = buf.read_int()
		else:
			num_assets = 1
		for i in range(num_assets):
			asset = Asset.from_bundle(self, buf)
			if not asset.is_resource:
				asset.load(asset.data)
			self.assets.append(asset)

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
		data = self.read_compressed_data(buf, compression)

		blk = BinaryReader(BytesIO(data), endian=">")
		self.guid = blk.read(16)
		num_blocks = blk.read_int()
		blocks = []
		for i in range(num_blocks):
			bcsize, busize = blk.read_int(), blk.read_int()
			bflags = blk.read_int16()
			blocks.append((bcsize, busize, bflags))

		num_nodes = blk.read_int()
		nodes = []
		for i in range(num_nodes):
			ofs = blk.read_int64()
			size = blk.read_int64()
			status = blk.read_int()
			name = blk.read_string()
			nodes.append((ofs, size, status, name))

		basepos = buf.tell()
		for ofs, size, status, name in nodes:
			buf.seek(basepos + ofs)
			asset = Asset.from_bundle(self, buf)
			asset.name = name
			if not asset.is_resource:
				asset.load(asset.data)
			self.assets.append(asset)

		# Hacky
		self.name = self.assets[0].name
