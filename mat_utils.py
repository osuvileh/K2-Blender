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
    mat = rMatrix @ bMatrix
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

    zero_angle_matrix = vec_roll_to_mat3(axis, 0.0)
    delta_matrix = zero_angle_matrix.inverted() @ mat_3x3
    angle = math.atan2(delta_matrix.col[2][0], delta_matrix.col[2][2])
    return axis, angle 