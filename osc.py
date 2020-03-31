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
from bpy.app.handlers import persistent
from mathutils import *

from oscpy.server import OSCThreadServer
from oscpy.client import OSCClient

import g_vars
from data import upd_settings_sub

import time
#import sys

osc_server = None
osc_in_ok = False


def set_props(item, bl_item, val):
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
        getattr(ref, prop)[bl_item.array] = post_func(current, result, bl_item)
    else:
        current = getattr(ref, prop)
        result2 = post_func(current, result, bl_item)
        setattr(ref, prop, result2)

    # insert keyframe
    if bl_item.record and bpy.data.screens[0].is_animation_playing:
        if bl_item.is_array and (bl_item.use_array is False):
            index = bl_item.array
            ref.keyframe_insert(data_path=prop, index=index, **item['ks_params'])
        else:
            ref.keyframe_insert(data_path=prop, **item['ks_params'])


def actua_osc():
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
                print("\nOSC - Receiving:", msg)

            for n, bl_item, dico_arr in g_vars.addroutes_osc_in.get(addr, []):
                try:
                    # getting index and a ref for the blender item
                    idx = bl_item.osc_select_rank
                    val2 = val[idx:idx+bl_item.osc_select_n]          # val2 matters

                    if bl_item.is_multi is True:
                        dico = dico_arr.get(str(int(multi_idx)))
                        if dico is not None:
                            set_props(dico, bl_item, val2)
                        # debug in console
                        if bpy.context.window_manager.addroutes_osc_debug is True:
                            print("---> OK route #"+str(n), ", category: "+bl_item.category, ", updating with:", val2)
                            debug_flag = True
                    elif bl_item.is_multi is False:
                        dico = dico_arr["0"]
                        set_props(dico, bl_item, val2)
                        # debug in console
                        if bpy.context.window_manager.addroutes_osc_debug is True:
                            print("---> OK route #"+str(n), ", category: "+bl_item.category, ", updating with:", val2)
                            debug_flag = True

                except:
                    #print("Unexpected error:", sys.exc_info()[0])
                    if bpy.context.window_manager.addroutes_osc_debug is True:
                        print("---> ERROR with route #"+str(n), ", category: "+bl_item.category)
                        debug_flag = True

            # if no route has triggered a debug_flag
            if bpy.context.window_manager.addroutes_osc_debug is True and debug_flag is False:
                print("... but no matching route")

    return prefs.refresh/1000


def OSC_callback(*args):
    bcw = bpy.context.window_manager
    fail = True

    args = list(args)

    # still needed to decode the address
    args[0] = args[0].decode('UTF-8')

    g_vars.osc_queue.append(args)


osc_server = OSCThreadServer(encoding='utf8', default_handler=OSC_callback)


def save_osc_udp_in(self, context):
    global osc_in_ok, osc_server
    upd_settings_sub(10)
    osc_in_ok = False
    osc_server.stop_all()


def save_osc_port_in(self, context):
    global osc_in_ok
    upd_settings_sub(11)
    osc_in_ok = False
    osc_server.stop_all()


def save_osc_udp_out(self, context):
    upd_settings_sub(12)


def save_osc_port_out(self, context):
    upd_settings_sub(13)


def save_osc_in_enable(self, context):
    upd_settings_sub(14)


def save_osc_out_enable(self, context):
    upd_settings_sub(15)


@persistent
def osc_frame_upd(scn):
    # kludge to avoid error while changing scene
    if g_vars.scene is not scn:
        return

    # send osc events
    bcw = bpy.context.window_manager
    osc = OSCClient(bcw.addroutes_osc_udp_out, bcw.addroutes_osc_port_out, encoding='utf8')

    if bcw.addroutes_osc_out_enable is True:
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
                    osc.send_message(addr, val3)

            except:
                print("Error while sending, improper OSC route #", item["n"], 'category :', bl_item.category)
            break

                #if bpy.context.window_manager.addroutes_osc_debug:
                #    print('OSC Sending - route #', item['n'], addr, val2)


def redraw_hack():
    # trick to update the GUI
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def retry_server():
    global osc_server, osc_in_ok
    bcw = bpy.context.window_manager
    ip = bcw.addroutes_osc_udp_in
    port = bcw.addroutes_osc_port_in

    # open connection
    if bcw.addroutes_osc_in_enable is True and osc_in_ok is False:
        # try opening
        try:
            sock = osc_server.listen(address=ip, port=port, default=False)
            bcw.addroutes_osc_alert = False
            osc_in_ok = True
            redraw_hack()

        except:
            if bcw.addroutes_osc_alert is not True:
                bcw.addroutes_osc_alert = True
                redraw_hack()

    # close connection
    if bcw.addroutes_osc_in_enable is False and osc_in_ok is True:
        # try closing a previous instance
        osc_server.stop_all()
        osc_in_ok = False

    return 1


cls = ( #AddRoutes_Refresh_OSC,
       )


def register():
    bpy.types.WindowManager.addroutes_osc_udp_in = bpy.props.StringProperty(
        default="0.0.0.0",
        update=save_osc_udp_in,
        description='The IP of the interface of your Blender machine to listen on, set to 0.0.0.0 for all of them')

    bpy.types.WindowManager.addroutes_osc_udp_out = bpy.props.StringProperty(
        default="127.0.0.1",
        update=save_osc_udp_out,
        description='The IP of the destination machine to send messages to')

    bpy.types.WindowManager.addroutes_osc_port_in = bpy.props.IntProperty(
        default=9001,
        min=0,
        max=65535,
        update=save_osc_port_in,
        description='The input network port (0-65535)')

    bpy.types.WindowManager.addroutes_osc_port_out = bpy.props.IntProperty(
        default=9002,
        min=0,
        max=65535,
        update=save_osc_port_out,
        description='The output network port (0-65535)')

    bpy.types.WindowManager.addroutes_osc_alert = bpy.props.BoolProperty()
    bpy.types.WindowManager.addroutes_osc_debug = bpy.props.BoolProperty(
        description='Debug incoming OSC messages in console. Warning: Can be slow !')
    bpy.types.WindowManager.addroutes_osc_in_enable = bpy.props.BoolProperty(update=save_osc_in_enable)
    bpy.types.WindowManager.addroutes_osc_out_enable = bpy.props.BoolProperty(update=save_osc_out_enable)

    bpy.app.timers.register(actua_osc, persistent=True)
    bpy.app.timers.register(retry_server, persistent=True)
    bpy.app.handlers.frame_change_pre.append(osc_frame_upd)

    for c in cls:
        register_class(c)


def unregister():
    del bpy.types.WindowManager.addroutes_osc_udp_in
    del bpy.types.WindowManager.addroutes_osc_udp_out
    del bpy.types.WindowManager.addroutes_osc_port_in
    del bpy.types.WindowManager.addroutes_osc_port_out
    del bpy.types.WindowManager.addroutes_osc_alert
    del bpy.types.WindowManager.addroutes_osc_debug
    del bpy.types.WindowManager.addroutes_osc_in_enable
    del bpy.types.WindowManager.addroutes_osc_out_enable
    bpy.app.timers.unregister(actua_osc)
    bpy.app.timers.unregister(retry_server)
    bpy.app.handlers.frame_change_pre.remove(osc_frame_upd)
    for c in cls:
        unregister_class(c)


if __name__ == "__main__":
    register()
