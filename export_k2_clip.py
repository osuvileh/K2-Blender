import struct
from io import BytesIO
from math import degrees

import bpy
from mathutils import Matrix

##############################
# CLIPS
##############################
MKEY_X, MKEY_Y, MKEY_Z, MKEY_PITCH, MKEY_ROLL, MKEY_YAW, MKEY_VISIBILITY, MKEY_SCALE_X, MKEY_SCALE_Y, MKEY_SCALE_Z, MKEY_COUNT = range(11)

IMPORT_LOG_LEVEL = 3


def log(msg):
    if IMPORT_LOG_LEVEL >= 1:
        print(msg)


def vlog(msg):
    if IMPORT_LOG_LEVEL >= 2:
        print(msg)


def err(msg):
    log(msg)


def bone_depth(bone):
    if not bone.parent:
        return 0
    else:
        return 1 + bone_depth(bone.parent)


def write_block(file, name, data):
    file.write(name.encode('utf8')[:4])
    file.write(struct.pack("<i", len(data)))
    file.write(data)


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
    vlog('baking animation')
    armature = arm_ob.data
    if transform:
        worldmat = arm_ob.matrix_world
    else:
        worldmat = Matrix([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])

    scene = bpy.context.scene
    pose = arm_ob.pose

    motions = {}
    for frame in range(frame_start, frame_end):
        scene.frame_set(frame)
        for bone in pose.bones.values():
            append_bone_motion(bone, motions, worldmat)

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
    print("done!")


def append_bone_motion(bone, motions, worldmat):
    matrix = bone.matrix
    if bone.parent:
        matrix = matrix @ (bone.parent.matrix.copy().inverted())
    else:
        matrix = matrix @ worldmat
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
