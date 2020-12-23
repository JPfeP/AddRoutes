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

from . import g_vars

blem_server = None
bl_ok = False
stored = None

auto_port_out = None
auto_udp_out = None

upd_cnt = -1
blem_cnt = 0


def redraw_hack():
    # trick to update the GUI
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def retry_server():
    global blem_server, bl_ok
    pref = bpy.context.preferences.addons['AddRoutes'].preferences
    bcw = bpy.context.window_manager
    ip = pref.blemote_udp_in
    port = pref.blemote_port_in

    # open connection
    if pref.blemote_enable is True and bl_ok is False:
        # try closing a previous instance
        try:
            sock = blem_server.listen(address=ip, port=port, default=False)
            bcw.addroutes_blemote_alert = False
            bl_ok = True
            redraw_hack()

        except:
            if bcw.addroutes_blemote_alert is not True:
                bcw.addroutes_blemote_alert = True
                redraw_hack()

    # close connection
    if pref.blemote_enable is False and bl_ok is True:
        # try closing a previous instance
        blem_server.stop_all()
        bl_ok = False

    return 1


def blemote_poll():
    global auto_port_out, auto_udp_out, stored, upd_cnt, blem_cnt
    pref = bpy.context.preferences.addons['AddRoutes'].preferences
    if pref.blemote_autoconf:
        udp_out = auto_udp_out
        port_out = auto_port_out
    else:
        udp_out = pref.blemote_udp_out
        port_out = pref.blemote_port_out

    try:
        osc = OSCClient(udp_out, port_out, encoding='utf8')
        osc.send_message("/pong", [upd_cnt])

    except:
        return 1

    current = g_vars.addroutes_blemote

    if blem_cnt != upd_cnt:
        addr = str.encode('/BLEMOTE_ROUTES')
        osc.send_message(addr, [str.encode('START')])
        for p_rnk, item in g_vars.addroutes_blemote.items():
            dico = item[2]
            n = item[1]
            val = dico['min']

            bl_item = item[0]
            index = bl_item.array

            try:
                if bl_item.is_str2eval is False:
                    #print(dico['trigger'])
                    if bl_item.is_array:
                        val = getattr(dico['trigger']['ref'], dico['trigger']['prop'])[index]
                    else:
                        val = getattr(dico['trigger']['ref'], dico['trigger']['prop'])
            except:
                pass

            to_send = [p_rnk, n, dico['min'], dico['max'], dico['step'], dico['category'], val, bl_item.route_name]
            osc.send_message(addr, to_send)

        osc.send_message(addr, ['STOP'])
        #print('BLEMOTE ROUTES UPDATE')

    if current != stored:
        upd_cnt += 1
        stored = dict(current)

    return 2


def Blemote_callback(*args):
    global blem_server, auto_udp_out, auto_port_out, blem_cnt
    bcw = bpy.context.window_manager
    fail = True
    #bcw.addroutes_osc_lastaddr = args[0]
    content = ""
    args = list(args)

    # still needed to decode the address
    addr = args[0].decode('UTF-8')

     #for i in args[1:]:
    #    content += str(i) + " "
    #bpy.context.window_manager.addosc_lastpayload = content
    #print(args)

    p_rnk = args[1]
    if addr == '/blender':
        route_blemote = g_vars.addroutes_blemote.get(p_rnk)
        if route_blemote is None:
            return
        dico = route_blemote[2]
        n = route_blemote[1]
        item = route_blemote[0]
        if dico['engine'] == 'MIDI':
            chan = dico['trigger']['channel']
            cont_type = dico['trigger']['cont_type']
            controller = dico['trigger']['controller']
            g_vars.blemote_midi_fb.append([chan, cont_type, controller, args[2]])

        elif dico['engine'] == 'OSC':
            g_vars.osc_queue.append([dico['trigger'], args[2]])
            #print(dico['trigger'], args[1])

        elif dico['engine'] == 'Blemote':
            g_vars.blemote_fb.append([item, dico['trigger'], args[2], n])

    elif addr == '/ping':
        #print(blem_server.get_sender())
        auto_udp_out = blem_server.get_sender()[1]
        auto_port_out = args[1]
        blem_cnt = args[2]

    elif addr == '/Sequencer':
        for window in bpy.data.window_managers[0].windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'DOPESHEET_EDITOR':
                    override = {'window': window, 'screen': screen, 'area': area}

        if args[1] == 'Play':
            bpy.ops.screen.animation_play(override, sync=True)

        elif args[1] == 'Backward':
            bpy.ops.screen.animation_play(override, reverse= True, sync=True)

        elif args[1] == 'Start':
            bpy.ops.screen.frame_jump(override, end=False)
        elif args[1] == 'End':
            bpy.ops.screen.frame_jump(override, end=True)

        elif args[1] == 'KF+':
            bpy.ops.screen.keyframe_jump(override, next=True)
        elif args[1] == 'KF-':
            bpy.ops.screen.keyframe_jump(override, next=False)

        elif args[1] == 'Marker+':
            bpy.ops.screen.marker_jump(override, next=True)
        elif args[1] == 'Marker-':
            bpy.ops.screen.marker_jump(override, next=False)




blem_server = OSCThreadServer(encoding='utf8', default_handler=Blemote_callback)


def save_blemote_addr_in(self, context):
    pass
    #upd_settings_sub(20)
    #bpy.ops.addroutes.refresh_blemote()


def save_blemote_port_in(self, context):
    pass
    #upd_settings_sub(21)
    #bpy.ops.addroutes.refresh_blemote()


def save_blemote_addr_out(self, context):
    pass
    #upd_settings_sub(22)


def save_blemote_port_out(self, context):
    pass
    #upd_settings_sub(23)


cls = ()


def register():
    bpy.types.WindowManager.addroutes_blemote_udp_in = bpy.props.StringProperty(
        default="0.0.0.0",
        update=save_blemote_addr_in,
        description='The IP of the interface of your Blender machine to listen on, set to 0.0.0.0 for all of them')

    bpy.types.WindowManager.addroutes_blemote_udp_out = bpy.props.StringProperty(
        default="127.0.0.1",
        update=save_blemote_addr_out,
        description='The IP of Blemote to send messages to')

    bpy.types.WindowManager.addroutes_blemote_port_in = bpy.props.IntProperty(
        default=9003,
        min=0,
        max=65535,
        update=save_blemote_port_in,
        description='The input network port (0-65535)')

    bpy.types.WindowManager.addroutes_blemote_port_out = bpy.props.IntProperty(
        default=9004,
        min=0,
        max=65535,
        update=save_blemote_port_out,
        description='The output network port (0-65535)')

    bpy.types.WindowManager.addroutes_blemote_alert = bpy.props.BoolProperty()

    bpy.app.timers.register(retry_server, persistent=True)
    bpy.app.timers.register(blemote_poll, persistent=True)

    for c in cls:
        register_class(c)


def unregister():
    del bpy.types.WindowManager.addroutes_blemote_alert
    del bpy.types.WindowManager.addroutes_blemote_port_out
    del bpy.types.WindowManager.addroutes_blemote_port_in
    del bpy.types.WindowManager.addroutes_blemote_udp_out
    del bpy.types.WindowManager.addroutes_blemote_udp_in

    bpy.app.timers.unregister(retry_server)
    bpy.app.timers.unregister(blemote_poll)

    for c in cls:
        unregister_class(c)


if __name__ == "__main__":
    register()