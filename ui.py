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
#  Copyright (C) 2019 JPfeP
#
# ##### END GPL LICENSE BLOCK #####


import bpy
from bpy.utils import register_class, unregister_class
from bpy.types import Panel
from bpy.types import Menu
from bpy_extras.io_utils import ImportHelper

import json
import time

from . import g_vars
from .data import generate_dict


class VIEW3D_PT_AddRoutes_MIDI_Config(Panel):
    bl_category = "AddR Config"
    bl_idname = "VIEW3D_PT_addroutes_config_midi"
    bl_label = "MIDI Config"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        prefs = bpy.context.preferences.addons['AddRoutes'].preferences
        layout = self.layout

        box = layout.box()
        box.prop(context.window_manager, 'addroutes_midi_settings')

        col = box.column(align=True)
        row1 = col.row()
        row2 = col.row()
        row1.alert = context.window_manager.addroutes_midi_in_alert
        row2.alert = context.window_manager.addroutes_midi_out_alert

        if context.window_manager.addroutes_midi_settings == 'Project':
            row1.prop(context.window_manager, "addroutes_midi_in_enum", text="Project In")
            row2.prop(context.window_manager, "addroutes_midi_out_enum", text="Project Out")
        else:
            row1.prop(context.window_manager, "addroutes_sys_midi_in_enum", text="System In")
            row2.prop(context.window_manager, "addroutes_sys_midi_out_enum", text="System Out")
            box.operator('wm.save_userpref')

        box.operator("addroutes.refresh_devices", text='Refresh Devices List')
        box.prop(bpy.context.window_manager, 'addroutes_midi_debug', text='Debug (!)')

        row = box.row()
        row.prop(context.scene, 'off_to_0', text='Convert notes off')

        box = layout.box()
        box.label(text="Synchronization:")

        row = box.row(align=True)
        row.prop(context.scene, 'sync')
        row.prop(context.scene, 'SPP')

        row = box.row(align=True)
        row.prop(context.scene, 'midi_clock_out')
        row.prop(context.scene, 'SPP_out')

        row = box.row()
        row.operator('addroutes.midiplay', text='Play', icon='PLAY')
        row.operator('addroutes.midicont', text='Pause', icon='PAUSE')
        #row.operator('addroutes.midistop', text='Stop', icon='MATPLANE')
        row = box.row()
        row.prop(context.scene, 'tempo')

        box = layout.box()
        box.label(text="Midifile settings:")
        row = box.row()
        row.prop(context.scene, 'midifile', text='')
        row.operator('addroutes.openmidifile', text='', icon='FILEBROWSER')
        row.operator('addroutes.midifile_parse', text='', icon='FILE_REFRESH')

        row = box.row(align=True)
        row.operator("addroutes.midifile", text='Convert midifile')
        row.prop(context.scene, 'mf_offset')
        box.prop(context.scene, 'mf_extraspoil', text='No Extrapolation')
        box.prop(context.scene, 'mf_render', text='Contribute while rendering')
        box.prop(context.scene, 'mf_play', text='Contribute while playing (Blender bug !)')

        box = layout.box()
        box.label(text="Postprocessing:")
        box.prop(context.scene, 'show_postprocess')
        #box.prop(context.scene, 'auto_postprocess')


class VIEW3D_PT_AddRoutes_OSC_Config(Panel):
    bl_category = "AddR Config"
    bl_idname = "VIEW3D_PT_addroutes_config_osc"
    bl_label = "OSC Config"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        prefs = bpy.context.preferences.addons['AddRoutes'].preferences
        layout = self.layout
        box = layout.box()
        col = box.column()

        col.prop(context.window_manager, 'addroutes_osc_settings')
        row = col.row(align=True)
        row.alert = bpy.context.window_manager.addroutes_osc_in_alert and g_vars.osc_in_enable
        col2 = layout.column(align=True)
        row2 = col.row(align=True)
        row2.alert = bpy.context.window_manager.addroutes_osc_out_alert and g_vars.osc_out_enable

        if context.window_manager.addroutes_osc_settings == 'Project':
            row.prop(bpy.context.window_manager, 'addroutes_osc_udp_in', text="Listen on")
            row.prop(bpy.context.window_manager, 'addroutes_osc_port_in', text="Input port")
            row.prop(bpy.context.window_manager, 'addroutes_osc_in_enable', text="")

            row2.prop(bpy.context.window_manager, 'addroutes_osc_udp_out', text="Destination address")
            row2.prop(bpy.context.window_manager, 'addroutes_osc_port_out', text="Outport port")
            row2.prop(bpy.context.window_manager, 'addroutes_osc_out_enable', text="")
        else:

            row.prop(prefs, 'osc_udp_in', text="Listen on ")
            row.prop(prefs, 'osc_port_in', text="Input port")
            row.prop(prefs, 'osc_in_enable', text="")

            row2.prop(prefs, 'osc_udp_out', text="Destination address")
            row2.prop(prefs, 'osc_port_out', text="Outport port")
            row2.prop(prefs, 'osc_out_enable', text="")
            col2.operator('wm.save_userpref')

        #col3 = layout.column()
        row3 = col.row(align=True)
        row3.prop(bpy.context.window_manager, 'addroutes_osc_debug', text='Debug (!)')

        box = layout.box()
        col = box.column()
        #col.separator()
        col.label(text="File conversion:")
        row = col.row()
        row.prop(context.scene, 'addroutes_qlistfile', text='')
        row.operator('addroutes.qlistopen', text='', icon='FILEBROWSER')
        row = col.row()
        row.operator('addroutes.qlistconvert')
        row.prop(context.scene, 'addroutes_qf_offset')

        col.separator()
        row = col.row()
        row.prop(context.scene, 'addroutes_fcapfile', text='')
        row.operator('addroutes.fcapopen', text='', icon='FILEBROWSER')
        row = col.row()
        row.operator('addroutes.fcapconvert')
        row.prop(context.scene, 'addroutes_fcap_offset')


class VIEW3D_PT_AddRoutes_Blemote_Config(Panel):
    bl_category = "AddR Config"
    bl_idname = "VIEW3D_PT_addroutes_config_blemote"
    bl_label = "Blemote Config"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        prefs = bpy.context.preferences.addons['AddRoutes'].preferences
        box = layout.box()
        box.label(text="Blemote Settings:")
        box.prop(prefs, "blemote_enable")
        box.prop(prefs, "blemote_autoconf")
        col = box.column(align=True)
        row = col.row(align=True)
        row.alert = bpy.context.window_manager.addroutes_blemote_alert and prefs.blemote_enable
        row.prop(prefs, "blemote_udp_in")
        row.prop(prefs, "blemote_port_in")

        row = col.row(align=True)
        row.prop(prefs, "blemote_udp_out")
        row.prop(prefs, "blemote_port_out")
        row.active = not (prefs.blemote_autoconf)
        box.operator('wm.save_userpref')

        box = layout.box()
        box.prop(bpy.context.window_manager, 'addroutes_blemote_debug')
        box.operator('addroutes.showblenderip')


class VIEW3D_PT_AddRoutes_Tools(Panel):
    bl_category = "Routes"
    bl_idname = "VIEW3D_PT_addroutes_tools"
    bl_label = "Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        row = col.row(align=True)
        row.prop(context.scene, 'MOM_catenum')
        row.operator('addroutes.addcat', icon='ADD', text='')
        row.operator('addroutes.removecat', icon='PANEL_CLOSE', text='')

        row = col.row(align=True)
        row.operator('addroutes.renamecat')
        row.operator('addroutes.copycat')

        row = col.row(align=True)
        row.operator('addroutes.catimport', icon='FILEBROWSER')
        row.operator('addroutes.catexport', icon='FILEBROWSER')

        col = layout.column()
        col.label(text='Routes sorting:')
        row = col.row(align=True)
        row.prop(context.scene, 'MOM_sorting', expand=True)

        box = layout.box()
        box.label(text="Extra route parameters:")
        box.prop(context.scene, 'show_postprocess')
        box.prop(context.scene, 'show_categories')
        box.prop(context.scene, 'addroutes_show_name_setting')

        #box.prop(context.scene, 'show_routes_number')

        row = layout.row()
        n_events = str(context.window_manager.n_overflow)
        row.label(text='Overflow events: ' + n_events)


def show_routes(context, layout, item, i, route_type):
    box = layout.box()

    #box_r.use_property_split = True
    #box_r.use_property_decorate = False  # No animation.

    if route_type == 'NORMAL':
        j = 0
    else:
        j = 1

    # Section 1 - Title bar
    #if context.window_manager.addroutes_osc_debug or context.window_manager.addroutes_midi_debug or context.scene.show_routes_number:
    box2 = box.box()
    row = box2.row()

    if item.show_expanded:
        row.prop(item, "show_expanded", text="", icon='DISCLOSURE_TRI_DOWN', emboss=False)
    else:
        row.prop(item, "show_expanded", text="", icon='DISCLOSURE_TRI_RIGHT', emboss=False)

    if route_type == 'NORMAL':
        if item.route_name == "":
            row.label(text='Route #' + str(i) + "       ")
        else:
            row.label(text=item.route_name)
        row.operator("addroutes.copyprop", icon='ADD', text='').n = i
        row.operator("addroutes.removeprop", icon='PANEL_CLOSE', text='').n = i
    else:
        if item.route_name == "":
            row.label(text='Route S' + str(i) + "       ")
        else:
            row.label(text=item.route_name)
        row.operator("addroutes.copysysprop", icon='ADD', text='').n = i
        row.operator("addroutes.remsysroute", icon='PANEL_CLOSE', text='').n = i

    if item.show_expanded:
        col = box.column(align=True)
        if context.scene.show_categories and route_type != 'SYSTEM':
            col.prop(item, 'category')

        if context.scene.addroutes_show_name_setting:
            col.prop(item, 'route_name')

    # Section 2 - Properties
    if item.show_expanded:
        row = box.row()
        row.alignment = 'CENTER'
        row.label(text="___Property___")
        col = box.column(align=True)

        if route_type == 'NORMAL' and not item.is_multi:
            col.prop(item, 'is_str2eval', text='Python')
        if item.is_str2eval:
            col = box.column(align=True)
            col.prop(item, 'str2eval')
            col.prop(item, 'withctx')
            col.prop(item, 'is_array', text='Is Array (show Index/All)')
            col.prop(item, 'is_angle', text='Is Angle (allow conversion)')
            # row.prop(item, 'is_enum')

        if item.alert is True and item.mode != 'Off':
            col.alert = True
        if route_type == 'NORMAL' and not item.is_str2eval:
            col.prop(item, 'id_type') #, icon_only=True)

            # Note: arg1= target ID pointer, arg2= name of the according prop, arg3= obvious, arg4= ID cat of the scene
            if item.is_multi and (item.VAR_use == 'name'):
                col.prop(item, 'name_var')
            else:
                col.prop_search(item.id, item.id_type, bpy.data, item.id_type, text='Item')

            col.prop(item, 'data_path', text='Path')

        row_dp = col.row(align=True)
        #row_dp.use_property_split = True                                                                               #trick to punch keyframe
        if item.is_array:
            if item.engine == 'MIDI' or item.engine == 'Blemote':
                row_dp.prop(item, 'array', text="Index")
            elif item.engine == 'OSC':
                if item.use_array is False:
                    row_dp.prop(item, 'array', text='Index')
                row_dp.prop(item, 'use_array', toggle=True)
        if item.is_angle:
            col.prop(item, 'rad2deg', toggle=True)

        if (item.engine == 'MIDI' or item.engine == 'OSC') and not item.is_str2eval:
            col = box.column(align=True)
            col.prop(item, 'is_multi')
            if item.is_multi:
                col.prop(item, 'number')
                col.prop(item, 'offset')
                col.prop(item, 'VAR_use')

        # Second Section
        row = box.row()
        row.alignment = 'CENTER'
        row.label(text="___Engine___")
        split = box.split(factor=0.8)
        row = split.row()
        row.prop(item, 'engine', text='Engine', expand=False)
        row = split.row()
        if item.engine != 'Blemote':
            row.prop(item, 'blem_switch', text='Blemote')



        # split = row.split(factor=.8)
        # row_dp = split.row(align=True)
        '''
     
        split2 = box.split(factor=0.8)
        row_e = split2.row(align=True)
        row_e2 = split2.row(align=True)
        if item.engine != 'Blemote':
            row_e2.prop(item, 'blem_switch', text='BL')
        else:
            row_e2.prop(item, 'record', text='Rec', icon='RADIOBUT_ON')
    
        '''

        col = box.column()
        if item.engine == 'MIDI':

            col.prop(item, 'channel')
            col.prop(item, 'cont_type')

            # Events with filter option
            if item.f_show:
                col.prop(item, 'filter')

            # If filter on
            if item.filter:
                col.prop(item, 'controller', text='Select')

            col3 = box.column(align=True)
            col3.label(text='Rescale:')
            row3 = col3.row(align=True)
            row3.prop(item, 'rescale_mode', expand=True)
            if item.rescale_mode != 'Auto' and item.rescale_mode != 'Direct':
                row3 = col3.row(align=True)
                row3.label(text='MIDI')
                row3.prop(item, 'rescale_outside_low')
                row3.prop(item, 'rescale_outside_high')
            if item.rescale_mode != 'Direct':
                row4 = col3.row(align=True)
                row4.label(text='Blender')
                row4.prop(item, 'rescale_blender_low')
                row4.prop(item, 'rescale_blender_high')

        # For OSC
        elif item.engine == 'OSC':
            split = box.split(factor=0.8)
            row = split.row()
            row.prop(item, 'osc_address')
            row = split.row()
            row.operator("addroutes.osc_pick", text='Pick').r = (i, j, 0)

            split = box.split(factor=0.8)
            row = split.row(align=True)
            # row.prop(item, 'filter', text='Extract')
            row.prop(item, 'osc_select_rank')
            row.prop(item, 'osc_select_n')
            row = split.row()
            row.alignment = 'CENTER'
            if route_type != "SYSTEM":
                if item.is_array and item.use_array:
                    row.label(text='(' + str(item.len) + ')')
                else:
                    row.label(text='(1)')
            else:
                if item.use_array:
                    row.label(text='(?)')
                else:
                    row.label(text='(1)')

        row = box.row()

        # this is for blemote, later
        if item.blem_switch or item.engine == 'Blemote':
            box.label(text='Blemote slider:')
            row = box.row(align=True)
            row.prop(item, 'blem_min')
            row.prop(item, 'blem_max')
            row.prop(item, 'blem_step')

        # 3th section
        row = box.row()
        row.alignment = 'CENTER'
        row.label(text="___Action___")
        col = box.column(align=True)
        col.prop(item, 'eval_mode')
        if item.eval_mode == 'expr':
            col.prop(item, 'eval_expr')

        box.separator()
        if context.scene.show_postprocess:
            row = box.row(align=True)
            row.label(text='Envelope settings:')
            row.prop(item, 'env_attack', text='Attack')
            row.prop(item, 'env_release', text='Release')
            row = box.row()
            row.prop(item, 'env_auto')

            op = row.operator("addroutes.midienv", text='Apply Envelope').r = (i, j, 0)

        box.separator()
        if item.record:
            box.label(text='Keyframes settings:')

            row = box.row()
            row.prop(item, 'kf_needed', text='Needed')
            row.prop(item, 'kf_visual', text='Visual')
            row.prop(item, 'kf_rgb', text='XYZ to RGB')

            row = box.row()
            row.prop(item, 'kf_replace', text='Replace')
            row.prop(item, 'kf_available', text='Available')
            row.prop(item, 'kf_cycle', text='Cycle aware')

            box.prop(item, 'kf_group', text='Group')

        split = box.split(factor=0.8)
        row = split.row()
        row.prop(item, 'mode', expand=True)
        if item.engine == 'Blemote':
            row.enabled = False
        else:
            row.enabled = True
        row = split.row()
        row.prop(item, 'record', text='Rec', icon='RADIOBUT_ON')


class VIEW3D_PT_AddRoutes_Routes(Panel):
    bl_category = "Routes"
    bl_label = "Project Routes"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_idname = "VIEW3D_PT_Mom_routes"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        for i, item in enumerate(bpy.context.scene.MOM_Items):
            if (item.category == context.scene.MOM_catenum and context.scene.MOM_sorting == 'Category') or context.scene.MOM_sorting == 'None':
                show_routes(context, layout, item, i, 'NORMAL')

        layout.operator("addroutes.addprop", text='Add route')


class VIEW3D_PT_AddR_Sys_Routes(Panel):
    bl_category = "Routes"
    bl_label = "System Routes"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_idname = "VIEW3D_PT_AddR_system_routes"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        prefs = bpy.context.preferences.addons['AddRoutes'].preferences
        layout = self.layout
        col = layout.column(align=True)

        for i, item in enumerate(prefs.AddR_System_Routes):
            show_routes(context, layout, item, i, 'SYSTEM')

        layout.operator("addroutes.addsysroute", text='Add system route')
        layout.operator('wm.save_userpref')


def addaroute(collection):
    item = collection.add()
    g_vars.highest_rank += 1
    item.perma_rank = g_vars.highest_rank
    return item


class AddRoutes_AddProp(bpy.types.Operator):
    """Add a route"""
    bl_idname = "addroutes.addprop"
    bl_label = "AddRoutes Add Route"
    bl_options = {'UNDO'}

    def execute(self, context):
        my_item = addaroute(bpy.context.scene.MOM_Items)
        my_item.cont_type = 'key_on'
        return{'FINISHED'}


class AddR_AddSysRoutes(bpy.types.Operator):
    """Add a system route"""
    bl_idname = "addroutes.addsysroute"
    bl_label = "AddRoutes Add Route"
    bl_options = {'UNDO'}

    def execute(self, context):
        prefs = bpy.context.preferences.addons['AddRoutes'].preferences
        my_item = addaroute(prefs.AddR_System_Routes)
        my_item.cont_type = 'key_on'
        return{'FINISHED'}


class AddRoutes_RemoveProp(bpy.types.Operator):
    """Remove route"""
    bl_idname = "addroutes.removeprop"
    bl_label = "AddRoutes Remove Route"
    bl_options = {'UNDO'}

    n: bpy.props.IntProperty()

    def execute(self, context):
        bpy.context.scene.MOM_Items.remove(self.n)
        generate_dict(self, context)
        return {'FINISHED'}


class AddRoutes_RemoveSysRoute(bpy.types.Operator):
    """Remove sys route"""
    bl_idname = "addroutes.remsysroute"
    bl_label = "AddRoutes Remove Sys Route"
    bl_options = {'UNDO'}

    n: bpy.props.IntProperty()
    
    def execute(self, context):
        prefs = bpy.context.preferences.addons['AddRoutes'].preferences
        prefs.AddR_System_Routes.remove(self.n)
        generate_dict(self, context)
        return{'FINISHED'}


class AddRoutes_CopyProp(bpy.types.Operator):
    """Copy a route"""
    bl_idname = "addroutes.copyprop"
    bl_label = "Copy Route"
    bl_options = {'UNDO'}

    n: bpy.props.IntProperty()

    def execute(self, context):
        my_item = addaroute(context.scene.MOM_Items)
        for k, v in context.scene.MOM_Items[self.n].items():
            if k != 'perma_rank':
                try:
                    my_item[k] = v
                except:
                    pass
        generate_dict(self, context)
        return{'FINISHED'}


def highest_rank(scene):
    highest = 0
    for item in scene.MOM_categories:
        if item.rank > highest:
            highest = item.rank
    return highest + 1


def list_scenes(self, context):
    result = []
    for sce in bpy.data.scenes:
        result.append((sce.name, sce.name, ''))
    return result


class AddRoutes_CopySysProp(bpy.types.Operator):
    """Copy a route"""
    bl_idname = "addroutes.copysysprop"
    bl_label = "Copy System Route"
    bl_options = {'UNDO'}

    n: bpy.props.IntProperty()

    def execute(self, context):
        prefs = bpy.context.preferences.addons['AddRoutes'].preferences
        my_item = addaroute(prefs.AddR_System_Routes)
        for k, v in prefs.AddR_System_Routes[self.n].items():
            if k != 'perma_rank':
                try:
                    my_item[k] = v
                except:
                    pass
        generate_dict(self, context)
        return{'FINISHED'}


class AddRoutes_CopyCategory(bpy.types.Operator):
    """Copy a whole category to another scene"""
    bl_idname = "addroutes.copycat"
    bl_label = "Copy to a scene"
    bl_property = "enumsce"
    #n: bpy.props.IntProperty()
    #targetsce : bpy.props.StringProperty()
    enumsce : bpy.props.EnumProperty(items=list_scenes)

    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}

    def execute(self, context):
        sce = bpy.data.scenes[self.enumsce]
        # first check is a similar category exist there
        if sce.MOM_categories.find(context.scene.MOM_catenum) == -1:
            new = sce.MOM_categories.add()
            new.name = context.scene.MOM_catenum
            new.rank = highest_rank(sce)

        for item in bpy.context.scene.MOM_Items:
            if item.category == context.scene.MOM_catenum:
                my_item = addaroute(sce.MOM_Items)
                for k, v in item.items():
                    try:
                        if k != 'category':
                            my_item[k] = v
                        else:
                            my_item[k] = sce.MOM_categories[context.scene.MOM_catenum].rank
                    except:
                        pass
        return{'FINISHED'}


class AddRoutes_CreateCategory(bpy.types.Operator):
    """Create a category"""
    bl_idname = "addroutes.addcat"
    bl_label = "Create a category"

    name: bpy.props.StringProperty(default='New Category')

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        new = context.scene.MOM_categories.add()
        new.name = self.name
        new.rank = highest_rank(context.scene)

        return{'FINISHED'}


class AddRoutes_RenameCategory(bpy.types.Operator):
    """Rename a category"""
    bl_idname = "addroutes.renamecat"
    bl_label = "Rename"

    name: bpy.props.StringProperty(default='New Category')

    def invoke(self, context, event):
        if context.scene.MOM_catenum == 'Default':
            self.report({'INFO'}, "'Default' cannot be renamed !")
            return{'FINISHED'}
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        n = context.scene.MOM_categories.find(context.scene.MOM_catenum)
        target = context.scene.MOM_categories[n]
        target.name = self.name

        return{'FINISHED'}


class AddRoutes_RemoveCategory(bpy.types.Operator):
    """Remove a category"""
    bl_idname = "addroutes.removecat"
    bl_label = "Remove a category"

    def execute(self, context):
        for item in context.scene.MOM_Items:
            if item.category == context.scene.MOM_catenum:
                item.category = 'Default'

        rank = context.scene.MOM_categories.find(context.scene.MOM_catenum)
        context.scene.MOM_categories.remove(rank)
        context.scene.MOM_catenum = 'Default'

        return{'FINISHED'}


def keep_good_keys(dir_list):
    bad = ('__annotations__', '__dict__', '__doc__', '__module__', '__weakref__', 'bl_rna', 'rna_type',  'upd_max', 'upd_min',  'double', 'int', 'name')
    for bad_item in bad:
        try:
            dir_list.remove(bad_item)
        except:
            #print("Export, not found :", bad_item)
            pass
    return dir_list


def catexport(sce):
    catroutes = {}
    route = {}
    for i, item in enumerate(sce.MOM_Items):
        if item.category == sce.MOM_catenum:
            pair = {}
            k_list = keep_good_keys(dir(item))
            for k in k_list:
                if k == 'id':
                    pair[k] = item.id[item.id_type].name
                elif k == 'perma_rank':
                    continue
                else:
                    try:
                        pair[k] = getattr(item, k)
                    except:
                        pass
            route[i] = pair
    catroutes[sce.MOM_catenum] = route

    return json.dumps(catroutes)


class AddRoutes_Category_Export(bpy.types.Operator):
    """Export category to a file in JSON format"""
    bl_idname = "addroutes.catexport"
    bl_label = "Export"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filename: bpy.props.StringProperty()

    def execute(self, context):
        file = open(self.filepath, 'w')
        file.write(catexport(context.scene))
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filename = context.scene.MOM_catenum+'.routes'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def catimport(scene, file):
    table = json.load(file)
    for catroutes in table.items():
        # check if the category need to be created
        cat = catroutes[0]
        routes = catroutes[1]
        if scene.MOM_categories.get(cat) is None:
            new = scene.MOM_categories.add()
            new.name = cat
            new.rank = highest_rank(scene)

        for route in routes.items():
            item = scene.MOM_Items.add()
            i = route[0]
            t = route[1]
            ID = ""
            for k, v in t.items():

                if k == "id":
                    ID = v

                elif k == "id_type":
                    setattr(item, k, v)
                    ref = getattr(bpy.data, item.id_type)
                    try:
                        item.id[item.id_type] = ref[ID]
                    except:
                        pass

                else:
                    setattr(item, k, v)
            item.category = cat
        #updaterank()


class AddRoutes_Category_Import(bpy.types.Operator, ImportHelper):
    """Import category to a file in JSON format"""
    bl_idname = "addroutes.catimport"
    bl_label = "Import"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filename: bpy.props.StringProperty()
    filter_glob: bpy.props.StringProperty(
        default="*.routes",
        options={'HIDDEN'})

    def execute(self, context):
        file = open(self.filepath, 'r')
        catimport(context.scene, file)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filename = ""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# This is for the contextual menu to create route from a property
class WM_OT_button_context_addroutes(bpy.types.Operator):
    """Create a route"""
    bl_idname = "wm.button_context_addroutes"
    bl_label = "Create a realtime route"

    # @classmethod
    # def poll(cls, context):
    #      print (context.active_operator)
    #      return context.active_object is not None

    def execute(self, context):
        value1 = getattr(context, "button_pointer", None)
        if value1 is not None:
            id = value1.id_data

        value2 = getattr(context, "button_prop", None)
        if value2 is not None:
            prop = value2.identifier
            my_item = addaroute(bpy.context.scene.MOM_Items)
            my_item.cont_type = 'key_on'

            # Workaround for materials using nodes
            if id.name == 'Shader Nodetree':
                # Ugly way to guess the good id
                # For materials
                try:
                    id_type = 'materials'
                    id = bpy.context.object.active_material
                    data_path = 'node_tree.'+value1.path_from_id(prop)

                    # this to raise an error, if needed
                    a = eval(repr(id)+'.'+data_path)

                    my_item.id_type = id_type
                    setattr(my_item.id, id_type, id)
                    my_item.data_path = data_path
                except:
                    self.report({'INFO'}, "Error !")
                # For worlds
                try:
                    id_type = 'worlds'
                    id = bpy.context.scene.world
                    data_path = 'node_tree.'+value1.path_from_id(prop)

                    # this to raise an error, if needed
                    a = eval(repr(id) + '.' + data_path)

                    my_item.id_type = id_type
                    setattr(my_item.id, id_type, id)
                    my_item.data_path = data_path
                except:
                    self.report({'INFO'}, "Error !")

            else:
                try:
                    id_type = repr(id).split(".")[2].split('[')[0]
                    data_path = value1.path_from_id(prop)

                    my_item.id_type = id_type
                    setattr(my_item.id, id_type, id)
                    my_item.data_path = data_path
                except:
                    print (value1, value2, prop)
                    self.report({'INFO'}, "Error !")

        return {'FINISHED'}


# This class has to be exactly named like that to insert an entry in the right click menu
class WM_MT_button_context(Menu):
    bl_label = "Unused"

    def draw(self, context):
        pass


class AddRoutes_OscPick(bpy.types.Operator):
    """Pick last event OSC address"""
    bl_idname = "addroutes.osc_pick"
    bl_label = "AddRoutes OSC event pick address"
    bl_options = {'UNDO'}

    r: bpy.props.IntVectorProperty()

    def execute(self, context):
        item = g_vars.get_item(self.r[0], self.r[1])
        if g_vars.last_osc_addr is not None:
            item.osc_address = g_vars.last_osc_addr

        return {'FINISHED'}


class AddRoutes_DebugInfo(bpy.types.Operator):
    """Copy debug messages in Info window"""
    bl_idname = "addroutes.debuginfo"
    bl_label = "Copy Debug in Info window"

    msg: bpy.props.StringProperty()

    def execute(self, context):
        g_vars.debugcopy(self, context)
        prefs = bpy.context.preferences.addons['AddRoutes'].preferences

        if prefs.debug_timestamp:
            msg = time.strftime("%H:%M:%S", time.localtime()) + ': ' + self.msg
        else:
            msg = self.msg
        if prefs.debug_copy:
            text = bpy.data.texts.get("AddRoutes: Debug in/out")
            if text is not None:
                text.cursor_set(line=0)
                text.write(msg+'\n\n')
        print(msg+'\n\n')

        return {'FINISHED'}


def menu_func(self, context):
    layout = self.layout
    layout.separator()
    layout.operator(WM_OT_button_context_addroutes.bl_idname)


cls = ( AddRoutes_AddProp,
        AddRoutes_RemoveProp,
        AddRoutes_RemoveSysRoute,
        AddRoutes_CopyProp,
        AddRoutes_CopySysProp,
        AddRoutes_CreateCategory,
        AddRoutes_CopyCategory,
        AddRoutes_RemoveCategory,
        AddRoutes_RenameCategory,
        AddRoutes_Category_Export,
        AddRoutes_Category_Import,
        AddRoutes_OscPick,
        AddRoutes_DebugInfo,
        VIEW3D_PT_AddRoutes_MIDI_Config,
        VIEW3D_PT_AddRoutes_OSC_Config,
        VIEW3D_PT_AddRoutes_Blemote_Config,
        VIEW3D_PT_AddRoutes_Tools,
        VIEW3D_PT_AddRoutes_Routes,
        VIEW3D_PT_AddR_Sys_Routes,
        WM_OT_button_context_addroutes,
        WM_MT_button_context,
        AddR_AddSysRoutes,
    )


def register():
    for c in cls:
        register_class(c)
    bpy.types.WM_MT_button_context.append(menu_func)


def unregister():
    bpy.types.WM_MT_button_context.remove(menu_func)  # order was important
    for c in cls:
        unregister_class(c)


if __name__ == "__main__":
    register()

