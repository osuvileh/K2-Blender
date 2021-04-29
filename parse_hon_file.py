import struct

IMPORT_LOG_LEVEL = 3


def log(msg):
    if IMPORT_LOG_LEVEL >= 1: print(msg)


def vlog(msg):
    if IMPORT_LOG_LEVEL >= 2: print(msg)


def read_int(hon_chunk):
    return struct.unpack("<i", hon_chunk.read(4))[0]


def read_float(hon_chunk):
    return struct.unpack("<f", hon_chunk.read(4))[0]


def parse_links(hon_chunk, bone_names):
    mesh_index = read_int(hon_chunk)  # wireframe index
    num_verts = read_int(hon_chunk)  # number of vertices
    log("links")
    vlog("mesh index: %d" % mesh_index)
    vlog("vertices number: %d" % num_verts)
    v_groups = {}
    for i in range(num_verts):
        num_weights = read_int(hon_chunk)  # number of scales
        if num_weights > 0:
            weights = struct.unpack("<%df" % num_weights, hon_chunk.read(num_weights * 4))
            indexes = struct.unpack("<%dI" % num_weights, hon_chunk.read(num_weights * 4))
        else:
            weights = indexes = []
        for ii, index in enumerate(indexes):
            name = bone_names[index]
            if name not in v_groups:
                v_groups[name] = list()
            v_groups[name].append((i, weights[ii]))
    hon_chunk.skip()
    return v_groups


def parse_vertices(hon_chunk):
    vlog('parsing vertices chunk')
    num_verts = (hon_chunk.chunksize - 4) / 12
    num_verts = int(num_verts)
    vlog('%d vertices' % num_verts)
    mesh_index = read_int(hon_chunk)  # wireframe index
    return [struct.unpack("<3f", hon_chunk.read(12)) for i in range(int(num_verts))]


def parse_sign(hon_chunk):
    vlog('parsing sign chunk')
    num_verts = (hon_chunk.chunksize - 8)
    mesh_index = read_int(hon_chunk)  # wireframe index
    vlog(read_int(hon_chunk))  # huh?
    return [struct.unpack("<b", hon_chunk.read(1)) for i in range(num_verts)]


def parse_faces(hon_chunk, version):
    vlog('parsing faces chunk')
    mesh_index = read_int(hon_chunk)  # wireframe index
    numfaces = read_int(hon_chunk)  # number of faces
    vlog('%d faces' % numfaces)
    if version == 3:
        size = struct.unpack('B', hon_chunk.read(1))[0]
    elif version == 1:
        size = 4
    if size == 2:
        return [struct.unpack("<3H", hon_chunk.read(6)) for i in range(numfaces)]
    elif size == 1:
        return [struct.unpack("<3B", hon_chunk.read(3)) for i in range(numfaces)]
    elif size == 4:
        return [struct.unpack("<3I", hon_chunk.read(12)) for i in range(numfaces)]
    else:
        log("unknown size for faces:%d" % size)
        return []


def parse_normals(hon_chunk):
    vlog('parsing normals chunk')
    num_verts = (hon_chunk.chunksize - 4) / 12
    num_verts = int(num_verts)
    vlog('%d normals' % num_verts)
    mesh_index = read_int(hon_chunk)  # wireframe index
    return [struct.unpack("<3f", hon_chunk.read(12)) for i in range(num_verts)]


def parse_texc(hon_chunk, version):
    vlog('parsing uv texc chunk')
    num_verts = int((hon_chunk.chunksize - 4) / 8)
    num_verts = int(num_verts)
    vlog('%d texc' % num_verts)
    mesh_index = read_int(hon_chunk)  # wireframe index
    if version == 3:
        vlog(read_int(hon_chunk))  # huh?
    return [struct.unpack("<2f", hon_chunk.read(8)) for i in range(num_verts)]


def parse_colr(hon_chunk):
    vlog('parsing vertex colours chunk')
    num_verts = (hon_chunk.chunksize - 4) / 4
    num_verts = int(num_verts)
    mesh_index = read_int(hon_chunk)  # wireframe index
    return [struct.unpack("<4B", hon_chunk.read(4)) for i in range(num_verts)]


def parse_surf(hon_chunk):
    vlog('parsing surf chunk')
    surf_index = read_int(hon_chunk)  # surface index
    num_planes = read_int(hon_chunk)  # number of planes
    num_points = read_int(hon_chunk)  # amount of points
    num_edges = read_int(hon_chunk)  # number of ribs
    num_tris = read_int(hon_chunk)  # the number of triangles?
    # BMINf,BMAXf,FLAGSi
    hon_chunk.read(4 * 3 + 4 * 3 + 4)
    return \
        [struct.unpack("<4f", hon_chunk.read(4 * 4)) for i in range(num_planes)], \
        [struct.unpack("<3f", hon_chunk.read(4 * 3)) for i in range(num_points)], \
        [struct.unpack("<6f", hon_chunk.read(4 * 6)) for i in range(num_edges)], \
        [struct.unpack("<3I", hon_chunk.read(4 * 3)) for i in range(num_tris)]