import chunk
import struct

import bpy
import mathutils

from .mat_utils import round_matrix, mat3_to_vec_roll
from .parse_hon_file import log, read_int, vlog, parse_vertices, parse_faces, parse_normals, parse_texc, parse_colr, \
    parse_links, parse_sign, parse_surf


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
    vlog("bounding box: (%f,%f,%f) - (%f,%f,%f)" % struct.unpack("<ffffff", hon_chunk.read(24)))
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
        group_name = ''
        parent_bone_index = read_int(hon_chunk)  # parent bone index

        if version == 3:
            # and the inverse coordinates of the bone
            inv_matrix = mathutils.Matrix((struct.unpack('<3f', hon_chunk.read(12)) + (0.0,),
                                           struct.unpack('<3f', hon_chunk.read(12)) + (0.0,),
                                           struct.unpack('<3f', hon_chunk.read(12)) + (0.0,),
                                           struct.unpack('<3f', hon_chunk.read(12)) + (1.0,)))
            # bone coordinates
            matrix = mathutils.Matrix((struct.unpack('<3f', hon_chunk.read(12)) + (0.0,),
                                       struct.unpack('<3f', hon_chunk.read(12)) + (0.0,),
                                       struct.unpack('<3f', hon_chunk.read(12)) + (0.0,),
                                       struct.unpack('<3f', hon_chunk.read(12)) + (1.0,)))

            name_length = struct.unpack("B", hon_chunk.read(1))[0]  # length of the bone name string
            group_name = hon_chunk.read(name_length)  # bone name

            hon_chunk.read(1)  # zero
        elif version == 1:
            group_name = ''
            pos = hon_chunk.tell() - 4
            b = hon_chunk.read(1)
            while b != '\0':
                group_name += b
                b = hon_chunk.read(1)
            hon_chunk.seek(pos + 0x24)
            inv_matrix = mathutils.Matrix((struct.unpack('<4f', hon_chunk.read(16)),  # transformation matrix 4x4 MAX
                                           struct.unpack('<4f', hon_chunk.read(16)),
                                           struct.unpack('<4f', hon_chunk.read(16)),
                                           struct.unpack('<4f', hon_chunk.read(16))))

            matrix = mathutils.Matrix((struct.unpack('<4f', hon_chunk.read(16)),  # 4x4 Savage transformation matrix
                                       struct.unpack('<4f', hon_chunk.read(16)),
                                       struct.unpack('<4f', hon_chunk.read(16)),
                                       struct.unpack('<4f', hon_chunk.read(16))))

        group_name = group_name.decode()
        log("bone name: %s,parent %d" % (group_name, parent_bone_index))
        bone_names.append(group_name)
        matrix.transpose()
        matrix = round_matrix(matrix, 4)
        pos = matrix.translation
        axis, roll = mat3_to_vec_roll(matrix.to_3x3())
        bone = armature_data.edit_bones.new(group_name)
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
                vlog("bounding box: (%f,%f,%f) - (%f,%f,%f)" % struct.unpack("<ffffff", hon_chunk.read(24)))  # coordinates of the overall container
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

        bpy_mesh = bpy.data.meshes.new(name=mesh_name)
        bpy_mesh.from_pydata(verts, [], faces)
        bpy_mesh.update()

        if material_name is not None:
            bpy_mesh.materials.append(bpy.data.materials.new(material_name))

        if len(texc) > 0:
            if flip_uv:
                for t in range(len(texc)):
                    texc[t] = (texc[t][0], 1 - texc[t][1])

            # Generate texCoords for faces
            tex_coords = []
            for face in faces:
                tex_coords.extend([texc[vert_id] for vert_id in face])

            # uvMain = createTextureLayer("UVMain", bpy_mesh, tex_coords)
            bpy_mesh.uv_layers.new()
            uv_layer = bpy_mesh.uv_layers.active.data

            for tris in bpy_mesh.polygons:
                for loopIndex in range(tris.loop_start, tris.loop_start + tris.loop_total):
                    vertex_index = bpy_mesh.loops[loopIndex].vertex_index
                    uv_layer[loopIndex].uv = tex_coords[vertex_index]

            # uvtex = bpy_mesh.uv_textures.new()
            # uvtex.name = 'UVMain' + mesh_name
            # uvloop = bpy_mesh.uv_layers[-1]
            # for n, f in enumerate(tex_coords):
            #     uvloop.data[n].uv = f

        bpy_object = bpy.data.objects.new('%s_Object' % mesh_name, bpy_mesh)
        # Link object to scene
        scn.collection.objects.link(bpy_object)
        # scn.objects.active = bpy_object
        bpy.context.view_layer.objects.active = bpy_object
        # scn.update()

        if surf or mode != 1:
            bpy_object.display_type = 'WIRE'
        else:
            # vertex groups
            if bone_link >= 0:
                grp = bpy_object.vertex_groups.new(bone_names[bone_link])
                grp.add(list(range(len(bpy_mesh.vertices))), 1.0, 'REPLACE')
            for group_name in v_groups.keys():
                grp = bpy_object.vertex_groups.new(name=group_name)
                for (v, w) in v_groups[group_name]:
                    grp.add([v], w, 'REPLACE')

            mod = bpy_object.modifiers.new('MyRigModif', 'ARMATURE')
            mod.object = rig
            mod.use_bone_envelopes = False
            mod.use_vertex_groups = True

            if False:  # removedoubles:
                bpy_object.select = True
                bpy.ops.object.mode_set(mode='EDIT', toggle=False)
                bpy.ops.mesh.remove_doubles()
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                bpy_object.select = False

            # bpy.context.scene.objects.active = rig
            # rig.select = True
            bpy.context.view_layer.objects.active = rig
            rig.select_set(True)
            bpy.ops.object.mode_set(mode='POSE', toggle=False)
            pose = rig.pose
            for b in pose.bones:
                b.rotation_mode = "QUATERNION"
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            # rig.select = False
            rig.select_set(False)
        # bpy.context.scene.objects.active = None
        bpy.context.view_layer.objects.active = None

    # scn.update()
    return bpy_object, rig
