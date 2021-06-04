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

# <pep8-80 compliant>

bl_info = {
    "name": "K2 Model/Animation Import-Export",
    "author": "Anton Romanov",
    "version": (0, 1),
    "blender": (2, 8, 0),
    "location": "File > Import-Export > K2 model/clip",
    "description": "Import-Export meshes and animations used by K2 engine (Savage 2 and Heroes of Newerth games)",
    "warning": "",
    "wiki_url": "https://github.com/theli-ua/K2-Blender/wiki",
    "tracker_url": "https://github.com/theli-ua/K2-Blender/issues",
    "support": "TESTING",
    "category": "Import-Export"}

if "bpy" not in locals():
    print("init first load")
    import bpy
    from . import k2_import
    from . import k2_export
    from .operators import K2_OT_clip_importer, K2_OT_mesh_importer, K2_OT_clip_exporter, K2_OT_mesh_exporter
    # import register, unregister
else:
    print("init reload")
    import importlib
    from . import k2_import
    from . import create_blender_mesh
    from . import create_blender_clip
    from . import k2_export
    from . import create_bone_data
    from . import create_mesh_data
    from . import export_k2_mesh
    from . import export_k2_clip
    from . import operators
    from . import mat_utils
    # from .operators import K2ImporterClip, K2Importer, K2ClipExporter, K2MeshExporter

    importlib.reload(k2_import)
    importlib.reload(create_blender_mesh)
    importlib.reload(create_blender_clip)
    importlib.reload(k2_export)
    importlib.reload(create_bone_data)
    importlib.reload(create_mesh_data)
    importlib.reload(export_k2_mesh)
    importlib.reload(export_k2_clip)
    importlib.reload(operators)
    importlib.reload(mat_utils)
    # importlib.reload(K2ImporterClip)
    # importlib.reload(K2Importer)
    # importlib.reload(K2ClipExporter)
    # importlib.reload(K2MeshExporter)


def menu_import(self, context):
    self.layout.operator(K2_OT_mesh_importer.bl_idname, text="K2 mesh (.model)")
    self.layout.operator(K2_OT_clip_importer.bl_idname, text="K2 clip (.clip)")


def menu_export(self, context):
    self.layout.operator(K2_OT_mesh_exporter.bl_idname, text="K2 Mesh (.model)")
    self.layout.operator(K2_OT_clip_exporter.bl_idname, text="K2 Clip (.clip)")


def register():
    bpy.utils.register_class(K2_OT_clip_importer)
    bpy.utils.register_class(K2_OT_mesh_importer)
    bpy.utils.register_class(K2_OT_clip_exporter)
    bpy.utils.register_class(K2_OT_mesh_exporter)
    # bpy.utils.register_module(__name__)

    bpy.types.TOPBAR_MT_file_import.append(menu_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_export)
    # bpy.types.INFO_MT_file_import.append(menu_import)
    # bpy.types.INFO_MT_file_export.append(menu_export)


def unregister():
    # bpy.utils.unregister_module(__name__)

    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_export)
    # bpy.types.INFO_MT_file_import.remove(menu_import)
    # bpy.types.INFO_MT_file_export.remove(menu_export)
    bpy.utils.unregister_class(K2_OT_clip_importer)
    bpy.utils.unregister_class(K2_OT_mesh_importer)
    bpy.utils.unregister_class(K2_OT_clip_exporter)
    bpy.utils.unregister_class(K2_OT_mesh_exporter)


if __name__ == "__main__":
    register()
