import struct
from io import BytesIO

# from .export_k2_clip import bone_depth


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


def bone_depth(bone):
    if not bone.parent:
        return 0
    else:
        return 1 + bone_depth(bone.parent)
