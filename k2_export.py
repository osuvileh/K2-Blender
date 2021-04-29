# Copyright (c) 2010 Anton Romanov
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
import bpy, bmesh
from io import BytesIO
import struct

# determines the verbosity of loggin.
#   0 - no logging (fatal errors are still printed)
#   1 - standard logging
#   2 - verbose logging
#   3 - debug level. really boring (stuff like vertex data and verbatim lines)
from bpy.types import Depsgraph
from mathutils import Matrix
import bmesh

IMPORT_LOG_LEVEL = 3


def log(msg):
    if IMPORT_LOG_LEVEL >= 1:
        print(msg)


def vlog(msg):
    if IMPORT_LOG_LEVEL >= 2:
        print(msg)


def dlog(msg):
    if IMPORT_LOG_LEVEL >= 3:
        print(msg)


def err(msg):
    log(msg)


def bone_depth(bone):
    if not bone.parent:
        return 0
    else:
        return 1 + bone_depth(bone.parent)


def generate_bbox(meshes):
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
    mesh_data.write(struct.pack("<6f", *generate_bbox([mesh])))  # bounding box
    mesh_data.write(struct.pack("<i", -1))  # bone link... dunno... TODO
    mesh_data.write(struct.pack("<B", len(name)))
    mesh_data.write(struct.pack("<B", len(m_name)))
    mesh_data.write(name)
    mesh_data.write(struct.pack("<B", 0))
    mesh_data.write(m_name)
    mesh_data.write(struct.pack("<B", 0))
    return mesh_data.getvalue()


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


def write_block(file, name, data):
    file.write(name.encode('utf8')[:4])
    file.write(struct.pack("<i", len(data)))
    file.write(data)


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


def face_to_vertices_dup(faces, fdata, verts):
    v_data = [None] * len(verts)
    for fi, f in enumerate(faces):
        for vi, v in enumerate(f):
            if v_data[v] is None or v_data[v] == fdata[fi][vi]:
                v_data[v] = fdata[fi][vi]
            else:
                new_ind = len(verts)
                verts.append(verts[v])
                faces[fi][vi] = new_ind
                v_data.append(fdata[fi][vi])
    return v_data


def face_to_vertices(faces, f_data, verts):
    vdata = [None] * len(verts)
    print("blääää___", f_data)
    for fi, f in enumerate(faces):
        print(fi, f)
        for vi, v in enumerate(f):
            print(vi, v)
            vdata[v] = f_data[fi][vi]
    return vdata


def create_bone_data(armature, arm_matrix, transform):
    bones = []
    for bone in sorted(armature.bones.values(), key=bone_depth):
        bones.append(bone.name)
    bone_data = BytesIO()

    for name in bones:
        bone = armature.bones[name]
        base = bone.matrix_local.copy()
        if transform:
            base @= arm_matrix
        base_inv = base.copy()
        base_inv.invert()
        if bone.parent:
            parent_index = bones.index(bone.parent.name)
        else:
            parent_index = -1
        base_inv.transpose()
        base.transpose()
        # parent bone index
        bone_data.write(struct.pack("<i", parent_index))
        # inverted matrix
        bone_data.write(struct.pack('<12f', *sum([list(row[0:3]) for row in base_inv], [])))
        # base matrix
        bone_data.write(struct.pack('<12f', *sum([list(row[0:3]) for row in base], [])))
        # bone name
        name = name.encode('utf8')
        bone_data.write(struct.pack("B", len(name)))
        bone_data.write(name)
        bone_data.write(struct.pack("B", 0))
    return bones, bone_data.getvalue()


def export_k2_mesh(context, filename, apply_mods):
    meshes = []
    armature = None
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            matrix = obj.matrix_world

            if apply_mods:
                # org_mesh = obj.to_mesh(True, depsgraph="PREVIEW")
                deps_graph = context.evaluated_depsgraph_get()
                # org_mesh = obj.to_mesh(obj.evaluated_get(deps_graph), preserve_all_data_layers=True, depsgraph=deps_graph)
                org_mesh = obj.to_mesh(preserve_all_data_layers=True, depsgraph=deps_graph)
                # org_mesh = obj.to_mesh(True, depsgraph=Depsgraph())
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

    head_data.write(struct.pack("<6f", *generate_bbox([x for _, x in meshes])))  # bounding box

    mesh_index = 0

    file = open(filename, 'wb')
    file.write(b'SMDL')

    write_block(file, 'head', head_data.getvalue())
    write_block(file, 'bone', bone_data)

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


##############################
# CLIPS
##############################

MKEY_X, MKEY_Y, MKEY_Z, \
MKEY_PITCH, MKEY_ROLL, MKEY_YAW, \
MKEY_VISIBILITY, \
MKEY_SCALE_X, MKEY_SCALE_Y, MKEY_SCALE_Z, \
MKEY_COUNT \
    = range(11)

from math import sqrt, atan2, degrees


def clip_bone(file, bone_name, motion, index):
    for key_type in range(MKEY_COUNT):
        key_data = BytesIO()
        key = motion[key_type]
        # if key_type != MKEY_VISIBILITY:
        # key = map(lambda k: round(k,ROUND_KEYS), key)
        if min(key) == max(key):
            key = [key[0]]
        num_keys = len(key)
        key_data.write(struct.pack("<i", index))
        key_data.write(struct.pack("<i", key_type))
        key_data.write(struct.pack("<i", num_keys))
        key_data.write(struct.pack("B", len(bone_name)))
        key_data.write(bone_name)
        key_data.write(struct.pack("B", 0))
        if key_type == MKEY_VISIBILITY:
            key_data.write(struct.pack('%dB' % num_keys, *key))
        else:
            key_data.write(struct.pack('<%df' % num_keys, *key))
        write_block(file, 'bmtn', key_data.getvalue())


def export_k2_clip(filename, transform, frame_start, frame_end):
    obj_list = bpy.context.selected_objects
    if len(obj_list) != 1 or obj_list[0].type != 'ARMATURE':
        err('Select needed armature only')
        return
    arm_ob = obj_list[0]
    motions = {}
    vlog('baking animation')
    armature = arm_ob.data
    if transform:
        worldmat = arm_ob.matrix_world
    else:
        worldmat = Matrix([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
    scene = bpy.context.scene
    pose = arm_ob.pose

    for frame in range(frame_start, frame_end):
        scene.frame_set(frame)
        for bone in pose.bones.values():
            matrix = bone.matrix
            if bone.parent:
                matrix = matrix * (bone.parent.matrix.copy().inverted())
            else:
                matrix = matrix * worldmat
            if bone.name not in motions:
                motions[bone.name] = []
                for i in range(MKEY_COUNT):
                    motions[bone.name].append([])
            motion = motions[bone.name]

            translation = matrix.translation
            rotation = matrix.to_euler('YXZ')
            scale = matrix.to_scale()
            visibility = 255

            motion[MKEY_X].append(translation[0])
            motion[MKEY_Y].append(translation[1])
            motion[MKEY_Z].append(translation[2])

            motion[MKEY_PITCH].append(-degrees(rotation[0]))
            motion[MKEY_ROLL].append(-degrees(rotation[1]))
            motion[MKEY_YAW].append(-degrees(rotation[2]))

            motion[MKEY_SCALE_X].append(scale[0])
            motion[MKEY_SCALE_Y].append(scale[1])
            motion[MKEY_SCALE_Z].append(scale[2])

            motion[MKEY_VISIBILITY].append(visibility)

    head_data = BytesIO()
    head_data.write(struct.pack("<i", 2))
    head_data.write(struct.pack("<i", len(motions.keys())))
    head_data.write(struct.pack("<i", frame_end - frame_start))

    file = open(filename, 'wb')
    file.write(b'CLIP')
    write_block(file, 'head', head_data.getvalue())

    index = 0
    for bone_name in sorted(armature.bones.keys(), key=lambda x: bone_depth(armature.bones[x])):
        clip_bone(file, bone_name.encode('utf8'), motions[bone_name], index)
        index += 1
    file.close()
