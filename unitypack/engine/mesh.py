from .component import Component
from .object import Object, field


class Mesh(Object):
	usage_flags = field("m_MeshUsageFlags")
	keep_indices = field("m_KeepIndices")
	baked_convex_collision_mesh = field("m_BakedConvexCollisionMesh")
	baked_triangle_collision_mesh = field("m_BakedTriangleCollisionMesh")
	compressed_mesh = field("m_CompressedMesh")
	is_readable = field("m_IsReadable")
	localAABB = field("m_LocalAABB")
	root_bone_name_hash = field("m_RootBoneNameHash")
	mesh_compression = field("m_MeshCompression")
	bone_name_hashes = field("m_BoneNameHashes")
	bind_pose = field("m_BindPose")
	shapes = field("m_Shapes")
	skin = field("m_Skin")
	submeshes = field("m_SubMeshes")
	keep_vertices = field("m_KeepVertices")
	index_buffer = field("m_IndexBuffer")
	vertex_data = field("m_VertexData")


class MeshFilter(Component):
	pass
