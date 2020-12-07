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

from oscpy.server import OSCThreadServer
from oscpy.client import OSCClient

from . import g_vars

osc_server = None
osc_in_ok = False
ip = None
port = None


def OSC_callback(*args):
    bcw = bpy.context.window_manager
    fail = True

    args = list(args)

    # still needed to decode the address
    args[0] = args[0].decode('UTF-8')

    g_vars.osc_queue.append(args)


osc_server = OSCThreadServer(encoding='utf8', default_handler=OSC_callback)


# for change of mode
def update_osc_mode(self, context):
    update_osc_in_enable(self, context)
    update_osc_out_enable(self, context)

    update_osc_in(self, context)
    update_osc_out(self, context)


def update_osc_in_enable(self, context):
    prefs = bpy.context.preferences.addons['AddRoutes'].preferences
    bcw = bpy.context.window_manager

    if bcw.addroutes_osc_settings == 'Project':
        g_vars.osc_in_enable = bcw.addroutes_osc_in_enable
    else:
        g_vars.osc_in_enable = prefs.osc_in_enable


def update_osc_out_enable(self, context):
    prefs = bpy.context.preferences.addons['AddRoutes'].preferences
    bcw = bpy.context.window_manager

    if bcw.addroutes_osc_settings == 'Project':
        g_vars.osc_out_enable = bcw.addroutes_osc_out_enable
    else:
        g_vars.osc_out_enable = prefs.osc_out_enable


def update_osc_in(self, context):
    global osc_in_ok, osc_server, osc_in_ok, ip, port

    prefs = bpy.context.preferences.addons['AddRoutes'].preferences
    bcw = bpy.context.window_manager

    osc_in_ok = False
    osc_server.stop_all()

    if bcw.addroutes_osc_settings == 'Project':
        ip = bcw.addroutes_osc_udp_in
        port = bcw.addroutes_osc_port_in
    else:
        ip = prefs.osc_udp_in
        port = prefs.osc_port_in


def update_osc_out(self, context):
    prefs = bpy.context.preferences.addons['AddRoutes'].preferences
    bcw = bpy.context.window_manager

    if bcw.addroutes_osc_settings == 'Project':
        ip_out = bcw.addroutes_osc_udp_out
        port_out = bcw.addroutes_osc_port_out
    else:
        ip_out = prefs.osc_udp_out
        port_out = prefs.osc_port_out

    try:
        g_vars.osc_client = OSCClient(ip_out, port_out, encoding='utf8')
        addr = str.encode("/blender_info")
        g_vars.osc_client.send_message(addr, ["Hello, my name is Blender... and I'm not a tin can !"])
        bcw.addroutes_osc_out_alert = False
    except:
        bcw.addroutes_osc_out_alert = True


def redraw_hack():
    # trick to update the GUI
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def retry_server():
    global osc_server, osc_in_ok, ip, port
    bcw = bpy.context.window_manager

    # Hack to handle script reloading
    if ip is None:
        #print("AddRoutes: Reload Script detected, updating connections")
        update_osc_mode(None, None)

    # open connection
    if g_vars.osc_in_enable and osc_in_ok is False:
        # try opening
        try:
            sock = osc_server.listen(address=ip, port=port, default=False)
            bcw.addroutes_osc_in_alert = False
            osc_in_ok = True
            redraw_hack()

        except:
            if bcw.addroutes_osc_in_alert is False:
                bcw.addroutes_osc_in_alert = True
                redraw_hack()

    # close connection
    if g_vars.osc_in_enable is False and osc_in_ok is True:
        # try closing a previous instance
        osc_server.stop_all()
        osc_in_ok = False

    return 1


cls = (
       )


def register():
    global osc_in_ok
    bpy.types.WindowManager.addroutes_osc_settings = bpy.props.EnumProperty(
        name="OSC configuration",
        items=[('System', 'System', 'System', 0),
               ('Project', 'Project', 'Project', 1)],
        update=update_osc_mode
    )

    bpy.types.WindowManager.addroutes_osc_udp_in = bpy.props.StringProperty(
        default="0.0.0.0",
        update=update_osc_in,
        description='The IP of the interface of your Blender machine to listen on, set to 0.0.0.0 for all of them')

    bpy.types.WindowManager.addroutes_osc_udp_out = bpy.props.StringProperty(
        default="127.0.0.1",
        update=update_osc_out,
        description='The IP of the destination machine to send messages to')

    bpy.types.WindowManager.addroutes_osc_port_in = bpy.props.IntProperty(
        default=9001,
        min=0,
        max=65535,
        update=update_osc_in,
        description='The input network port (0-65535)')

    bpy.types.WindowManager.addroutes_osc_port_out = bpy.props.IntProperty(
        default=9002,
        min=0,
        max=65535,
        update=update_osc_out,
        description='The output network port (0-65535)')

    bpy.types.WindowManager.addroutes_osc_in_alert = bpy.props.BoolProperty()
    bpy.types.WindowManager.addroutes_osc_out_alert = bpy.props.BoolProperty()
    bpy.types.WindowManager.addroutes_osc_debug = bpy.props.BoolProperty(
        description='Debug in/out OSC messages. Warning: Can be slow !',
        update=g_vars.debugcopy
    )
    bpy.types.WindowManager.addroutes_osc_in_enable = bpy.props.BoolProperty(update=update_osc_in_enable,
                                                                             description='Enable OSC Input')
    bpy.types.WindowManager.addroutes_osc_out_enable = bpy.props.BoolProperty(update=update_osc_out_enable,
                                                                              description='Enable OSC Output')

    bpy.app.timers.register(retry_server, persistent=True)

    for c in cls:
        register_class(c)

    #osc_in_ok = False


def unregister():
    del bpy.types.WindowManager.addroutes_osc_udp_in
    del bpy.types.WindowManager.addroutes_osc_udp_out
    del bpy.types.WindowManager.addroutes_osc_port_in
    del bpy.types.WindowManager.addroutes_osc_port_out
    del bpy.types.WindowManager.addroutes_osc_in_alert
    del bpy.types.WindowManager.addroutes_osc_out_alert
    del bpy.types.WindowManager.addroutes_osc_debug
    del bpy.types.WindowManager.addroutes_osc_in_enable
    del bpy.types.WindowManager.addroutes_osc_out_enable
    bpy.app.timers.unregister(retry_server)
    osc_server.stop_all()
    for c in cls:
        unregister_class(c)


if __name__ == "__main__":
    register()