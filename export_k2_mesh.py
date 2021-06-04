import struct
from io import BytesIO

import bmesh
import bpy

from .create_bone_data import create_bone_data
from .create_mesh_data import generate_bounding_box, create_mesh_data
from .export_k2_clip import write_block, vlog

##############################
# CLIPS
##############################

MKEY_X, MKEY_Y, MKEY_Z, MKEY_PITCH, MKEY_ROLL, MKEY_YAW, MKEY_VISIBILITY, MKEY_SCALE_X, MKEY_SCALE_Y, MKEY_SCALE_Z, MKEY_COUNT = range(11)


def create_vrts_data(verts, mesh_index):
    data = BytesIO()
    data.write(struct.pack("<i", mesh_index))
    for v in verts:
        data.write(struct.pack("<3f", *v.co))
    return data.getvalue()


def create_face_data(verts, faces, mesh_index):
    data = BytesIO()
    data.write(struct.pack("<i", mesh_index))
    data.write(struct.pack("<i", len(faces)))

    if len(verts) < 255:
        data.write(struct.pack("<B", 1))
        string = '<3B'
    else:
        data.write(struct.pack("<B", 2))
        string = '<3H'
    for f in faces:
        data.write(struct.pack(string, *f))
    return data.getvalue()


def create_tang_data(tang, mesh_index):
    data = BytesIO()
    data.write(struct.pack("<i", mesh_index))
    data.write(struct.pack("<i", 0))  # huh?
    for t in tang:
        data.write(struct.pack('<3f', *list(t)))
    return data.getvalue()


def create_texc_data(texc, mesh_index):
    # if flip_uv:
    for i in range(len(texc)):
        texc[i] = [texc[i][0], 1.0 - texc[i][1]]
    data = BytesIO()
    data.write(struct.pack("<i", mesh_index))
    data.write(struct.pack("<i", 0))  # huh?
    for t in texc:
        data.write(struct.pack("<2f", *t))
    return data.getvalue()


def create_colr_data(colr, mesh_index):
    data = BytesIO()
    data.write(struct.pack("<i", mesh_index))
    for c in colr:
        data.write(struct.pack("<4B", c.r, c.g, c.b, c.a))
    return data.getvalue()


def create_nrml_data(verts, mesh_index):
    data = BytesIO()
    data.write(struct.pack("<i", mesh_index))
    for v in verts:
        data.write(struct.pack("<3f", *v.normal))
    return data.getvalue()


def create_lnk1_data(lnk1, mesh_index, bone_indices):
    data = BytesIO()
    data.write(struct.pack("<i", mesh_index))
    data.write(struct.pack("<i", len(lnk1)))
    for influences in lnk1:
        influences = [inf for inf in influences if inf[0] in bone_indices]
        l = len(influences)
        data.write(struct.pack("<i", l))
        if l > 0:
            data.write(struct.pack('<%df' % l, *[inf[1] for inf in influences]))
            data.write(struct.pack('<%dI' % l, *[bone_indices[inf[0]] for inf in influences]))
    return data.getvalue()


def create_sign_data(mesh_index, sign):
    data = BytesIO()
    data.write(struct.pack("<i", mesh_index))
    data.write(struct.pack("<i", 0))
    for s in sign:
        data.write(struct.pack("<b", s))
    return data.getvalue()


def calc_face_signs(ftexc):
    fsigns = []
    for uv in ftexc:
        if ((uv[1][0] - uv[0][0]) * (uv[2][1] - uv[1][1]) - (uv[1][1] - uv[0][1]) * (uv[2][0] - uv[1][0])) > 0:
            fsigns.append((0, 0, 0))
        else:
            fsigns.append((-1, -1, -1))
    return fsigns


def face_to_vertices(faces, f_data, verts):
    vdata = [None] * len(verts)
    print("blääää___", f_data)
    for fi, f in enumerate(faces):
        print(fi, f)
        for vi, v in enumerate(f):
            print(vi, v)
            vdata[v] = f_data[fi][vi]
    return vdata


def export_k2_mesh(context, filename, apply_mods):
    meshes = []
    armature = None
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            matrix = obj.matrix_world

            if apply_mods:
                deps_graph = context.evaluated_depsgraph_get()
                org_mesh = obj.to_mesh(preserve_all_data_layers=True, depsgraph=deps_graph)
            else:
                org_mesh = obj.data
            bm = bmesh.new()
            bm.from_mesh(org_mesh)
            b_mesh = bm
            bmesh.ops.triangulate(b_mesh, faces=bm.faces)
            b_mesh.transform(matrix)

            meshes.append((obj, b_mesh))
        elif obj.type == 'ARMATURE':
            armature = obj.data
            arm_matrix = obj.matrix_world

    if armature:
        armature.pose_position = 'REST'
        bone_indices, bone_data = create_bone_data(armature, arm_matrix, apply_mods)

    head_data = BytesIO()
    head_data.write(struct.pack("<i", 3))
    head_data.write(struct.pack("<i", len(meshes)))
    head_data.write(struct.pack("<i", 0))
    head_data.write(struct.pack("<i", 0))
    if armature:
        head_data.write(struct.pack("<i", len(armature.bones.values())))
    else:
        head_data.write(struct.pack("<i", 0))

    head_data.write(struct.pack("<6f", *generate_bounding_box([x for _, x in meshes])))  # bounding box

    mesh_index = 0

    file = open(filename, 'wb')
    file.write(b'SMDL')

    write_block(file, 'head', head_data.getvalue())
    write_block(file, 'bone', bone_data)

    write_model_data(bone_indices, file, mesh_index, meshes)


def write_model_data(bone_indices, file, mesh_index, meshes):
    for obj, org_mesh in meshes:
        vert = [vert for vert in org_mesh.verts]
        faces = []
        f_texc = []
        f_tang = []
        f_colr = []
        f_lnk1 = []
        # faces = [[v.index for v in f.verts] for f in org_mesh.faces]
        # f_tang = [[
        # f_texc = org_mesh.uv_layers.active.data

        # if org_mesh.vertexColors:
        # f_colr = [[c for c in f.col] for f in org_mesh.faces]
        # else:
        # f_colr = None
        uv_lay = org_mesh.loops.layers.uv.active
        if not uv_lay:
            f_texc = None
        col_lay = org_mesh.loops.layers.color.active
        if not col_lay:
            f_colr = None
        dvert_lay = org_mesh.verts.layers.deform.active

        f_lnk1 = [vert[dvert_lay].items() for vert in org_mesh.verts]

        for f in org_mesh.faces:
            uv = []
            col = []
            v_index = []
            tang = []
            for loop in f.loops:
                if f_texc is not None:
                    uv.append(loop[uv_lay].uv)
                v_index.append(loop.vert.index)
                if f_colr is not None:
                    col.append(loop[col_lay].color)
                tang.append(loop.calc_tangent())
            if f_texc is not None:
                f_texc.append(uv)
            f_tang.append(tang)
            faces.append(v_index)
            if f_colr:
                f_colr.append(col)

        # duplication
        if f_texc:
            # texc = face_to_vertices_dup(faces,f_texc,vert)
            fsign = calc_face_signs(f_texc)
            # duplication
            # sign = face_to_vertices_dup(faces,fsign,vert)
            sign = face_to_vertices(faces, fsign, vert)
            # recreate texc data due to duplicated vertices
            texc = face_to_vertices(faces, f_texc, vert)
            tang = face_to_vertices(faces, f_tang, vert)
        # Gram-Schmidt orthogonalize
        for i in range(len(vert)):
            # tang[i] = (tang[i] - vert[i].normal * DotVecs(tang[i],vert[i].normal)).normalize()
            tang[i] = (tang[i] - vert[i].normal * tang[i].dot(vert[i].normal))
            tang[i].normalize()

        # lnk1 = face_to_vertices(faces,f_lnk1,vert)
        lnk1 = f_lnk1
        if f_colr is not None:
            colr = face_to_vertices(faces, f_colr, vert)
        else:
            colr = None

        write_block(file, 'org_mesh', create_mesh_data(org_mesh, vert, mesh_index, obj.name.encode('utf8'),
                                                       obj.data.materials[0].name.encode('utf8')))
        write_block(file, 'vrts', create_vrts_data(vert, mesh_index))
        new_indices = {}
        print(bone_indices)
        for group in obj.vertex_groups:
            new_indices[group.index] = bone_indices.index(group.name)
        write_block(file, 'lnk1', create_lnk1_data(lnk1, mesh_index, new_indices))
        if len(faces) > 0:
            write_block(file, 'face', create_face_data(vert, faces, mesh_index))
            if f_texc is not None:
                write_block(file, "texc", create_texc_data(texc, mesh_index))
                for i in range(len(tang)):
                    if sign[i] == 0:
                        tang[i] = -(tang[i].copy())
                write_block(file, "tang", create_tang_data(tang, mesh_index))
                write_block(file, "sign", create_sign_data(mesh_index, sign))
            write_block(file, "nrml", create_nrml_data(vert, mesh_index))
        if f_colr is not None:
            write_block(file, "colr", create_colr_data(colr, mesh_index))
        mesh_index += 1
        vlog('total vertices duplicated: %d' % (len(vert) - len(org_mesh.verts)))