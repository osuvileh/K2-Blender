import chunk
import math
import struct

import bpy
import mathutils

from .create_blender_mesh import err
from .parse_hon_file import IMPORT_LOG_LEVEL, log, read_int, vlog

##############################
# CLIPS
##############################
MKEY_X, MKEY_Y, MKEY_Z, MKEY_PITCH, MKEY_ROLL, MKEY_YAW, MKEY_VISIBILITY, MKEY_SCALE_X, MKEY_SCALE_Y, MKEY_SCALE_Z = range(10)

def dlog(msg):
    if IMPORT_LOG_LEVEL >= 3: print(msg)


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
    scale = mathutils.Vector([sx, sy, sz])
    bone_rotation_matrix = mathutils.Euler((math.radians(rx), math.radians(ry), math.radians(rz)), 'YXZ').to_matrix().to_4x4()

    bone_rotation_matrix = mathutils.Matrix.Translation(mathutils.Vector((x, y, z))) @ bone_rotation_matrix

    return bone_rotation_matrix, scale


def animate_bone(name, pose, motions, num_frames, armature, arm_ob, version):
    if name not in armature.bones.keys():
        log('%s not found in armature' % name)
        return
    motion = motions[name]
    bone = armature.bones[name]
    bone_rest_matrix = mathutils.Matrix(bone.matrix_local)

    if bone.parent is not None:
        parent_bone = bone.parent
        parent_rest_bone_matrix = mathutils.Matrix(parent_bone.matrix_local)
        parent_rest_bone_matrix.invert()
        bone_rest_matrix = parent_rest_bone_matrix @ bone_rest_matrix

    bone_rest_matrix_inv = mathutils.Matrix(bone_rest_matrix)
    bone_rest_matrix_inv.invert()

    pbone = pose.bones[name]
    prev_euler = mathutils.Euler()
    for i in range(0, num_frames):
        transform, size = get_transform_matrix(motions, bone, i, version)
        transform = bone_rest_matrix_inv @ transform
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
    # arm_obj = objList[0]
    # action = Blender.Armature.NLA.NewAction(clipname)
    # action.setActive(arm_obj)
    # pose = arm_obj.getPose()
    # armature = arm_obj.getData()
    arm_obj = bpy.context.selected_objects[0]
    print("bpy.data.armatures:", bpy.data.armatures.values())

    for ob in bpy.context.editable_objects:
        print("ob.name:", ob.name)

        try:
            if(ob.data in bpy.data.armatures.values()):
                print("armatures!")
                arm_obj = ob
        except AttributeError:
            print("nope")
        # print(ob.data.nodes)
    if arm_obj.data not in bpy.data.armatures.values():
        raise TypeError("Selected object not an armature")

    if not arm_obj.animation_data:
        arm_obj.animation_data_create()

    armature = arm_obj.data
    action = bpy.data.actions.new(name=clip_name)
    arm_obj.animation_data.action = action
    pose = arm_obj.pose

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
        animate_bone(bone_name, pose, motions, num_frames, armature, arm_obj, version)
    # pose.update()