#!/usr/bin/python
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gio, Gtk, GdkPixbuf
import inspect
import numpy as np
import os
import sys
import time
import threading

# Debugging function
def line_num(onlyLineNum=False):
    if(onlyLineNum):
        return "line: " + str(inspect.currentframe().f_back.f_lineno)
    return "function: " \
           + inspect.currentframe().f_back.f_code.co_name \
           + ", line: " \
           + str(inspect.currentframe().f_back.f_lineno)

class HotspotFixApp(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        max_action = Gio.SimpleAction.new_stateful("maximize",
                                                    None,
                                                    GLib.Variant.new_boolean(False))
        max_action.connect("change-state", self.on_maximize_toggle)
        self.add_action(max_action)
        self.connect("notify::is-maximized",
                      lambda obj, pspec: max_action.set_state(
                          GLib.Variant.new_boolean(obj.props.is_maximized)
                      ))
    def on_maximize_toggle(self, action, value):
        action.set_state(value)
        if value.get_boolean():
            self.maximize()
        else:
            self.unmaximize()

class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="noidea.what.to.do",
                          flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                          **kwargs)
        self.window = None
        self.add_main_option("test", ord("t"), GLib.OptionFlags.NONE,
                              GLib.OptionArg.NONE, "Command line test", None)
        self.add_main_option("file", ord("f"), GLib.OptionFlags.NONE,
                              GLib.OptionArg.NONE, "Command line test", None)
    def do_startup(self):
        Gtk.Application.do_startup(self)
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)
        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)
        builder = Gtk.Builder.new_from_file("menu.xml")
        self.set_app_menu(builder.get_object("app-menu"))
    def do_activate(self):
        if not self.window:
            self.window = HotspotFixApp(application=self, default_width=700, default_height=700,  title="Main Window")
        self.window.present()
    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        options = options.end().unpack()
        if "test" in options:
            print("Test argument recieved: %s" % options["test"])
        if "file" in options:
            self.cursor = ReadXCursor(arg)
            if cursor == False:
                print("Error with file: ", arg)
                return
        self.activate()
        return 0
    def on_about(self, action, param):
        about_dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about_dialog.present()
    def on_quit(self, action, param):
        self.quit()

def hide():
    # print command line arguments
    arg = sys.argv[1]
    cursor = ReadXCursor(arg)
    if cursor == False:
        print("Error with file: ", arg)
        return
    window = Gtk.Window(default_width=700, default_height=700, title="Edit the hotspot for: " + arg)
    window.connect("destroy", Gtk.main_quit)
    cursor_pb = cursor[3][0]
    cpb_w = cursor_pb.get_width()
    cpb_h = cursor_pb.get_height()
    scale = max(max(cpb_w, cpb_h), 700)/min(max(cpb_w, cpb_h), 700)
    cursor_img = Gtk.Image(pixbuf=(cursor_pb.scale_simple(cpb_w * scale, cpb_h * scale, GdkPixbuf.InterpType.NEAREST)))
    vbox = Gtk.VBox()

    vbox.pack_start(cursor_img, False, False, 0)
    window.add(vbox)
    window.show_all()

    Gtk.main()

def ReadXCursor(filename):
    try:
        imagefile = open(filename, 'r+b')
    except IOError:
        return False

    # the first 4 bytes of an xcursor imagefile is always Xcur
    magic = imagefile.read(4)
    if magic != b'Xcur':
        return False

    header = np.frombuffer(imagefile.read(4), dtype=np.int32)
    version = imagefile.read(4)
    ntoc = np.frombuffer(imagefile.read(4), dtype=np.int32)

    ftype = []
    size = []
    position = []

    # TODO cleanup
    for i in np.arange(ntoc[0]):
        ftype.append(imagefile.read(4))
        size.append(np.frombuffer(imagefile.read(4), dtype=np.int32))
        postionCounter = np.frombuffer(imagefile.read(4), dtype=np.int32)
        position.append(postionCounter[0])  # we only need the values

    width = []
    height = []
    delay = []
    pixels = []

    for i in np.arange(ntoc):
        imagefile.seek(position[i])
        header = np.frombuffer(imagefile.read(4), dtype=np.int32)
        ctype = imagefile.read(4)
        csubtype = np.frombuffer(imagefile.read(4), dtype=np.int32)
        if ctype != ftype[i] or csubtype != size[i]:
            imagefile.close()
            return False
        if np.frombuffer(ctype, dtype=np.int32) == -131071:
            pass  # it's a comment
        elif np.frombuffer(ctype, dtype=np.int32) == -196606:
            version = np.frombuffer(imagefile.read(4), dtype=np.int32)
            width.append(int(np.frombuffer(imagefile.read(4), dtype=np.int32)))
            height.append(int(np.frombuffer(imagefile.read(4), dtype=np.int32)))
            xhot = int(np.frombuffer(imagefile.read(4), dtype=np.int32))
            yhot = int(np.frombuffer(imagefile.read(4), dtype=np.int32))
            delay.append(int(np.frombuffer(imagefile.read(4), dtype=np.int32)))
            # images are represented in ARGB, byteswapped format.
            # That is, each word contains in order B, G, R, A
            # pixbufs need RGBA representation
            p = np.swapaxes(np.reshape(np.frombuffer(imagefile.read(4 * height[-1] * width[-1]), 'b'),
                                                    (width[-1] * height[-1], 4)), 0, 1)

            pixels.append(np.swapaxes(np.array([p[2], p[1], p[0], p[3]], 'b'),
                                      0, 1
                                      ).tostring())

    imagefile.close()

    pics = []
    for i in np.arange(ntoc):
        try:
            pics.append(GdkPixbuf.Pixbuf.new_from_data(pixels[i],
                                                     GdkPixbuf.Colorspace.RGB,
                                                     True, 8, width[i],
                                                     height[i], width[i] * 4))
        except Exception as e:
            pics.append(None)

    return [xhot, yhot, delay, pics]

def array_from_pixbuf(p):
    " convert from GdkPixbuf to numpy array"
    w,h,c,r=(p.get_width(), p.get_height(), p.get_n_channels(), p.get_rowstride())
    assert p.get_colorspace() == GdkPixbuf.Colorspace.RGB
    assert p.get_bits_per_sample() == 8
    if  p.get_has_alpha():
        assert c == 4
    else:
        assert c == 3
    assert r >= w * c
    a=np.frombuffer(p.get_pixels(),dtype=np.uint8)
    if a.shape[0] == w*c*h:
        return a.reshape( (h, w, c) )
    else:
        b=np.zeros((h,w*c),'uint8')
        for j in range(h):
            b[j,:]=a[r*j:r*j+w*c]
        return b.reshape( (h, w, c) )

def WriteXCursor(xhot, yhot, delaylist, pixlist, filename):
    ntoc = len(pixlist)
    file = open(filename, 'w+b')
    file.write(b'Xcur')
    file.write(np.array(16).tostring())  # Header byte length
    file.write(np.array(65536).tostring())  # Version
    file.write(np.array(ntoc).tostring())
    position = 16 + ntoc * 12
    for i in np.arange(ntoc):
        file.write(np.array(0x0200fdff).byteswap().tostring())  # Type
        if type(pixlist[i]) == GdkPixbuf.Pixbuf:
            width = pixlist[i].get_width()
            height = pixlist[i].get_height()
            file.write(np.array(max([width, height])).tostring())  # Subtype
            file.write(np.array(position).tostring())
            position = position + width * height * 4 + 36  # Image weight + image header
        else:
            file.write(np.array(0).tostring())  # Subtype
            file.write(np.array(position).tostring())
            position = position + 36

    for i in np.arange(ntoc):
        file.write(np.array(36).tostring())  # Header byte length
        file.write(np.array(0x0200fdff).byteswap().tostring())  # Type

        if type(pixlist[i]) == GdkPixbuf.Pixbuf:
            # partly taken from https://stackoverflow.com/questions/39936737/how-to-turn-gdk-pixbuf-object-into-numpy-array/41714464#41714464
            width = pixlist[i].get_width()
            height = pixlist[i].get_height()
            channels = pixlist[i].get_n_channels()
            rowstride = pixlist[i].get_rowstride()
            pixels = np.frombuffer(pixlist[i].get_pixels(), dtype=np.uint8)
            if(pixels.shape[0] == width * height * channels):
                pixels = pixels.reshape( (height, width, channels))
            else:
                temp_pixels = np.zeros((height, width, channels), 'uint8')
                for j in range(height):
                    temp_pixels[j, :] = pixels[rowstride * j: rowstride * j + width * channels]
                pixels = temp_pixels.reshape((height, width, channels))
            # width = pixlist[i].get_width()
            # height = pixlist[i].get_height()
            file.write(np.array(max([width, height])).tostring())  # Subtype
            file.write(np.array(1).tostring())  # Version
            file.write(np.array(width).tostring())
            file.write(np.array(height).tostring())
            file.write(np.array(xhot).tostring())
            file.write(np.array(yhot).tostring())
            file.write(np.array(delaylist[i]).tostring())

            # converts from RGBA to ARGB byteswapped
            pixels = np.swapaxes(pixels, 0, 2)
            pixels = np.array([pixels[2, :],
                               pixels[1, :],
                               pixels[0, :],
                               pixels[3, :]], 'b')
            pixels = np.swapaxes(pixels, 0, 2)
            file.write(pixels.tostring())
        else:
            file.write(np.array(0).tostring())  # Subtype (size)
            file.write(np.array(1).tostring())  # Version
            file.write(np.array(0).tostring())  # Width
            file.write(np.array(0).tostring())  # Height
            file.write(np.array(0).tostring())  # xhot
            file.write(np.array(0).tostring())  # yhot
            file.write(np.array(0).tostring())  # delay

    file.close()
    return True

if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)