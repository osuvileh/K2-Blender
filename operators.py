import bpy
from bpy.props import StringProperty, BoolProperty, IntProperty

from .export_k2_clip import export_k2_clip
from .export_k2_mesh import export_k2_mesh


class K2_OT_clip_importer(bpy.types.Operator):
    '''Load K2/Silverlight clip data'''
    bl_idname = "k2.clip_importer"
    bl_label = "Import K2 Clip"

    filepath: StringProperty(subtype='FILE_PATH', )
    filter_glob: StringProperty(default="*.clip", options={'HIDDEN'})

    def execute(self, context):
        from . import k2_import
        k2_import.read_clip(self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class K2_OT_mesh_importer(bpy.types.Operator):
    '''Load K2/Silverlight mesh data'''
    bl_idname = "k2.mesh_importer"
    bl_label = "Import K2 Mesh"

    filepath: StringProperty(name='File Path', default='', maxlen=1024, subtype='FILE_PATH')
    filter_glob: StringProperty(default='*.model', options={'HIDDEN'})
    flipuv: BoolProperty(
        name="Flip UV",
        description="Flip UV",
        default=True,
    )

    def execute(self, context):
        from . import k2_import
        k2_import.read(self.filepath, self.flipuv)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class K2_OT_clip_exporter(bpy.types.Operator):
    '''Save K2 triangle clip data'''
    bl_idname = "k2.clip_exporter"
    bl_label = "Export K2 Clip"

    filepath: StringProperty(
        subtype='FILE_PATH',
    )
    filter_glob: StringProperty(default="*.clip", options={'HIDDEN'})
    check_existing: BoolProperty(
        name="Check Existing",
        description="Check and warn on overwriting existing files",
        default=True,
        options={'HIDDEN'},
    )
    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Use transformed mesh data from each object",
        default=True,
    )
    frame_start: IntProperty(name="Start Frame", description="Starting frame for the animation", default=0)
    frame_end: IntProperty(name="Ending Frame", description="Ending frame for the animation", default=1)

    def execute(self, context):
        from . import k2_export
        export_k2_clip(self.filepath, self.apply_modifiers, self.frame_start, self.frame_end)
        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = bpy.path.ensure_ext(bpy.data.filepath, ".clip")
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class K2_OT_mesh_exporter(bpy.types.Operator):
    '''Save K2 triangle mesh data'''
    bl_idname = "k2.mesh_exporter"
    bl_label = "Export K2 Mesh"

    filepath: StringProperty(
        subtype='FILE_PATH',
    )
    filter_glob: StringProperty(default="*.model", options={'HIDDEN'})
    check_existing: BoolProperty(
        name="Check Existing",
        description="Check and warn on overwriting existing files",
        default=True,
        options={'HIDDEN'},
    )
    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Use transformed mesh data from each object",
        default=True,
    )

    def execute(self, context):
        from . import k2_export
        export_k2_mesh(context, self.filepath, self.apply_modifiers)

        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = bpy.path.ensure_ext(bpy.data.filepath, ".model")
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}
