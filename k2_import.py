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
from mathutils import Vector, Matrix, Euler
import math
# determines the verbosity of loggin.
#   0 - no logging (fatal errors are still printed)
#   1 - standard logging
#   2 - verbose logging
#   3 - debug level. really boring (stuff like vertex data and verbatim lines)
IMPORT_LOG_LEVEL = 3

def log(msg):
    if IMPORT_LOG_LEVEL >= 1: print (msg)

def vlog(msg):
    if IMPORT_LOG_LEVEL >= 2: print (msg)

def dlog(msg):
    if IMPORT_LOG_LEVEL >= 3: print (msg)

def err(msg):
    log(msg)

import bpy
import bmesh
import struct,chunk
import itertools

from bpy.props import *

def read_int(honchunk):
    return struct.unpack("<i",honchunk.read(4))[0]
def read_float(honchunk):
    return struct.unpack("<f",honchunk.read(4))[0]

def parse_links(honchunk,bone_names):
    mesh_index = read_int(honchunk)
    numverts = read_int(honchunk)
    log("links")
    vlog("mesh index: %d" % mesh_index)
    vlog("vertices number: %d" % numverts)
    vgroups = {}
    for i in range(numverts):
        num_weights = read_int(honchunk)
        if num_weights > 0:
            weights = struct.unpack("<%df" % num_weights,honchunk.read(num_weights * 4))
            indexes = struct.unpack("<%dI" % num_weights,honchunk.read(num_weights * 4))
        else:
            weights = indexes = []
            vlog("Missing weights!")
        for ii, index in enumerate(indexes):
            name = bone_names[index]
            if name not in vgroups:
                vgroups[name] = list()
            vgroups[name].append( (i,weights[ii] ) )
    honchunk.skip()
    return vgroups

def parse_vertices(honchunk):
    vlog('parsing vertices chunk')
    numverts = (honchunk.chunksize - 4)/12
    numverts = int(numverts)
    vlog('%d vertices' % numverts)
    meshindex = read_int(honchunk)
    return [struct.unpack("<3f", honchunk.read(12)) for i in range(int(numverts))]
def parse_sign(honchunk):
    vlog('parsing sign chunk')
    numverts = (honchunk.chunksize - 8)
    meshindex = read_int(honchunk)
    vlog(read_int(honchunk)) # huh?
    return [struct.unpack("<b", honchunk.read(1)) for i in range(numverts)]
def parse_faces(honchunk,version):
    vlog('parsing faces chunk')
    meshindex = read_int(honchunk)
    numfaces = read_int(honchunk)
    vlog('%d faces' % numfaces)
    if version == 3:
        size = struct.unpack('B',honchunk.read(1))[0]
    elif version == 1:
        size = 4
    if size == 2:
        return [struct.unpack("<3H", honchunk.read(6)) for i in range(numfaces)]
    elif size ==1:
        return [struct.unpack("<3B", honchunk.read(3)) for i in range(numfaces)]
    elif size == 4:
        return [struct.unpack("<3I", honchunk.read(12)) for i in range(numfaces)]
    else:
        log("unknown size for faces:%d" % size)
        return []
def parse_normals(honchunk):
    vlog('parsing normals chunk')
    numverts = (honchunk.chunksize - 4)/12
    numverts = int(numverts)
    vlog('%d normals' % numverts)
    meshindex = read_int(honchunk)
    return [struct.unpack("<3f", honchunk.read(12)) for i in range(numverts)]
def parse_texc(honchunk,version):
    vlog('parsing uv texc chunk')
    numverts = int((honchunk.chunksize - 4)/8)
    numverts = int(numverts)
    vlog('%d texc' % numverts)
    meshindex = read_int(honchunk)
    if version == 3:
        vlog(read_int(honchunk)) # huh?
    return [struct.unpack("<2f", honchunk.read(8)) for i in range(numverts)]   
def parse_colr(honchunk):
    vlog('parsing vertex colours chunk')
    numverts = (honchunk.chunksize - 4)/4
    numverts = int(numverts)
    meshindex = read_int(honchunk)
    return [struct.unpack("<4B", honchunk.read(4)) for i in range(numverts)]


def parse_surf(honchunk):
    vlog('parsing surf chunk')
    surfindex = read_int(honchunk)
    num_planes = read_int(honchunk)
    num_points = read_int(honchunk)
    num_edges = read_int(honchunk)
    num_tris = read_int(honchunk)
    #BMINf,BMAXf,FLAGSi
    honchunk.read(4*3+4*3+4)
    return \
            [struct.unpack("<4f", honchunk.read(4*4)) for i in range(num_planes)],\
            [struct.unpack("<3f", honchunk.read(4*3)) for i in range(num_points)],\
            [struct.unpack("<6f", honchunk.read(4*6)) for i in range(num_edges)],\
            [struct.unpack("<3I", honchunk.read(4*3)) for i in range(num_tris)]

def roundVector(vec,dec=17):
    fvec=[]
    for v in vec:
        fvec.append(round(v,dec))
    return Vector(fvec)

def roundMatrix(mat,dec=17):
    fmat = []
    for row in mat:
        fmat.append(roundVector(row,dec))
    return Matrix(fmat)

def vec_roll_to_mat3(vec, roll):
    #Direct copy from https://coder-question.com/cq-blog/494393 
    #port of the updated C function from armature.c
    #https://developer.blender.org/T39470
    #note that C accesses columns first, so all matrix indices are swapped compared to the C version

    nor = vec.normalized()
    THETA_THRESHOLD_NEGY = 1.0e-9
    THETA_THRESHOLD_NEGY_CLOSE = 1.0e-5

    #create a 3x3 matrix
    bMatrix = Matrix().to_3x3()

    theta = 1.0 + nor[1]

    if (theta > THETA_THRESHOLD_NEGY_CLOSE) or ((nor[0] or nor[2]) and theta > THETA_THRESHOLD_NEGY):

        bMatrix[1][0] = -nor[0]
        bMatrix[0][1] = nor[0]
        bMatrix[1][1] = nor[1]
        bMatrix[2][1] = nor[2]
        bMatrix[1][2] = -nor[2]
        if theta > THETA_THRESHOLD_NEGY_CLOSE:
            #If nor is far enough from -Y, apply the general case.
            bMatrix[0][0] = 1 - nor[0] * nor[0] / theta
            bMatrix[2][2] = 1 - nor[2] * nor[2] / theta
            bMatrix[0][2] = bMatrix[2][0] = -nor[0] * nor[2] / theta

        else:
            #If nor is too close to -Y, apply the special case.
            theta = nor[0] * nor[0] + nor[2] * nor[2]
            bMatrix[0][0] = (nor[0] + nor[2]) * (nor[0] - nor[2]) / -theta
            bMatrix[2][2] = -bMatrix[0][0]
            bMatrix[0][2] = bMatrix[2][0] = 2.0 * nor[0] * nor[2] / theta

    else:
        #If nor is -Y, simple symmetry by Z axis.
        bMatrix = Matrix().to_3x3()
        bMatrix[0][0] = bMatrix[1][1] = -1.0

    #Make Roll matrix
    rMatrix = Matrix.Rotation(roll, 3, nor)

    #Combine and output result
    mat = rMatrix * bMatrix
    return mat

def mat3_to_vec_roll(mat):
    """Computes rotation axis and its roll from a Matrix.

    :param mat: Matrix
    :type mat: Matrix
    :return: Rotation axis and roll
    :rtype: Vector and float
    """
    mat_3x3 = mat.to_3x3()
    # print('  mat_3x3:\n%s' % str(mat_3x3))
    axis = Vector(mat_3x3.col[1]).normalized()
    # print('  axis:\n%s' % str(axis))
    # print('  mat_3x3[2]:\n%s' % str(mat_3x3.col[2]))

    zero_angle_matrix = vec_roll_to_mat3(axis, 0)
    delta_matrix = zero_angle_matrix.inverted() * mat_3x3
    angle = math.atan2(delta_matrix.col[2][0], delta_matrix.col[2][2])
    return axis, angle 

def CreateBlenderMesh(filename, objname,flipuv):
    file = open(filename,'rb')
    if not file:
        log("can't open file")
        return
    sig = file.read(4)
    if sig != b'SMDL':
        err('unknown file signature')
        return

    try:
        honchunk = chunk.Chunk(file,bigendian=0,align=0)
    except EOFError:
        log('error reading first chunk')
        return
    if honchunk.getname() != b'head':
        log('file does not start with head chunk!')
        return
    version = read_int(honchunk)
    num_meshes = read_int(honchunk)
    num_sprites = read_int(honchunk)
    num_surfs = read_int(honchunk)
    num_bones = read_int(honchunk)

    vlog("Version %d" % version)
    vlog("%d mesh(es)" % num_meshes)
    vlog("%d sprites(es)" % num_sprites)
    vlog("%d surfs(es)" % num_surfs)
    vlog("%d bones(es)" % num_bones)
    vlog("bounding box: (%f,%f,%f) - (%f,%f,%f)" % \
        struct.unpack("<ffffff", honchunk.read(24)))
    honchunk.skip()

    scn= bpy.context.scene

    try:
        honchunk = chunk.Chunk(file,bigendian=0,align=0)
    except EOFError:
        log('error reading bone chunk')
        return


    #read bones

    #create armature object
    armature_data = bpy.data.armatures.new('%s_Armature' % objname)
    armature_data.show_names = True
    rig = bpy.data.objects.new('%s_Rig' % objname, armature_data)
    scn.objects.link(rig)
    scn.objects.active = rig
    rig.select = True

    # armature = armature_object.getData()
    # if armature is None:
    # base_name = Blender.sys.basename(file_object.name)
    # armature_name = Blender.sys.splitext(base_name)[0]
    # armature = Blender.Armature.New(armature_name)
    # armature_object.link(armature)
    #armature.drawType = Blender.Armature.STICK
    #armature.envelopes = False
    #armature.vertexGroups = True
       
    bpy.ops.object.mode_set(mode='EDIT')

    bones = []
    bone_names = []
    parents = []
    for i in range(num_bones):
        name = ''
        parent_bone_index = read_int(honchunk)

        if version == 3:
            inv_matrix = Matrix((struct.unpack('<3f', honchunk.read(12)) + (0.0,),
                         struct.unpack('<3f', honchunk.read(12)) + (0.0,),
                         struct.unpack('<3f', honchunk.read(12)) + (0.0,),
                         struct.unpack('<3f', honchunk.read(12)) + (1.0,)))

            matrix = Matrix((struct.unpack('<3f', honchunk.read(12)) + (0.0,),
                     struct.unpack('<3f', honchunk.read(12)) + (0.0,),
                     struct.unpack('<3f', honchunk.read(12)) + (0.0,),
                     struct.unpack('<3f', honchunk.read(12)) + (1.0,)))

            name_length = struct.unpack("B" , honchunk.read(1))[0]
            name = honchunk.read(name_length)

            honchunk.read(1) #zero
        elif version == 1:
            name = ''
            pos = honchunk.tell() - 4
            b = honchunk.read(1)
            while b != '\0':
                name += b
                b = honchunk.read(1)
            honchunk.seek(pos + 0x24)
            inv_matrix = Matrix((struct.unpack('<4f', honchunk.read(16)),
                         struct.unpack('<4f', honchunk.read(16)),
                         struct.unpack('<4f', honchunk.read(16)),
                         struct.unpack('<4f', honchunk.read(16))))

            matrix = Matrix((struct.unpack('<4f', honchunk.read(16)),
                     struct.unpack('<4f', honchunk.read(16)),
                     struct.unpack('<4f', honchunk.read(16)),
                     struct.unpack('<4f', honchunk.read(16))))

        name = name.decode()
        bone_names.append(name)
        matrix.transpose()
        #matrix = roundMatrix(matrix,4)
        pos = matrix.translation
        axis, roll = mat3_to_vec_roll(matrix)

        bone = armature_data.edit_bones.new(name)
        bone.head = pos
        bone.tail = pos + axis
        bone.roll = roll
        log("bone name: %s,parent %d, roll %f" % (name,parent_bone_index, roll))
        parents.append(parent_bone_index)
        bones.append(bone)
    for i in range(num_bones):
        if parents[i] != -1:
            bones[i].parent = bones[parents[i]]

    honchunk.skip()

    bpy.ops.object.mode_set(mode='OBJECT')
    rig.show_x_ray = True
    rig.update_tag()
    scn.update()

    try:
        honchunk = chunk.Chunk(file,bigendian=0,align=0)
    except EOFError:
        log('error reading mesh chunk')
        return
    while honchunk and honchunk.getname() in [b'mesh', b'surf']:
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
        if honchunk.getname() == b'mesh':
            surf = False
            #read mesh chunk
            vlog("mesh index: %d" % read_int(honchunk))
            mode = 1
            if version == 3:
                mode = read_int(honchunk)
                vlog("mode: %d" % mode)
                vlog("vertices count: %d" % read_int(honchunk))
                vlog("bounding box: (%f,%f,%f) - (%f,%f,%f)" % \
                    struct.unpack("<ffffff", honchunk.read(24)))
                bone_link = read_int(honchunk)
                vlog("bone link: %d" % bone_link)
                sizename = struct.unpack('B',honchunk.read(1))[0]
                sizemat = struct.unpack('B',honchunk.read(1))[0]
                meshname = honchunk.read(sizename)
                honchunk.read(1) # zero
                materialname = honchunk.read(sizemat)
            elif version == 1:
                bone_link = -1
                pos = honchunk.tell() - 4
                b = honchunk.read(1)
                meshname = ''
                while b != '\0':
                    meshname += b
                    b = honchunk.read(1)
                honchunk.seek(pos + 0x24)

                b = honchunk.read(1)
                materialname = ''
                while b != '\0':
                    materialname += b
                    b = honchunk.read(1)

            honchunk.skip()

            meshname = meshname.decode()
            materialname = materialname.decode()
            while 1:
                try:
                    honchunk = chunk.Chunk(file,bigendian=0,align=0)
                except EOFError:
                    vlog('done reading chunks')
                    honchunk = None
                    break
                if honchunk.getname()  in [b'mesh', b'surf']:
                    break
                elif mode != 1 and False:#SKIP_NON_PHYSIQUE_MESHES:
                    honchunk.skip()
                else:
                    if honchunk.getname() == b'vrts':
                        verts = parse_vertices(honchunk)
                    elif honchunk.getname() == b'face':
                        faces = parse_faces(honchunk,version)
                    elif honchunk.getname() == b'nrml':
                        nrml = parse_normals(honchunk)
                    elif honchunk.getname() == b'texc':
                        texc = parse_texc(honchunk,version)
                    elif honchunk.getname() == b'colr':
                        colors = parse_colr(honchunk)
                    elif honchunk.getname() == b'lnk1' or honchunk.getname() == b'lnk3':
                        vgroups = parse_links(honchunk,bone_names)
                    elif honchunk.getname() == b'sign':
                        signs = parse_sign(honchunk)
                    elif honchunk.getname() == b'tang':
                        honchunk.skip()
                    else:
                        vlog('unknown chunk: %s' % honchunk.chunkname)
                        honchunk.skip()
        elif honchunk.getname() == b'surf':
            surf_planes,surf_points,surf_edges,surf_tris = parse_surf(honchunk)
            print(surf_planes)
            print(surf_points)
            print(surf_edges)
            print(surf_tris)
            verts = surf_points
            faces = surf_tris
            surf = True
            meshname = objname + '_surf'
            honchunk.skip()
            mode = 1
            try:
                honchunk = chunk.Chunk(file,bigendian=0,align=0)
            except EOFError:
                vlog('done reading chunks')
                honchunk = None

        if mode != 1 and False:#SKIP_NON_PHYSIQUE_MESHES:
            continue
        
        msh = bpy.data.meshes.new(name=meshname)
        msh.from_pydata(verts, [], faces)
        msh.update()

           
        if materialname is not None:
            msh.materials.append(bpy.data.materials.new(materialname))

        if len(texc) > 0:
            if flipuv:
                for t in range(len(texc)):
                    texc[t] = ( texc[t][0], 1-texc[t][1] )


            # Generate texCoords for faces
            texcoords = []
            for face in faces:
                texcoords.extend( [ texc[vert_id] for vert_id in face ] )
                
            #uvMain = createTextureLayer("UVMain", msh, texcoords)
                            
            uvtex = msh.uv_textures.new()
            uvtex.name = 'UVMain' + meshname
            uvloop = msh.uv_layers[-1]
            for n,f in enumerate(texcoords):
                uvloop.data[n].uv = f


        obj = bpy.data.objects.new('%s_Object' % meshname, msh)
        # Link object to scene
        scn.objects.link(obj)
        scn.objects.active = obj
        scn.update()

        if surf or mode != 1:
            obj.draw_type = 'WIRE'
        else:
            #vertex groups
            if bone_link >=0 :
                grp = obj.vertex_groups.new(bone_names[bone_link])
                grp.add(list(range(len(msh.vertices))),1.0,'REPLACE')
            for name in vgroups.keys():
                grp = obj.vertex_groups.new(name)
                for (v, w) in vgroups[name]:
                    grp.add([v], w, 'REPLACE')
            
            mod = obj.modifiers.new('MyRigModif', 'ARMATURE')
            mod.object = rig
            mod.use_bone_envelopes = False
            mod.use_vertex_groups = True


            if False:#removedoubles:
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


    scn.update()
    return ( obj, rig )
############################## 
#CLIPS
##############################
    

MKEY_X,MKEY_Y,MKEY_Z,\
MKEY_PITCH,MKEY_ROLL,MKEY_YAW,\
MKEY_VISIBILITY,\
MKEY_SCALE_X,MKEY_SCALE_Y,MKEY_SCALE_Z \
    = range(10)

def bone_depth(bone):
    if not bone.parent:
        return 0
    else:
        return 1+bone_depth(bone.parent)
        
def getTransformMatrix(motions,bone,i,version):
    motion = motions[bone.name]
    #translation
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

    #rotation
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
    
    #scaling
    if version == 1:
        if i >= len(motion[MKEY_SCALE_X]):
            sx = motion[MKEY_SCALE_X][-1]
        else:
            sx = motion[MKEY_SCALE_X][i]
        sy = sz = sx
    else:
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
    scale = Vector([sx,sy,sz])
    bone_rotation_matrix = Euler((math.radians(rx),math.radians(ry),math.radians(rz)),'YXZ').to_matrix().to_4x4()

    bone_rotation_matrix = Matrix.Translation(\
        Vector((x,y,z))) * bone_rotation_matrix

    return bone_rotation_matrix,scale
    
def AnimateBone(name,pose,motions,num_frames,armature,armOb,version):
    if name not in armature.bones.keys():
        log ('%s not found in armature' % name)
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
        transform,size = getTransformMatrix(motions,bone,i,version)
        transform = bone_rest_matrix_inv * transform
        pbone.rotation_quaternion = transform.to_quaternion()
        pbone.location =  (transform).to_translation()
        pbone.keyframe_insert(data_path='rotation_quaternion',frame=i)
        pbone.keyframe_insert(data_path='location',frame=i)


def CreateBlenderClip(filename,clipname):
    file = open(filename,'rb')
    if not file:
        log("can't open file")
        return
    sig = file.read(4)
    if sig != b'CLIP':
        err('unknown file signature')
        return

    try:
        clipchunk = chunk.Chunk(file,bigendian=0,align=0)
    except EOFError:
        log('error reading first chunk')
        return
    version = read_int(clipchunk)
    num_bones = read_int(clipchunk)
    num_frames = read_int(clipchunk)
    vlog ("version: %d" % version)
    vlog ("num bones: %d" % num_bones)
    vlog ("num frames: %d" % num_frames)
    

    #objList = Blender.Object.GetSelected()
    #if len(objList) != 1:
        #err('select needed armature only')
    #armOb = objList[0]
    #action = Blender.Armature.NLA.NewAction(clipname)
    #action.setActive(armOb)
    #pose = armOb.getPose()
    #armature = armOb.getData()
    armOb = bpy.context.selected_objects[0]
    if not armOb.animation_data:
        armOb.animation_data_create()
    armature = armOb.data
    action = bpy.data.actions.new(name=clipname)
    armOb.animation_data.action = action
    pose = armOb.pose
    
    bone_index = -1
    motions = {}
    

    while 1:
        try:
            clipchunk = chunk.Chunk(file,bigendian=0,align=0)
        except EOFError:
            break
        if version == 1:
            name = clipchunk.read(32)
            if '\0' in name:
                name = name[:name.index('\0')]
        boneindex = read_int(clipchunk)
        keytype = read_int(clipchunk)
        numkeys = read_int(clipchunk)
        if version > 1:
            namelength = struct.unpack("B",clipchunk.read(1))[0]
            name = clipchunk.read(namelength)
            clipchunk.read(1)
        name = name.decode("utf8")
            
        if name not in motions:
            motions[name] = {}
        dlog ("%s,boneindex: %d,keytype: %d,numkeys: %d" % \
            (name,boneindex,keytype,numkeys))
        if keytype == MKEY_VISIBILITY:
            data = struct.unpack("%dB"  % numkeys,clipchunk.read(numkeys))
        else:
            data = struct.unpack("<%df" % numkeys,clipchunk.read(numkeys * 4))
        motions[name][keytype] = list(data)
        clipchunk.skip()
    #file read, now animate that bastard!
    for bone_name in motions:
        AnimateBone(bone_name,pose,motions,num_frames,armature,armOb,version)
    #pose.update()

def readclip(filepath):
    objName = bpy.path.display_name_from_filepath(filepath)
    CreateBlenderClip(filepath, objName)

def read(filepath,flipuv):
    objName = bpy.path.display_name_from_filepath(filepath)
    CreateBlenderMesh(filepath, objName,flipuv)

# package manages registering
