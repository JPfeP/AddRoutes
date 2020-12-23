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

from oscpy.server import OSCThreadServer
from oscpy.client import OSCClient
import time

import ifaddr

from . import g_vars
from .load_save import save_settings


def actua_bl():
    prefs = bpy.context.preferences.addons['AddRoutes'].preferences
    in_len = len(g_vars.blemote_fb)

    if in_len > prefs.overflow:
        g_vars.blemote_fb = g_vars.blemote_fb[:prefs.overflow]
        bpy.context.window_manager.n_overflow += 1

    for i in range(prefs.overflow):
        if len(g_vars.blemote_fb) == 0:
            break
        else:
            msg = g_vars.blemote_fb.pop(0)
            bl_item = msg[0]
            item = msg[1]
            val = float(msg[2])
            n = msg[3]

            func = item['func']
            post_func = item['post_func']

            # scene can change in the meanwhile
            try:
                result = func(bl_item, item, val)

                if bl_item.is_str2eval:
                    g_vars.evalprop(bl_item.str2eval, bl_item.withctx)
                    prop = g_vars.eval_prop
                    ref = g_vars.eval_ref
                else:
                    ref = item['ref']
                    prop = item['prop']

                if bl_item.is_array:
                    current = getattr(ref, prop)[bl_item.array]
                    result2 = post_func(current, result, bl_item)
                    getattr(ref, prop)[bl_item.array] = result2
                else:
                    current = getattr(ref, prop)
                    result2 = post_func(current, result, bl_item)
                    setattr(ref, prop, result2)

                # insert keyframe
                if bl_item.record and bpy.data.screens[0].is_animation_playing:
                    if bl_item.is_array:
                        index = bl_item.array
                        ref.keyframe_insert(data_path=prop, index=index, **item['ks_params'])
                    else:
                        ref.keyframe_insert(data_path=prop, **item['ks_params'])

                if bpy.context.window_manager.addroutes_blemote_debug:
                    debug_msg = "Blemote: OK route n°" + str(n) + ", category: " + bl_item.category + ", updating to:" + str(result2) + ", using:" + str(val)
                    bpy.ops.addroutes.debuginfo(msg=debug_msg)

            except:
                if bpy.context.window_manager.addroutes_blemote_debug:
                    bpy.ops.addroutes.debuginfo(msg="Blemote: Update error, improper route n°" + str(n) + ", category: " + bl_item.category)

    return prefs.refresh/1000


class AddRoutes_ShowBlenderIP(bpy.types.Operator):
    """Show in the INFO window the possible Blender IP's to fill in the Blemote App Destination"""
    bl_idname = "addroutes.showblenderip"
    bl_label = "Show the IPs of Blender"

    def execute(self, context):
        adapters = ifaddr.get_adapters()

        for adapter in adapters:
            if adapter.nice_name != "lo":
                str_adapter = "IP of network adapter " + adapter.nice_name
                ip = adapter.ips[0]
                ip_data = str(ip.ip)
                self.report({'INFO'}, str_adapter + " : " + ip_data)

        return{'FINISHED'}


cls = (AddRoutes_ShowBlenderIP,
       )


def register():
    bpy.types.WindowManager.addroutes_blemote_debug = bpy.props.BoolProperty(
        name="Debug Blemote",
        default=False,
        description="Debug Blemote incoming messages"
    )

    bpy.app.timers.register(actua_bl, persistent=True)

    for c in cls:
        register_class(c)


def unregister():
    del bpy.types.WindowManager.addroutes_blemote_debug

    bpy.app.timers.unregister(actua_bl)

    for c in cls:
        unregister_class(c)


if __name__ == "__main__":
    register()