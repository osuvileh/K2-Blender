import struct
from io import BytesIO


def generate_bounding_box(meshes):
    # need to transform verts here?
    xx = []
    yy = []
    zz = []
    for mesh in meshes:
        nv = [v.co for v in mesh.verts]
        xx += [co[0] for co in nv]
        yy += [co[1] for co in nv]
        zz += [co[2] for co in nv]
    return [min(xx), min(yy), min(zz), max(xx), max(yy), max(zz)]


def create_mesh_data(mesh, vert, index, name, m_name):
    mesh_data = BytesIO()
    mesh_data.write(struct.pack("<i", index))
    mesh_data.write(struct.pack("<i", 1))  # mode? huh? dunno...
    mesh_data.write(struct.pack("<i", len(vert)))  # vertices count
    mesh_data.write(struct.pack("<6f", *generate_bounding_box([mesh])))  # bounding box
    mesh_data.write(struct.pack("<i", -1))  # bone link... dunno... TODO
    mesh_data.write(struct.pack("<B", len(name)))
    mesh_data.write(struct.pack("<B", len(m_name)))
    mesh_data.write(name)
    mesh_data.write(struct.pack("<B", 0))
    mesh_data.write(m_name)
    mesh_data.write(struct.pack("<B", 0))
    return mesh_data.getvalue()
