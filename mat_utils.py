import math

from mathutils import Vector, Matrix


def round_vector(vec, dec=17):
    fvec = []
    for v in vec:
        fvec.append(round(v, dec))
    return Vector(fvec)


def round_matrix(mat, dec=17):
    f_mat = []
    for row in mat:
        f_mat.append(round_vector(row, dec))
    return Matrix(f_mat)


def vec_roll_to_mat3(vec, roll):
    target = Vector((0, 1, 0))
    nor = vec.normalized()
    axis = target.cross(nor)
    if axis.dot(axis) > 0.000001:
        axis.normalize()
        theta = target.angle(nor)
        b_matrix = Matrix.Rotation(theta, 3, axis)
    else:
        updown = 1 if target.dot(nor) > 0 else -1
        b_matrix = Matrix.Scale(updown, 3)
    r_matrix = Matrix.Rotation(roll, 3, nor)
    mat = r_matrix @ b_matrix
    return mat


def mat3_to_vec_roll(mat):
    vec = mat.col[1]
    vec_mat = vec_roll_to_mat3(mat.col[1], 0)
    vec_mat_inv = vec_mat.inverted()
    roll_mat = vec_mat_inv @ mat
    roll = math.atan2(roll_mat[0][2], roll_mat[2][2])
    return vec, roll
