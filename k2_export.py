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

# determines the verbosity of loggin.
#   0 - no logging (fatal errors are still printed)
#   1 - standard logging
#   2 - verbose logging
#   3 - debug level. really boring (stuff like vertex data and verbatim lines)

from .export_k2_clip import IMPORT_LOG_LEVEL


def dlog(msg):
    if IMPORT_LOG_LEVEL >= 3:
        print(msg)


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


##############################
# CLIPS
##############################

MKEY_X, MKEY_Y, MKEY_Z, MKEY_PITCH, MKEY_ROLL, MKEY_YAW, MKEY_VISIBILITY, MKEY_SCALE_X, MKEY_SCALE_Y, MKEY_SCALE_Z, MKEY_COUNT = range(11)

