# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import chunk
import math
import struct

import bpy
from mathutils import Vector, Matrix, Euler

# determines the verbosity of loggin.
#   0 - no logging (fatal errors are still printed)
#   1 - standard logging
#   2 - verbose logging
#   3 - debug level. really boring (stuff like vertex data and verbatim lines)
from .mat_utils import round_matrix, mat3_to_vec_roll
from .parse_hon_file import IMPORT_LOG_LEVEL, log, vlog, read_int, parse_links, parse_vertices, parse_sign, parse_faces, \
    parse_normals, parse_texc, parse_colr, parse_surf


def dlog(msg):
    if IMPORT_LOG_LEVEL >= 3: print(msg)


def err(msg):
    log(msg)


def create_blender_mesh(filename, obj_name, flip_uv):
    file = open(filename, 'rb')
    if not file:
        log("can't open file")
        return
    sig = file.read(4)  # file descriptor
    if sig != b'SMDL':
        err('unknown file signature')
        return

    try:
        hon_chunk = chunk.Chunk(file, bigendian=0, align=0)
    except EOFError:
        log('error reading first chunk')
        return
    if hon_chunk.getname() != b'head':  # section title
        log('file does not start with head chunk!')
        return
    version = read_int(hon_chunk)  # file version
    num_meshes = read_int(hon_chunk)  # number of frames
    num_sprites = read_int(hon_chunk)  # number of sprites?
    num_surfs = read_int(hon_chunk)  # number of surfaces?
    num_bones = read_int(hon_chunk)  # number of bones

    vlog("Version %d" % version)
    vlog("%d mesh(es)" % num_meshes)
    vlog("%d sprites(es)" % num_sprites)
    vlog("%d surfs(es)" % num_surfs)
    vlog("%d bones(es)" % num_bones)
    vlog("bounding box: (%f,%f,%f) - (%f,%f,%f)" % \
         struct.unpack("<ffffff", hon_chunk.read(24)))
    hon_chunk.skip()

    scn = bpy.context.scene

    try:
        hon_chunk = chunk.Chunk(file, bigendian=0, align=0)
    except EOFError:
        log('error reading bone chunk')
        return

    # read bones

    # create armature object
    armature_data = bpy.data.armatures.new('%s_Armature' % obj_name)
    armature_data.show_names = True
    rig = bpy.data.objects.new('%s_Rig' % obj_name, armature_data)
    scn.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    # rig.select = True

    # armature = armature_object.getData()
    # if armature is None:
    # base_name = Blender.sys.basename(file_object.name)
    # armature_name = Blender.sys.splitext(base_name)[0]
    # armature = Blender.Armature.New(armature_name)
    # armature_object.link(armature)
    # armature.drawType = Blender.Armature.STICK
    # armature.envelopes = False
    # armature.vertexGroups = True

    bpy.ops.object.mode_set(mode='EDIT')

    bones = []
    bone_names = []
    parents = []
    for i in range(num_bones):
        name = ''
        parent_bone_index = read_int(hon_chunk)  # parent bone index

        if version == 3:
            # and the inverse coordinates of the bone
            inv_matrix = Matrix((struct.unpack('<3f', hon_chunk.read(12)) + (0.0,),
                                 struct.unpack('<3f', hon_chunk.read(12)) + (0.0,),
                                 struct.unpack('<3f', hon_chunk.read(12)) + (0.0,),
                                 struct.unpack('<3f', hon_chunk.read(12)) + (1.0,)))
            # bone coordinates
            matrix = Matrix((struct.unpack('<3f', hon_chunk.read(12)) + (0.0,),
                             struct.unpack('<3f', hon_chunk.read(12)) + (0.0,),
                             struct.unpack('<3f', hon_chunk.read(12)) + (0.0,),
                             struct.unpack('<3f', hon_chunk.read(12)) + (1.0,)))

            name_length = struct.unpack("B", hon_chunk.read(1))[0]  # length of the bone name string
            name = hon_chunk.read(name_length)  # bone name

            hon_chunk.read(1)  # zero
        elif version == 1:
            name = ''
            pos = hon_chunk.tell() - 4
            b = hon_chunk.read(1)
            while b != '\0':
                name += b
                b = hon_chunk.read(1)
            hon_chunk.seek(pos + 0x24)
            inv_matrix = Matrix((struct.unpack('<4f', hon_chunk.read(16)),  # transformation matrix 4x4 MAX
                                 struct.unpack('<4f', hon_chunk.read(16)),
                                 struct.unpack('<4f', hon_chunk.read(16)),
                                 struct.unpack('<4f', hon_chunk.read(16))))

            matrix = Matrix((struct.unpack('<4f', hon_chunk.read(16)),  # 4x4 Savage transformation matrix
                             struct.unpack('<4f', hon_chunk.read(16)),
                             struct.unpack('<4f', hon_chunk.read(16)),
                             struct.unpack('<4f', hon_chunk.read(16))))

        name = name.decode()
        log("bone name: %s,parent %d" % (name, parent_bone_index))
        bone_names.append(name)
        matrix.transpose()
        matrix = round_matrix(matrix, 4)
        pos = matrix.translation
        axis, roll = mat3_to_vec_roll(matrix.to_3x3())
        bone = armature_data.edit_bones.new(name)
        bone.head = pos
        bone.tail = pos + axis
        bone.roll = roll
        parents.append(parent_bone_index)
        bones.append(bone)
    for i in range(num_bones):
        if parents[i] != -1:
            bones[i].parent = bones[parents[i]]

    hon_chunk.skip()

    bpy.ops.object.mode_set(mode='OBJECT')
    # rig.show_x_ray = True
    rig.show_in_front = True
    rig.update_tag()
    # scn.update()

    try:
        hon_chunk = chunk.Chunk(file, bigendian=0, align=0)
    except EOFError:
        log('error reading mesh chunk')
        return
    while hon_chunk and hon_chunk.getname() in [b'mesh', b'surf']:
        verts = []
        faces = []
        signs = []
        nrml = []
        texc = []
        colors = []
        surf_planes = []
        surf_points = []
        surf_edges = []
        surf_tris = []
        if hon_chunk.getname() == b'mesh':  # section title
            surf = False
            # read mesh chunk
            vlog("mesh index: %d" % read_int(hon_chunk))  # wireframe index
            mode = 1
            if version == 3:
                mode = read_int(hon_chunk)  # is there a modifier Skin: 1 - yes, 2 - no
                vlog("mode: %d" % mode)
                vlog("vertices count: %d" % read_int(hon_chunk))  # number of vertices
                vlog("bounding box: (%f,%f,%f) - (%f,%f,%f)" % \
                     struct.unpack("<ffffff", hon_chunk.read(24)))  # coordinates of the overall container
                bone_link = read_int(hon_chunk)  # количество связей кости?
                vlog("bone link: %d" % bone_link)
                size_name = struct.unpack('B', hon_chunk.read(1))[0]  # length of the line with the name of the framework
                size_mat = struct.unpack('B', hon_chunk.read(1))[0]  # length of the line with the name of the material
                mesh_name = hon_chunk.read(size_name)  # frame name
                hon_chunk.read(1)  # zero
                material_name = hon_chunk.read(size_mat)  # name of material
            elif version == 1:
                bone_link = -1
                pos = hon_chunk.tell() - 4
                b = hon_chunk.read(1)
                mesh_name = ''
                while b != '\0':
                    mesh_name += b
                    b = hon_chunk.read(1)
                hon_chunk.seek(pos + 0x24)

                b = hon_chunk.read(1)
                material_name = ''
                while b != '\0':
                    material_name += b
                    b = hon_chunk.read(1)

            hon_chunk.skip()

            mesh_name = mesh_name.decode()
            material_name = material_name.decode()
            while 1:
                try:
                    hon_chunk = chunk.Chunk(file, bigendian=0, align=0)
                except EOFError:
                    vlog('done reading chunks')
                    hon_chunk = None
                    break
                if hon_chunk.getname() in [b'mesh', b'surf']:
                    break
                elif mode != 1 and False:  # SKIP_NON_PHYSIQUE_MESHES:
                    hon_chunk.skip()
                else:
                    if hon_chunk.getname() == b'vrts':
                        verts = parse_vertices(hon_chunk)
                    elif hon_chunk.getname() == b'face':
                        faces = parse_faces(hon_chunk, version)
                    elif hon_chunk.getname() == b'nrml':
                        nrml = parse_normals(hon_chunk)
                    elif hon_chunk.getname() == b'texc':
                        texc = parse_texc(hon_chunk, version)
                    elif hon_chunk.getname() == b'colr':
                        colors = parse_colr(hon_chunk)
                    elif hon_chunk.getname() == b'lnk1' or hon_chunk.getname() == b'lnk3':
                        v_groups = parse_links(hon_chunk, bone_names)
                    elif hon_chunk.getname() == b'sign':
                        signs = parse_sign(hon_chunk)
                    elif hon_chunk.getname() == b'tang':
                        hon_chunk.skip()
                    else:
                        vlog('unknown chunk: %s' % hon_chunk.chunkname)
                        hon_chunk.skip()
        elif hon_chunk.getname() == b'surf':
            surf_planes, surf_points, surf_edges, surf_tris = parse_surf(hon_chunk)
            print(surf_planes)
            print(surf_points)
            print(surf_edges)
            print(surf_tris)
            verts = surf_points
            faces = surf_tris
            surf = True
            mesh_name = obj_name + '_surf'
            hon_chunk.skip()
            mode = 1
            try:
                hon_chunk = chunk.Chunk(file, bigendian=0, align=0)
            except EOFError:
                vlog('done reading chunks')
                hon_chunk = None

        if mode != 1 and False:  # SKIP_NON_PHYSIQUE_MESHES:
            continue

        msh = bpy.data.meshes.new(name=mesh_name)
        msh.from_pydata(verts, [], faces)
        msh.update()

        if material_name is not None:
            msh.materials.append(bpy.data.materials.new(material_name))

        if len(texc) > 0:
            if flip_uv:
                for t in range(len(texc)):
                    texc[t] = (texc[t][0], 1 - texc[t][1])

            # Generate texCoords for faces
            texcoords = []
            for face in faces:
                texcoords.extend([texc[vert_id] for vert_id in face])

            # uvMain = createTextureLayer("UVMain", msh, texcoords)

            uvtex = msh.uv_textures.new()
            uvtex.name = 'UVMain' + mesh_name
            uvloop = msh.uv_layers[-1]
            for n, f in enumerate(texcoords):
                uvloop.data[n].uv = f

        obj = bpy.data.objects.new('%s_Object' % mesh_name, msh)
        # Link object to scene
        scn.collection.objects.link(obj)
        scn.objects.active = obj
        # scn.update()

        if surf or mode != 1:
            obj.draw_type = 'WIRE'
        else:
            # vertex groups
            if bone_link >= 0:
                grp = obj.vertex_groups.new(bone_names[bone_link])
                grp.add(list(range(len(msh.vertices))), 1.0, 'REPLACE')
            for name in v_groups.keys():
                grp = obj.vertex_groups.new(name)
                for (v, w) in v_groups[name]:
                    grp.add([v], w, 'REPLACE')

            mod = obj.modifiers.new('MyRigModif', 'ARMATURE')
            mod.object = rig
            mod.use_bone_envelopes = False
            mod.use_vertex_groups = True

            if False:  # removedoubles:
                obj.select = True
                bpy.ops.object.mode_set(mode='EDIT', toggle=False)
                bpy.ops.mesh.remove_doubles()
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                obj.select = False

            bpy.context.scene.objects.active = rig
            rig.select = True
            bpy.ops.object.mode_set(mode='POSE', toggle=False)
            pose = rig.pose
            for b in pose.bones:
                b.rotation_mode = "QUATERNION"
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            rig.select = False
        bpy.context.scene.objects.active = None

    # scn.update()
    return (obj, rig)


##############################
# CLIPS
##############################


MKEY_X, MKEY_Y, MKEY_Z, MKEY_PITCH, MKEY_ROLL, MKEY_YAW, MKEY_VISIBILITY, MKEY_SCALE_X, MKEY_SCALE_Y, MKEY_SCALE_Z = range(10)


def bone_depth(bone):
    if not bone.parent:
        return 0
    else:
        return 1 + bone_depth(bone.parent)


def get_transform_matrix(motions, bone, i, version):
    motion = motions[bone.name]
    # translation
    if i >= len(motion[MKEY_X]):
        x = motion[MKEY_X][-1]
    else:
        x = motion[MKEY_X][i]

    if i >= len(motion[MKEY_Y]):
        y = motion[MKEY_Y][-1]
    else:
        y = motion[MKEY_Y][i]

    if i >= len(motion[MKEY_Z]):
        z = motion[MKEY_Z][-1]
    else:
        z = motion[MKEY_Z][i]

    # rotation
    if i >= len(motion[MKEY_PITCH]):
        rx = motion[MKEY_PITCH][-1]
    else:
        rx = motion[MKEY_PITCH][i]

    if i >= len(motion[MKEY_ROLL]):
        ry = motion[MKEY_ROLL][-1]
    else:
        ry = motion[MKEY_ROLL][i]

    if i >= len(motion[MKEY_YAW]):
        rz = motion[MKEY_YAW][-1]
    else:
        rz = motion[MKEY_YAW][i]

    # scaling
    if version == 1:  # if the file version is 1, then
        if i >= len(motion[MKEY_SCALE_X]):
            sx = motion[MKEY_SCALE_X][-1]
        else:
            sx = motion[MKEY_SCALE_X][i]
        sy = sz = sx
    else:  # if the file version is not 1, then
        if i >= len(motion[MKEY_SCALE_X]):
            sx = motion[MKEY_SCALE_X][-1]
        else:
            sx = motion[MKEY_SCALE_X][i]

        if i >= len(motion[MKEY_SCALE_Y]):
            sy = motion[MKEY_SCALE_Y][-1]
        else:
            sy = motion[MKEY_SCALE_Y][i]

        if i >= len(motion[MKEY_SCALE_Z]):
            sz = motion[MKEY_SCALE_Z][-1]
        else:
            sz = motion[MKEY_SCALE_Z][i]
    scale = Vector([sx, sy, sz])
    bone_rotation_matrix = Euler((math.radians(rx), math.radians(ry), math.radians(rz)), 'YXZ').to_matrix().to_4x4()

    bone_rotation_matrix = Matrix.Translation(Vector((x, y, z))) * bone_rotation_matrix

    return bone_rotation_matrix, scale


def animate_bone(name, pose, motions, num_frames, armature, arm_ob, version):
    if name not in armature.bones.keys():
        log('%s not found in armature' % name)
        return
    motion = motions[name]
    bone = armature.bones[name]
    bone_rest_matrix = Matrix(bone.matrix_local)

    if bone.parent is not None:
        parent_bone = bone.parent
        parent_rest_bone_matrix = Matrix(parent_bone.matrix_local)
        parent_rest_bone_matrix.invert()
        bone_rest_matrix = parent_rest_bone_matrix * bone_rest_matrix

    bone_rest_matrix_inv = Matrix(bone_rest_matrix)
    bone_rest_matrix_inv.invert()

    pbone = pose.bones[name]
    prev_euler = Euler()
    for i in range(0, num_frames):
        transform, size = get_transform_matrix(motions, bone, i, version)
        transform = bone_rest_matrix_inv * transform
        pbone.rotation_quaternion = transform.to_quaternion()
        pbone.location = transform.to_translation()
        pbone.keyframe_insert(data_path='rotation_quaternion', frame=i)
        pbone.keyframe_insert(data_path='location', frame=i)


def create_blender_clip(filename, clip_name):
    file = open(filename, 'rb')  # open the file for reading
    if not file:  # if the file doesn't exist then
        log("can't open file")  # output to the log: "unable to open file"
        return
    sig = file.read(4)  # read the first 4 bytes - file descriptor
    if sig != b'CLIP':  # if the descriptor is not CLIP, then
        err('unknown file signature')  # we display an error: "unknown file signature"
        return

    try:
        clip_chunk = chunk.Chunk(file, bigendian=0, align=0)
    except EOFError:
        log('error reading first chunk')
        return
    version = read_int(clip_chunk)  # read the file version
    num_bones = read_int(clip_chunk)  # read the number of bones
    num_frames = read_int(clip_chunk)  # read the number of frames
    vlog("version: %d" % version)  # output the version of the file to the log
    vlog("num bones: %d" % num_bones)  # log the number of bones
    vlog("num frames: %d" % num_frames)  # log the number of frames

    # objList = Blender.Object.GetSelected()
    # if len(objList) != 1:
    # err('select needed armature only')
    # armOb = objList[0]
    # action = Blender.Armature.NLA.NewAction(clipname)
    # action.setActive(armOb)
    # pose = armOb.getPose()
    # armature = armOb.getData()
    armOb = bpy.context.selected_objects[0]
    if not armOb.animation_data:
        armOb.animation_data_create()
    armature = armOb.data
    action = bpy.data.actions.new(name=clip_name)
    armOb.animation_data.action = action
    pose = armOb.pose

    bone_index = -1  # create a variable bone_index with a value of -1
    motions = {}  # creating a dictionary motions

    while 1:  # execute the loop body as long as the loop condition is true
        try:  # run the try statement
            clip_chunk = chunk.Chunk(file, bigendian=0, align=0)  # read the block name
        except EOFError:  # if during the execution of the try statement we stumbled upon the end of the file, then
            break  # terminate the cycle ahead of schedule
        if version == 1:  # if the file version is 1, then
            name = clip_chunk.read(32)  # read the next 32 bytes - the name of the bone
            if '\0' in name:  # if, while reading, they stumbled upon the value 0, then
                name = name[:name.index('\0')]  # save the read bytes into the name variable
        boneindex = read_int(clip_chunk)  # read the bone index
        keytype = read_int(clip_chunk)  # read the animation key type
        numkeys = read_int(clip_chunk)  # read the number of animation keys
        if version > 1:  # if the file version is greater than 1, then
            namelength = struct.unpack("B", clip_chunk.read(1))[0]  # read the length of the bone name
            name = clip_chunk.read(namelength)  # we read the name of the bone taking into account its length
            clip_chunk.read(1)  # read 1 byte - value 0
        name = name.decode("utf8")  # recode the bone name in UTF-8 encoding

        if name not in motions:  # if the name of the bone is not in the motions dictionary, then
            motions[name] = {}
        dlog("%s,boneindex: %d,keytype: %d,numkeys: %d" % \
             (name, boneindex, keytype, numkeys))
        if keytype == MKEY_VISIBILITY:  # if the key type is visibility, then
            data = struct.unpack("%dB" % numkeys, clip_chunk.read(numkeys))  # read Byte
        else:  # if not, then
            data = struct.unpack("<%df" % numkeys, clip_chunk.read(numkeys * 4))  # read Float
        motions[name][keytype] = list(data)  # convert the data string to a list
        clip_chunk.skip()  # skip the error test
    # file read, now animate that bastard!
    for bone_name in motions:  # for each bone in the motions dictionary do
        animate_bone(bone_name, pose, motions, num_frames, armature, armOb, version)
    # pose.update()


def readclip(filepath):
    obj_name = bpy.path.display_name_from_filepath(filepath)
    create_blender_clip(filepath, obj_name)


def read(filepath, flipuv):
    obj_name = bpy.path.display_name_from_filepath(filepath)
    create_blender_mesh(filepath, obj_name, flipuv)

# package manages registering
