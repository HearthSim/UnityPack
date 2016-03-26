from io import BytesIO
from .utils import BinaryReader


class OBJVector2:
	def __init__(self, x = 0, y = 0):
		self.x = x
		self.y = y

	def read(self, buf):
		self.x = buf.read_float()
		self.y = buf.read_float()
		return self

	def __str__(self):
		return "%s %s" % (self.x, 1 - self.y)


class OBJVector3(OBJVector2):
	def __init__(self, x = 0, y = 0, z = 0):
		super().__init__(x, y)
		self.z = z

	def read(self, buf):
		super().read(buf)
		self.z = buf.read_float()
		return self

	def __str__(self):
		return "%s %s %s" % (-self.x, self.y, self.z)


class OBJVector4(OBJVector3):
	def __init__(self, x = 0, y = 0, z = 0, w = 0):
		super().__init__(x, y, z)
		self.w = w

	def read(self, buf):
		super().read(buf)
		self.w = buf.read_float()
		return self

	def read_color(self, buf):
		self.x = buf.read_ubyte()
		self.y = buf.read_ubyte()
		self.z = buf.read_ubyte()
		self.w = buf.read_ubyte()
		return self

	def __str__(self):
		return "%s %s %s %s" % (self.x, self.y, self.z, self.w)


class MeshData:
	def __init__(self, mesh):
		self.mesh = mesh
		self.indices = []
		self.triangles = []
		self.vertices = []
		self.normals = []
		self.colors = []
		self.uv1 = []
		self.uv2 = []
		self.uv3 = []
		self.uv4 = []
		self.tangents = []
		self.extract_indices()
		self.extract_vertices()

	def extract_indices(self):
		for sub in self.mesh.submeshes:
			sub_indices = []
			sub_triangles = []
			buf = BinaryReader(BytesIO(self.mesh.index_buffer))
			buf.seek(sub.first_byte)
			for i in range(0, sub.index_count):
				sub_indices.append(buf.read_uint16())
			if not sub.topology:
				sub_triangles.extend(sub_indices)
			else:
				raise NotImplementedError("(%s) topologies are not supported" % (self.mesh.name))

			self.indices.append(sub_indices)
			self.triangles.append(sub_triangles)

	def extract_vertices(self):
		# unity 5+ has 8 channels (6 otherwise)
		v5_channel_count = 8
		buf = BinaryReader(BytesIO(self.mesh.vertex_data.data))
		channels = self.mesh.vertex_data.channels
		# actual streams attribute 'm_Streams' may only exist in unity 4,
		# use of channel data alone seems to be sufficient
		stream_count = self.get_num_streams(channels)
		channel_count = len(channels)

		for s in range(0, stream_count):
			for i in range(0, self.mesh.vertex_data.vertex_count):
				for j in range(0, channel_count):
					ch = None
					if channel_count > 0:
						ch = channels[j]
						# format == 1, use half-floats (16 bit)
						if ch["format"] == 1:
							raise NotImplementedError("(%s) 16 bit floats are not supported" % (mesh.name))
					# read the appropriate vertex value into the correct list
					if ch and ch["dimension"] > 0 and ch["stream"] == s:
						if j == 0:
							self.vertices.append(OBJVector3().read(buf))
						elif j == 1:
							self.normals.append(OBJVector3().read(buf))
						elif j == 2:
							self.colors.append(OBJVector4().read_color(buf))
						elif j == 3:
							self.uv1.append(OBJVector2().read(buf))
						elif j == 4:
							self.uv2.append(OBJVector2().read(buf))
						elif j == 5:
							if channel_count == v5_channel_count:
								self.uv3.append(OBJVector2().read(buf))
							else:
								self.tangents.append(OBJVector4().read(buf))
						elif j == 6: # for unity 5+
							self.uv4.append(OBJVector2().read(buf))
						elif j == 7: # for unity 5+
							self.tangents.append(OBJVector4().read(buf))
			# TODO investigate possible alignment here, after each stream

	def get_num_streams(self, channels):
		streams = []
		# scan the channel's stream value for distinct entries
		for c in channels:
			if c["stream"] not in streams:
				streams.append(c["stream"])

		return len(streams)


class OBJMesh:
	def __init__(self, mesh):
		if mesh.mesh_compression:
			# TODO handle compressed meshes
			raise NotImplementedError("(%s) compressed meshes are not supported" % (mesh.name))
		self.mesh_data = MeshData(mesh)
		self.mesh = mesh

	@staticmethod
	def face_str(indices, coords, normals):
		ret = ["f "]
		for i in indices[::-1]:
			ret.append(str(i + 1))
			if coords or normals:
				ret.append("/")
				if coords:
					ret.append(str(i + 1))
				if normals:
					ret.append("/")
					ret.append(str(i + 1))
			ret.append(" ")
		ret.append("\n")
		return "".join(ret)

	def export(self):
		ret = []
		verts_per_face = 3
		normals = self.mesh_data.normals
		tex_coords = self.mesh_data.uv1
		if not tex_coords:
			tex_coords = self.mesh_data.uv2

		for v in self.mesh_data.vertices:
			ret.append("v %s\n" % (v))
		for v in normals:
			ret.append("vn %s\n" % (v))
		for v in tex_coords:
			ret.append("vt %s\n" % (v))
		ret.append("\n")

		# write group name and set smoothing to 1
		ret.append("g %s\n" % (self.mesh.name))
		ret.append("s 1\n")

		sub_count = len(self.mesh.submeshes)
		for i in range(0, sub_count):
			if sub_count == 1:
				ret.append("usemtl %s\n" % (self.mesh.name))
			else:
				ret.append("usemtl %s_%d\n" % (self.mesh.name, i))
			face_tri = []
			for t in self.mesh_data.triangles[i]:
				face_tri.append(t)
				if len(face_tri) == verts_per_face:
					ret.append(self.face_str(face_tri, tex_coords, normals))
					face_tri = []
			ret.append("\n")

		return "".join(ret)
