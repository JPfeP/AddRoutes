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


from __future__ import print_function

import logging
import sys
import time
from collections import defaultdict

import os

import bpy
from bpy.utils import register_class, unregister_class
from bpy.app.handlers import persistent
from bpy_extras.io_utils import ImportHelper
import functools

import mido
from mido import MidiFile

from . import g_vars

from .data import generate_dict
from .data import yield_all_routes
from .load_save import build_idx

MIDI_sent_values = [0 for i in range(1000)]

msg = []

CC_6 = [0 for i in range(16)]
CC_38 = [0 for i in range(16)]
CC_100 = [0 for i in range(16)]
CC_101 = [0 for i in range(16)]
CC_98 = [0 for i in range(16)]
CC_99 = [0 for i in range(16)]

# Some global variables
tempo = 120
fps = 24
clock = 0
running_status = 0
startpos = 0
pos_frame = -1
midifile_array = []

scn = None
midifile_conv = False
mf_frame = {}

is_playing = False

mf_deluxe = True


def get_ctx_scene():
    global scn
    try:
        get_scn = bpy.data.window_managers[0].windows[0].scene

        #get_scn = bpy.data.scenes[scn.name]
        if get_scn != scn:
            scn = get_scn
            build_idx()
            #bpy.ops.addroutes.gendict()
            generate_dict(None, bpy.data.window_managers[0].windows[0])
            send_clock(scn, scn)
    except:
        print('No Context Scene, waiting...')
        scn = None
    return 0.3


def actua_timer():
    prefs = bpy.context.preferences.addons['AddRoutes'].preferences
    scn = bpy.data.window_managers[0].windows[0].scene

    if g_vars.midiin is not None and scn is not None:

        for i in range(prefs.overflow):
            msg = g_vars.midiin.get_message()
            if msg:
                arr = decode(scn, msg[0])
                # trick to prevent Struct RNA of type Scene has been removed
                actualise(scn, arr)

        msg = g_vars.midiin.get_message()
        cnt = 1024 - prefs.overflow
        if msg is not None and cnt > 0:
            for i in range(cnt):
                msg = g_vars.midiin.get_message()
            bpy.context.window_manager.n_overflow += 1

    # for blemote injection
    if scn is not None:
        for i in range(prefs.overflow):
            if len(g_vars.blemote_midi_fb) > 0:
                arr = g_vars.blemote_midi_fb.pop(0)
                actualise(scn, arr)
        g_vars.blemote_midi_fb = []

    return prefs.refresh/1000


# This for applying the scale given by the user for each key
def rescale(val, min, max, quant):
    if quant != 0:
        return (val / quant) * (max - min) + min
    else:
        return min


#This to limit the sent values in a proper range
def clamp(minimum, x, maximum):
    return max(minimum, min(x, maximum))


def set_props(item, bl_item, val):
    global midifile_conv

    # testing rescale feature mode
    if bl_item.rescale_mode == 'Direct':
        result = val

    elif bl_item.rescale_mode == 'Auto':
        # no need to clamp
         result = rescale(val, bl_item.rescale_blender_low, bl_item.rescale_blender_high, item['quant'])

    elif bl_item.rescale_mode == "Cut":
        if val < bl_item.rescale_outside_low or val > bl_item.rescale_outside_high:
            return
        else:
            val = clamp(bl_item.rescale_outside_low, val, bl_item.rescale_outside_high)
            result = rescale(val, bl_item.rescale_blender_low, bl_item.rescale_blender_high, item['quant'])

    elif bl_item.rescale_mode == 'Wrap':
        val = clamp(bl_item.rescale_outside_low, val, bl_item.rescale_outside_high)
        result = rescale(val, bl_item.rescale_blender_low, bl_item.rescale_blender_high, item['quant'])

    func = item['func']
    result = func(bl_item, item, result)
    post_func = item['post_func']

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
    if bl_item.record and (bpy.data.screens[0].is_animation_playing or midifile_conv):
        if bl_item.is_array:
            index = bl_item.array
            ref.keyframe_insert(data_path=prop, index=index, **item['ks_params'], **mf_frame)
        else:
            ref.keyframe_insert(data_path=prop, **item['ks_params'], **mf_frame)

    return result2


def actualise(scn, msg):
    chan = str(msg[0])
    cont = msg[1]

    if msg == 'pass':
        return

    toexec = g_vars.addroutes_in[chan][cont]

    if bpy.context.window_manager.addroutes_midi_debug is True:
        debug = None
        debug_msg = "MIDI - Receiving on channel: " + chan + ", event: " + cont + ", payload:" + str(msg[2:])

    for n, bl_item, dico_arr in toexec:
        # getting index and a ref for the blender item

        try:
            # test if filtering is needed, to use p1 or p2
            # NOTE: filter is always True for Multi
            if bl_item.filter is True:
                dico = dico_arr.get(str(msg[2]))
                if dico is not None:
                    val = msg[3]
                    result2 = set_props(dico, bl_item, val)
            elif bl_item.filter is False:
                dico = list(dico_arr.values())[0]
                idx = 1

                if dico['option'] == '':
                    idx = 0
                val = msg[2+idx]
                result2 = set_props(dico, bl_item, val)

            if bpy.context.window_manager.addroutes_midi_debug is True:
                if dico is not None:
                    debug_msg += "\n---> OK route n°"+str(n)+", category: " + bl_item.category+", updating property to :" + str(result2) + " using:" + str(val)
                    bpy.ops.addroutes.debuginfo(msg=debug_msg)
                else:
                    debug_msg += "\n---> OK route n°"+str(n)+", category: "+bl_item.category+"... but filtered out"
                    bpy.ops.addroutes.debuginfo(msg=debug_msg)
                debug = True
        except:
            if bpy.context.window_manager.addroutes_midi_debug is True:
                debug_msg += "\n... but something went wrong with route n°"+str(n)+", category: "+bl_item.category
                bpy.ops.addroutes.debuginfo(msg=debug_msg)
                debug = True

    if bpy.context.window_manager.addroutes_midi_debug is True:
        if debug is None:
            debug_msg += "\n... but no matching route"
            bpy.ops.addroutes.debuginfo(msg=debug_msg)


def seq_do(scn, do):
    if scn.sync:
        #window = bpy.context.window_manager.windows[0]
        #ctx = {'window': window, 'screen': window.screen}

        for window in bpy.data.window_managers[0].windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    override = {'window': window, 'screen': screen, 'area': area}
                    if do == 'START':
                        bpy.ops.screen.frame_jump(override, end=False)
                        bpy.ops.screen.animation_play(override, sync=True)
                    elif do == 'CONTINUE':
                        pass
                        bpy.ops.screen.animation_play(override, sync=True)
                    elif do == 'STOP':
                        pass
                        bpy.ops.screen.animation_cancel(override, restore_frame=False)
                    # else:
                    #     fc = bpy.data.scenes["Scene"].frame_current
                    #     diff = do - fc
                    #     bpy.ops.screen.frame_offset(override, delta=diff)
                    break


def eval_bf(scn):
    fps = scn.render.fps

    tempo = scn.tempo
    beatframe = (60 / tempo) * fps
    return beatframe


def frame_upd(scn):
    global pos_frame
    current = scn.frame_current
    if scn.SPP is True and pos_frame != current:
        scn.frame_set(pos_frame)
        #print('JUMP TO FRAME ', pos_frame)


def decode(scn, message):
    global running_status, clock, startpos, pos_frame
    type = int(message[0] / 16)
    chan = message[0] % 16 + 1
    res = 'pass'

    if len(message) > 1:
        p1 = message[1]

    if len(message) > 2:
        p2 = message[2]

    if type == 9:       #Note On
        res = chan, 'key_on', p1, p2

    elif type == 8:    #Note Off
        if scn.off_to_0:
            res = chan, 'key_on', p1, 0
        else:
            res = chan, 'key_off', p1, p2

    elif type == 11:    #Control Change
        res = chan, 'cc7', p1, p2
        # handling rpn/nrpn
        if p1 == 6:
            CC_6[chan] = p2
        elif p1 == 38:
            CC_38[chan] = p2
        # For NRPN
        elif p1 == 99:
            CC_99[chan] = p2
        elif p1 == 98:
            # 14 bit
            nrpn_p1 = CC_99[chan] * 128 + p2
            nrpn_p2 = CC_6[chan] * 128 + CC_38[chan]
            res = chan, 'nrpn14', nrpn_p1, nrpn_p2
            # 7 bit
            nrpn_p2 = CC_6[chan]
            res = chan, 'nrpn', nrpn_p1, nrpn_p2
        # For RPN
        elif p1 == 101:
            CC_101[chan] = p2
        elif p1 == 100:
            # 14 bit
            nrpn_p1 = CC_101[chan] * 128 + p2
            nrpn_p2 = CC_6[chan] * 128 + CC_38[chan]
            res = chan, 'rpn14', nrpn_p1, nrpn_p2
            # 7 bit
            nrpn_p2 = CC_6[chan]
            res = chan, 'rpn', nrpn_p1, nrpn_p2

    elif type == 12:
        res = chan, 'pgm', p1, p1

    elif type == 13:    #Mono AT
        res = chan, 'AT_mono', p1, p1

    elif type == 10:    #Poly AT
        res = chan, 'AT_poly', p1, p2

    elif type == 14:    #Pitchbend: 14bit !
        p2 = p2 * 128 + p1
        res = chan, 'pitchbend', p2, p2

    # for MIDI sync
    if running_status == 1 and message[0] == 248: #clock
        clock += 1
    if message[0] == 250:
        running_status = 1
        clock = 0
        startpos = scn.frame_current
        seq_do(scn, 'START')
    if message[0] == 251:
        seq_do(scn, 'CONTINUE')

    if message[0] == 252:
        seq_do(scn, 'STOP')
        running_status = 0

    # for Song Pointer Position
    if message[0] == 242:
        locbeat = (message[1] + (128 * message[2])) / 4
        frame = locbeat * eval_bf(scn)
        pos_frame = int(frame)
        frame_upd(scn)

    return res


# to be removed ?
def addroutes_send():
    global addroutes_in
    for item in addroutes_in:
        g_vars.midiout.send_message([0])


def clock_timer(self):
    delay = (60 / self.tempo) / 24
    #scn = bpy.data.window_managers[0].windows[0].scene
    scn = self

    if self.midi_clock_out is False:
        return None

    if g_vars.midiout.is_port_open() and scn is not None:
        g_vars.midiout.send_message([248])

        return delay


def send_clock(self, context):
    if self.midi_clock_out is True:
        bpy.app.timers.register(functools.partial(clock_timer, self))
    #bpy.app.timers.register(send_clock)


class AddRoutes_Open_Midifile(bpy.types.Operator, ImportHelper):
    """Select Midifile"""
    bl_idname = "addroutes.openmidifile"
    bl_label = "Open"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filename: bpy.props.StringProperty()
    filter_glob: bpy.props.StringProperty(
        default="*.mid",
        options={'HIDDEN'})

    def execute(self, context):
        filename, extension = os.path.splitext(self.filepath)
        context.scene.midifile = bpy.path.relpath(self.filepath)
        bpy.ops.addroutes.midifile_parse()
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filename = ""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class AddRoutes_Midifile_Convert(bpy.types.Operator):
    '''Convert Midifile to F-curves'''
    bl_idname = "addroutes.midifile"
    bl_label = "Convert Midifile"

    def execute(self, context):
        global midifile_conv
        midifile_conv = True

        try:
            if context.scene.midifile[0] != "/":
                context.scene.midifile = "//"+context.scene.midifile
            current_file = bpy.path.abspath(context.scene.midifile)
            mid = MidiFile(current_file)
        except:
            midifile_conv = False
            self.report({'INFO'}, "Midifile not found")
            return {'FINISHED'}

        beat_dur = 60 / context.scene.tempo
        tick = beat_dur / mid.ticks_per_beat
        #context.scene.tempo = tempo

        # creating an empty array to later prevent notes "extrapolation"
        extraspoil = [[False for j in range(128)] for i in range(16)]

        timeline = 0
        for msg in mid:
            timeline += msg.time
            # to move the play head later
            pos_frame = timeline * context.scene.render.fps

            arr = decode(context.scene, msg.bytes())

            # feature to prevent extrapolation
            if context.scene.mf_extraspoil:
                # testing if noteon is first ever
                if arr[1] == 'key_on':
                    chan = arr[0]
                    key = arr[2]
                    vel = arr[3]
                    if vel != 0:
                        if extraspoil[chan][key] is False:
                            extraspoil[chan][key] is True
                            if timeline > 0:
                                # inserting a noteoff at frame 0
                                arr_extra = chan, 'key_on', key, 0
                                #context.scene.frame_set(context.scene.frame_start)
                                mf_frame['frame'] = context.scene.mf_offset - 1
                                actualise(context.scene, arr_extra)

            #context.scene.frame_set(pos_frame)
            mf_frame['frame'] = pos_frame + context.scene.mf_offset
            actualise(context.scene, arr)

        mf_frame.pop('frame', None)
        midifile_conv = False

        for i, item in yield_all_routes():
            if item.env_auto:
                if item.category == 'SYSTEM':
                    j = 1
                else:
                    j = 0
                bpy.ops.addroutes.midienv(r=(i, j, 0))

        self.report({'INFO'}, "File conversion done")
        return {'FINISHED'}


class AddRoutes_Midifile_Parse(bpy.types.Operator):
    '''Reload and Parse Midifile'''
    bl_idname = "addroutes.midifile_parse"
    bl_label = "Reload and Parse Midifile"

    def execute(self, context):
        global midifile_array
        try:
            if context.scene.midifile[0] != "/":
                context.scene.midifile = "//"+context.scene.midifile
            current_file = bpy.path.abspath(context.scene.midifile)
            mid = MidiFile(current_file)
        except:
            self.report({'INFO'}, "Midifile not found")
            return {'FINISHED'}

        beat_dur = 60 / context.scene.tempo
        tick = beat_dur / mid.ticks_per_beat


        # 1 - Simple method
        # populate the midifile array with some empty arrays
        midifile_array = []

        timeline = 0
        for msg in mid:
            if msg.type == 'set_tempo':
                context.scene.tempo = 60000000 / msg.tempo
            timeline += msg.time
            pos_frame = int(timeline * context.scene.render.fps)

            # to auto extend the array if needed
            diff = pos_frame - len(midifile_array)
            if diff >= 0:
                for i in range(diff+1):
                    midifile_array.append([])
            midifile_array[pos_frame].append(msg.bytes())

        # 2 - Deluxe
        '''
        mf_delux_pre = []
        timeline = 0
        for msg in mid:
            if msg.type == 'set_tempo':
                context.scene.tempo = 60000000 / msg.tempo
            timeline += msg.time
            pos_frame = int(timeline * context.scene.render.fps)

            # to auto extend the array if needed
            diff = pos_frame - len(mf_delux_pre)
            if diff >= 0:
                for i in range(diff + 1):
                    mf_delux_pre.append([])
            decoded = decode(context.scene, msg.bytes())
            print(decoded)
            if decoded != 'pass':
                mf_delux_pre[pos_frame].append(decoded)

        for i, item in enumerate(mf_delux_pre):
            print (i,item)
        '''

        self.report({'INFO'}, "Midifile Parsing Done")
        return {'FINISHED'}

'''
def Deluxe_mf():
    for msg in mid:
'''


class AddRoutes_Midi_Play(bpy.types.Operator):
    '''Play from start while sending midi clock '''
    bl_idname = "addroutes.midiplay"
    bl_label = "Play while sending clock"

    def execute(self, context):
        global is_playing
        if g_vars.midiout.is_port_open():
            g_vars.midiout.send_message([250])
            bpy.ops.screen.animation_cancel(restore_frame=False)
            bpy.ops.screen.frame_jump(end=False)
            bpy.ops.screen.animation_play(sync=True)
            is_playing = True
        return {'FINISHED'}


class AddRoutes_Midi_Env(bpy.types.Operator):
    '''Apply an envelope on fcurves'''
    bl_idname = "addroutes.midienv"
    bl_label = "Apply envelope on noteon curves"

    r: bpy.props.IntVectorProperty()

    def execute(self, context):
        route = g_vars.get_item(self.r[0], self.r[1])
        GRP = route.kf_group
        if GRP == '':
            self.report({'INFO'}, 'Group name is empty !')
            return {'FINISHED'}

        frame_duration = 1000 / context.scene.render.fps
        RAMP_UP = route.env_attack / frame_duration
        #RAMP_UP_MODE = 'before'

        RAMP_DOWN = route.env_release / frame_duration
        #RAMP_DOWN_MODE = 'after'

        RAMP_SUM = RAMP_UP + RAMP_DOWN

        for action in bpy.data.actions:
            if hasattr(action, 'groups'):
                if action.groups.get(GRP) is not None:
                    fcurves = action.groups[GRP].channels
                    for fcurve in fcurves:
                        # getting a immutable array of points
                        pts = []
                        pts_new = []
                        for pt in fcurve.keyframe_points:
                            pts.append(list(pt.co))

                        # iterating over sections
                        lenx = len(pts)
                        for i in range(lenx - 1):
                            if i > 0:
                                h1 = pts[i - 1][1]
                            h2 = pts[i + 1][1]

                            # we only need to fill gaps for now
                            if pts[i][1] == 0:
                                diff = pts[i + 1][0] - pts[i][0]

                                # need to calculate intersection point if range is too narrow
                                if diff < RAMP_SUM and pts[i][0] != 0:
                                    # intersection of the 2 lines -> y = d + px
                                    # line1 - Release : y = h1 - R_Dx
                                    # line2 - Attack :  y = (h2 - diff * R_U) + R_Ux
                                    # x = (d1 - d2) / (R_D + R_U)
                                    R_D_RATE = h1 / RAMP_DOWN
                                    R_U_RATE = h2 / RAMP_UP
                                    d2 = h2 - diff * R_U_RATE
                                    x = (h1 - d2) / (R_D_RATE + R_U_RATE)
                                    y = h1 - R_D_RATE * x
                                    pts_new.append((pts[i][0]+x, y))

                                else:
                                    # the range is wide enough for 2 pts
                                    if pts[i][0] != context.scene.mf_offset:
                                        pts_new.append((pts[i][0] + RAMP_DOWN, 0))
                                    pts_new.append((pts[i + 1][0] - RAMP_UP, 0))

                                # at any rate, we need to "reshape" the flip flop curve by moving original pt
                                if pts[i][0] > context.scene.mf_offset:
                                    fcurve.keyframe_points[i].co[1] = h1

                        # closing
                        pts_new.append((pts[-1][0] + RAMP_DOWN, 0))
                        fcurve.keyframe_points[-1].co[1] = pts[i][1]

                        # starting
                        pts_new.append((pts[0][0] - RAMP_UP, 0))

                        # actually creating points
                        for pt in pts_new:
                            #print("inserting", pt)
                            fcurve.keyframe_points.insert(pt[0], pt[1])

                        # change the interpolation mode
                        for pt in fcurve.keyframe_points:
                            pt.interpolation = 'LINEAR'

        self.report({'INFO'}, "Post processing done")
        return {'FINISHED'}


class AddRoutes_Midi_Pause(bpy.types.Operator):
    '''Pause or Continue while sending midi clock '''
    bl_idname = "addroutes.midicont"
    bl_label = "Pause or continue while sending clock"

    def execute(self, context):
        global is_playing
        if g_vars.midiout.is_port_open() and context.scene.midi_clock_out:
            if is_playing is True:
                g_vars.midiout.send_message([252])
                is_playing = False
                bpy.ops.screen.animation_cancel(restore_frame=False)
            else:
                g_vars.midiout.send_message([251])
                is_playing = True
                bpy.ops.screen.animation_play(sync=True)
        return {'FINISHED'}


prev_frame = 0
@persistent
def midi_frame_upd(scn):
    # kludge to avoid error while changing scene
    if g_vars.scene is not scn:
        return

    # for midifile live playing
    global midifile_array, prev_frame

    # frame change pre is buggy !
    # print(scn.frame_current)

    if scn.mf_play and bpy.data.screens[0].is_animation_playing:
        n_to_play = scn.frame_current - scn.mf_offset
        if (len(midifile_array) > n_to_play) and (n_to_play >= 0):
            for msg in midifile_array[n_to_play]:
                arr = decode(scn, msg)
                actualise(scn, arr)

    # this is for SPP out
    new_frame = scn.frame_current
    if scn.SPP_out and g_vars.midiout.is_port_open():
        # for restarting while playing in loop mode OR when not playing
        if ((new_frame != prev_frame + 1) and is_playing) or is_playing is False:
            pos_sec = scn.frame_current / scn.render.fps
            beats = (pos_sec / 60) * scn.tempo * 4  # in fact 16th not beat, hence the "4"
            p2 = int(beats / 128)
            p1 = beats % 128
            g_vars.midiout.send_message([242, p1, p2])
    prev_frame = new_frame

    # send midi events
    if g_vars.midiout.is_port_open():
        for bl_item, item in g_vars.addroutes_out:
            # getting current value
            if bl_item.is_str2eval:
                g_vars.evalprop(bl_item.str2eval, bl_item.withctx)
                prop = g_vars.eval_prop
                ref = g_vars.eval_ref
            else:
                ref = item['ref']
                prop = item['prop']

            try:
                if bl_item.is_array:
                    val = getattr(ref, prop)[bl_item.array]
                else:
                    val = getattr(ref, prop)

                # apply func
                func = item['func']
                val = func(bl_item, item, val)

                # testing rescale feature mode
                scale = item['rescale_bl']
                quant = item['quant']

                if bl_item.rescale_mode == 'Direct':
                    val2 = int(clamp(0, val, quant))

                if bl_item.rescale_mode == 'Auto':
                    val2 = rescale(val, 0, quant, scale)
                    val2 = int(clamp(0, val2, quant))

                elif bl_item.rescale_mode == "Cut":
                    if val < bl_item.rescale_outside_low or val > bl_item.rescale_outside_high:
                        return
                    else:
                        val2 = rescale(val, 0, quant, scale)
                        val2 = int(clamp(bl_item.rescale_outside_low, val2, bl_item.rescale_outside_high))

                elif bl_item.rescale_mode == 'Wrap':
                    val2 = rescale(val, 0, quant, scale)
                    val2 = int(clamp(bl_item.rescale_outside_low, val2, bl_item.rescale_outside_high))

                # the value has changed
                if val2 != item['val']:
                    item['val'] = val2

                    # simple 7bit parameter like pgm change and mono AT
                    if item['lenx'] == 1:
                        g_vars.midiout.send_message([item['midi'], val2])

                    # others 2 bytes msg
                    elif item['reg'] is None:
                        # for poly AT, cc7
                        if item['quant'] == 127:
                            g_vars.midiout.send_message([item['midi'], item['filter'], val2])
                        # for pitchbend
                        else:
                            LSB = val2 % 128
                            MSB = int(val2 / 128)
                            g_vars.midiout.send_message([item['midi'], LSB, MSB])

                    # for rpn/nrpn 7bit and 14bit
                    else:
                        # 7bit
                        if item['quant'] == 127:
                            for msg in item['reg']:
                                g_vars.midiout.send_message([item['midi'], msg[0], eval(msg[1])])

                        # 14bit msg
                        else:
                            LSB = val2 % 128
                            MSB = int(val2 / 128)
                            for msg in item['reg']:
                                g_vars.midiout.send_message([item['midi'], msg[0], eval(msg[1])])

                    if bpy.context.window_manager.addroutes_midi_debug is True:
                        bpy.ops.addroutes.debuginfo(msg="MIDI: Sending OK, route n°" + str(item["n"]) + ", category : " + bl_item.category + ", value: " + str(val2))

            except:
                if bpy.context.window_manager.addroutes_midi_debug is True:
                    bpy.ops.addroutes.debuginfo(msg="MIDI: Sending error, improper route n°" + str(item["n"]) + ', category :' + bl_item.category)


@persistent
def midifile_render(scn):
    global midifile_array

    if scn.mf_render:
        n_to_play = scn.frame_current - scn.mf_offset
        if (len(midifile_array) > n_to_play) and (n_to_play >= 0):
            for msg in midifile_array[scn.frame_current]:
                arr = decode(scn, msg)
                actualise(scn, arr)


@persistent
def addroutes_midi_on(scene):
    bpy.app.timers.register(get_ctx_scene, persistent=True)
    print("AddRoutes ON")


@persistent
def addroutes_midi_off(scene):
    bpy.app.timers.unregister(get_ctx_scene)
    print('AddRoutes OFF')


cls = (
    AddRoutes_Midifile_Convert,
    AddRoutes_Open_Midifile,
    AddRoutes_Midifile_Parse,
    AddRoutes_Midi_Play,
    AddRoutes_Midi_Pause,
    AddRoutes_Midi_Env,
  )


def register():
    bpy.types.WindowManager.n_overflow = bpy.props.IntProperty(description="Overflow events")
    bpy.types.Scene.sync = bpy.props.BoolProperty(name='Midi Clock in')
    bpy.types.Scene.SPP = bpy.props.BoolProperty(name='SPP in')
    bpy.types.Scene.midi_clock_out = bpy.props.BoolProperty(name='Midi Clock out', update=send_clock)
    bpy.types.Scene.SPP_out = bpy.props.BoolProperty(name='SPP out')
    bpy.types.Scene.tempo = bpy.props.FloatProperty(name='Tempo', default=120)
    bpy.types.Scene.midifile = bpy.props.StringProperty(name='Midifile', default='song.mid')
    bpy.types.Scene.mf_extraspoil = bpy.props.BoolProperty(
        name='Workaround to prevent note_on extrapolation during conversion', default=True)
    bpy.types.Scene.mf_offset = bpy.props.IntProperty(name='At frame', default=1,
                                                      description='At which frame convert/play/render the midifile')
    bpy.types.Scene.mf_render = bpy.props.BoolProperty(name='Contribute while rendering',
                                                       description='The midifile data are injected when rendering')
    bpy.types.Scene.mf_play = bpy.props.BoolProperty(name='Contribute while playing',
                                                     description='The midifile data are injected when playing (except the first 2 frames "eaten" by Blender !)')
    bpy.types.Scene.off_to_0 = bpy.props.BoolProperty(name='Copy notes off to null velocity notes on',
                                                      description='Note Off events are converted to null Note On')
    for c in cls:
        register_class(c)

    bpy.app.timers.register(actua_timer, persistent=True)
    bpy.app.handlers.frame_change_pre.append(midi_frame_upd)
    bpy.app.handlers.render_pre.append(midifile_render)
    bpy.app.handlers.load_pre.append(addroutes_midi_off)
    bpy.app.handlers.load_post.append(addroutes_midi_on)


def unregister():
    del bpy.types.WindowManager.n_overflow
    del bpy.types.Scene.off_to_0
    del bpy.types.Scene.mf_play
    del bpy.types.Scene.mf_render
    del bpy.types.Scene.mf_offset
    del bpy.types.Scene.mf_extraspoil
    del bpy.types.Scene.midifile
    del bpy.types.Scene.tempo
    del bpy.types.Scene.SPP_out
    del bpy.types.Scene.midi_clock_out
    del bpy.types.Scene.SPP
    del bpy.types.Scene.sync

    bpy.app.timers.unregister(actua_timer)
    bpy.app.handlers.frame_change_pre.remove(midi_frame_upd)
    bpy.app.handlers.load_post.remove(addroutes_midi_on)
    bpy.app.handlers.load_pre.remove(addroutes_midi_off)

    for c in cls:
        unregister_class(c)


if __name__ == "__main__":
    register()
