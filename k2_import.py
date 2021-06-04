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

import bpy

# determines the verbosity of loggin.
#   0 - no logging (fatal errors are still printed)
#   1 - standard logging
#   2 - verbose logging
#   3 - debug level. really boring (stuff like vertex data and verbatim lines)
from .create_blender_clip import create_blender_clip
from .create_blender_mesh import create_blender_mesh


def bone_depth(bone):
    if not bone.parent:
        return 0
    else:
        return 1 + bone_depth(bone.parent)


def read_clip(filepath):
    obj_name = bpy.path.display_name_from_filepath(filepath)
    create_blender_clip(filepath, obj_name)


def read(filepath, flipuv):
    obj_name = bpy.path.display_name_from_filepath(filepath)
    create_blender_mesh(filepath, obj_name, flipuv)

