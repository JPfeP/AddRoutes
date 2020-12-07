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

import os

import bpy
from bpy.utils import register_class, unregister_class
from bpy.app.handlers import persistent
from bpy_extras.io_utils import ImportHelper

from mathutils import *

from oscpy.client import OSCClient

import numpy as np

import time
#import sys

from . import g_vars

#for qfile conversion
qf_frame = {}


def set_props(item, bl_item, val):
    global qf_frame
    if len(val) == 1:
        val = val[0]

    func = item['func']
    result = func(bl_item, item, val)
    post_func = item['post_func']

    if bl_item.is_str2eval:
        g_vars.evalprop(bl_item.str2eval, bl_item.withctx)
        prop = g_vars.eval_prop
        ref = g_vars.eval_ref
    else:
        ref = item['ref']
        prop = item['prop']

    if bl_item.is_array and (bl_item.use_array is False):
        current = getattr(ref, prop)[bl_item.array]
        result2 = post_func(current, result, bl_item)
        getattr(ref, prop)[bl_item.array] = result2
    else:
        current = getattr(ref, prop)
        result2 = post_func(current, result, bl_item)
        setattr(ref, prop, result2)

    # insert keyframe
    if bl_item.record and (bpy.data.screens[0].is_animation_playing or qf_frame != {}):
        if bl_item.is_array and (bl_item.use_array is False):
            index = bl_item.array
            ref.keyframe_insert(data_path=prop, index=index, **item['ks_params'], **qf_frame)
        else:
            ref.keyframe_insert(data_path=prop, **item['ks_params'], **qf_frame)

    return result2


def actua_osc_timer():
    prefs = bpy.context.preferences.addons['AddRoutes'].preferences

    in_len = len(g_vars.osc_queue)
    if in_len > prefs.overflow:
        g_vars.osc_queue = g_vars.osc_queue[:prefs.overflow]
        bpy.context.window_manager.n_overflow += 1

    for i in range(prefs.overflow):
        if len(g_vars.osc_queue) == 0:
            break
        else:
            msg = g_vars.osc_queue.pop(0)
            actua_osc(msg)

    return prefs.refresh / 1000


def actua_osc(msg):
    addr = msg[0]
    val = msg[1:]

    # weird fix for Touch OSC and such with empty payload
    if len(val) == 0:
        val = [0]
    else:
        multi_idx = val[0]

    # get the osc address for OSC Pick operator
    g_vars.last_osc_addr = addr

    if bpy.context.window_manager.addroutes_osc_debug:
        debug_flag = False
        debug_msg = "OSC - Receiving:"+str(msg)

    for n, bl_item, dico_arr in g_vars.addroutes_osc_in.get(addr, []):
        try:
            # getting index and a ref for the blender item
            idx = bl_item.osc_select_rank
            val2 = val[idx:idx+bl_item.osc_select_n]          # val2 matters

            if bl_item.is_multi is True:
                dico = dico_arr.get(str(int(multi_idx)))
                if dico is not None:
                    result2 = set_props(dico, bl_item, val2)
                # debug in console
                if bpy.context.window_manager.addroutes_osc_debug is True:
                    debug_msg += "\n---> OK route n°" + str(n) + ", category: " + bl_item.category + ", updating property to :" + str(result2) + " using:" + str(val2)
                    bpy.ops.addroutes.debuginfo(msg=debug_msg)
                    debug_flag = True
            elif bl_item.is_multi is False:
                dico = dico_arr["0"]
                result2 = set_props(dico, bl_item, val2)
                # debug in console
                if bpy.context.window_manager.addroutes_osc_debug is True:
                    debug_msg += "\n---> OK route n°" + str(n) + ", category: " + bl_item.category + ", updating property to :" + str(result2) + " using:" + str(val2)
                    bpy.ops.addroutes.debuginfo(msg=debug_msg)
                    debug_flag = True

        except:
            #print("Unexpected error:", sys.exc_info()[0])
            if bpy.context.window_manager.addroutes_osc_debug is True:
                debug_msg += "\n---> but something went wrong with route n°" + str(n) + ", category: " + bl_item.category
                bpy.ops.addroutes.debuginfo(msg=debug_msg)
                debug_flag = True

    # if no route has triggered a debug_flag
    if bpy.context.window_manager.addroutes_osc_debug is True and debug_flag is False:
        debug_msg += "\n... but no matching route"
        bpy.ops.addroutes.debuginfo(msg=debug_msg)


class AddRoutes_Qlist_Open(bpy.types.Operator, ImportHelper):
    """Select Pd/Qlist file"""
    bl_idname = "addroutes.qlistopen"
    bl_label = "Open"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filename: bpy.props.StringProperty()
    filter_glob: bpy.props.StringProperty(
        default='*.txt',
        options={'HIDDEN'})

    def execute(self, context):
        filename, extension = os.path.splitext(self.filepath)
        context.scene.addroutes_qlistfile = bpy.path.relpath(self.filepath)
        if context.scene.addroutes_qlistfile[0] != "/":
            context.scene.addroutes_qlistfile = "//" + context.scene.addroutes_qlistfile
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filename = ""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class AddRoutes_Qlist_Convert(bpy.types.Operator):
    '''Convert Pd/Qlist to F-curves'''
    bl_idname = "addroutes.qlistconvert"
    bl_label = "Convert Pd/Qlist"

    def execute(self, context):
        global qf_frame
        try:
            qfile = open(bpy.path.abspath(context.scene.addroutes_qlistfile), "r")
        except:
            self.report({'INFO'}, "Pd/Qfile Error")
            return {'FINISHED'}

        line = qfile.readline()
        timeline = 0

        while line:
            if len(line) == 0:
                line = qfile.readline()
                continue
            atoms = line.split(" ")
            time = atoms[0]
            # this to prevent case where no time value is given
            try:
                time = float(time)
                addr = str(atoms[1])
                arr = atoms[2:]
            except:
                time = 0
                addr = str(atoms[0])
                arr = atoms[1:]

            if len(addr) == 0:
                line = qfile.readline()
                continue

            if addr[0] != "/":
                addr = "/" + addr

            timeline += time / 1000
            # to move the play head later
            pos_frame = timeline * context.scene.render.fps

            qf_frame = {}

            # try to convert to float each argument
            args = [addr]
            for arg in arr:
                try:
                    arg_f = float(arg)
                except:
                    arg_f = arg
                args.append(arg_f)

            qf_frame['frame'] = pos_frame + context.scene.addroutes_qf_offset

            actua_osc(args)
            line = qfile.readline()

        qf_frame = {}
        qfile.close()

        self.report({'INFO'}, "File conversion done")
        return {'FINISHED'}


class AddRoutes_FaceCap_Open(bpy.types.Operator, ImportHelper):
    """Select FaceCap file"""
    bl_idname = "addroutes.fcapopen"
    bl_label = "Open"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filename: bpy.props.StringProperty()
    filter_glob: bpy.props.StringProperty(
        default='*.txt',
        options={'HIDDEN'})

    def execute(self, context):
        filename, extension = os.path.splitext(self.filepath)
        context.scene.addroutes_fcapfile = bpy.path.relpath(self.filepath)
        if context.scene.addroutes_fcapfile[0] != "/":
            context.scene.addroutes_fcapfile = "//" + context.scene.addroutes_fcapfile
        #bpy.ops.addroutes.midifile_parse()
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filename = ""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class AddRoutes_FaceCap_Convert(bpy.types.Operator):
    '''Convert FaceCap text file to F-curves. Select a proper collection first'''
    bl_idname = "addroutes.fcapconvert"
    bl_label = "Convert FaceCap File"

    def execute(self, context):
        try:
            fcapfile = open(bpy.path.abspath(context.scene.addroutes_fcapfile), "r")
        except:
            self.report({'INFO'}, "FaceCap file Error")
            return {'FINISHED'}

        line = fcapfile.readline()
        timeline = 0

        try:
            parent = bpy.context.object
            score = 0
            for ob in parent.children:
                name = ob.name.lower()
                if name.find('head') != -1:
                    head = ob
                    score += 1
                elif name.find('left') != -1 and name.find('eye') != -1:
                    l_eye = ob
                    score += 1
                elif name.find('right') != -1 and name.find('eye') != -1:
                    r_eye = ob
                    score += 1
            if score != 3:
                raise ValueError("Some objects not found")
        except:
            self.report({'INFO'}, "Target's children should contain head and eyes objects")
            return {'FINISHED'}

        fcap_error = False
        while line:
            atoms = line.split(",")
            try:
                if atoms[0] == "bs":
                    blendshapes = atoms[1:]

                if atoms[0] == "k":
                    values = np.array(atoms[1:])
                    values = values.astype(np.float)
                    timeline = values[0]
                    loc = values[1:4]
                    head_euler = values[4:7]
                    l_eye_euler = values[7:9]
                    r_eye_euler = values[9:11]
                    shapekeys = values[11:-1]

                    pos_frame = (timeline * 0.001 * context.scene.render.fps) + context.scene.addroutes_fcap_offset

                    # location
                    parent.location = loc
                    parent.keyframe_insert(data_path='location', frame=pos_frame)
                    # head angle
                    parent.rotation_euler = np.radians(head_euler)
                    parent.keyframe_insert(data_path='rotation_euler', frame=pos_frame)
                    # left_eye
                    l_eye.rotation_euler[0:2] = np.radians(l_eye_euler)
                    l_eye.keyframe_insert(data_path='rotation_euler', frame=pos_frame)
                    # righ_eye
                    r_eye.rotation_euler[0:2] =  np.radians(r_eye_euler)
                    r_eye.keyframe_insert(data_path='rotation_euler', frame=pos_frame)
                    # for the 52 shape keys
                    for i, val in enumerate(shapekeys):
                        head.data.shape_keys.key_blocks[blendshapes[i]].value = val
                        head.data.shape_keys.key_blocks[blendshapes[i]].keyframe_insert(data_path='value', frame=pos_frame)
            except:
                fcap_error = True

            line = fcapfile.readline()

        fcapfile.close()

        if fcap_error is True:
            self.report({'INFO'}, "Some errors while converting, check your collection and/or documentation")
        else:
            self.report({'INFO'}, "File conversion done")

        return {'FINISHED'}


@persistent
def osc_frame_upd(scn):
    # kludge to avoid error while changing scene
    if g_vars.scene is not scn:
        return

    # send osc events
    if g_vars.osc_out_enable is True and bpy.context.window_manager.addroutes_osc_out_alert is False:
        for bl_item, item in g_vars.addroutes_osc_out:
            # getting current value
            if bl_item.is_str2eval:
                g_vars.evalprop(bl_item.str2eval, bl_item.withctx)
                prop = g_vars.eval_prop
                ref = g_vars.eval_ref
            else:
                ref = item['ref']
                prop = item['prop']

            # apply func
            func = item['func']

            try:
                if bl_item.is_array:
                    if bl_item.use_array is False:
                        val = getattr(ref, prop)[bl_item.array]
                        val2 = [func(bl_item, item, val)]
                    else:
                        val = getattr(ref, prop)
                        val2 = list(func(bl_item, item, val))
                else:
                    val = getattr(ref, prop)
                    val2 = [func(bl_item, item, val)]


                # the value has changed
                if val2 != item['val']:
                    item['val'] = val2

                    # for multi routes
                    val3 = val2.copy()
                    if bl_item.is_multi:
                        val3.insert(0, item['idx'])

                    addr = str.encode(item['address'])
                    g_vars.osc_client.send_message(addr, val3)

                    if bpy.context.window_manager.addroutes_osc_debug:
                        bpy.ops.addroutes.debuginfo(msg="OSC: Sending OK, route n°" + str(
                            item["n"]) + ', category :' + bl_item.category + ", value: " +str(val3))

            except:
                if bpy.context.window_manager.addroutes_osc_debug:
                    bpy.ops.addroutes.debuginfo(msg="OSC: Sending Error, improper OSC route n°"+str(item["n"])+', category :'+bl_item.category)
                    #    print('OSC Sending - route #', item['n'], addr, val2)


cls = (AddRoutes_Qlist_Open,
       AddRoutes_Qlist_Convert,
       AddRoutes_FaceCap_Open,
       AddRoutes_FaceCap_Convert
       )


def register():
    bpy.types.Scene.addroutes_fcapfile = bpy.props.StringProperty(name='FaceCap file')

    bpy.types.Scene.addroutes_fcap_offset = bpy.props.IntProperty(name='At frame', default=1,
                                                      description='At which frame convert the FaceCap file')

    bpy.types.Scene.addroutes_qlistfile = bpy.props.StringProperty(name='Qlist file')

    bpy.types.Scene.addroutes_qf_offset = bpy.props.IntProperty(name='At frame', default=1,
                                                      description='At which frame convert the Pd/Qlist file')

    bpy.app.timers.register(actua_osc_timer, persistent=True)
    bpy.app.handlers.frame_change_pre.append(osc_frame_upd)

    for c in cls:
        register_class(c)


def unregister():
    del bpy.types.Scene.addroutes_fcapfile
    del bpy.types.Scene.addroutes_fcap_offset
    del bpy.types.Scene.addroutes_qlistfile
    del bpy.types.Scene.addroutes_qf_offset
    bpy.app.timers.unregister(actua_osc_timer)
    bpy.app.handlers.frame_change_pre.remove(osc_frame_upd)
    for c in cls:
        unregister_class(c)


if __name__ == "__main__":
    register()
