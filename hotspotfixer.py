#!/usr/bin/python
import inspect
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf
import os
import sys
import numpy as np

def main():
    # print command line arguments
    for arg in sys.argv[1:]:
        cursor = ReadXCursor(arg)
        WriteXCursor(cursor[0], cursor[1], cursor[2], cursor[3], arg + "xcur.out")
        # print(cursor[0])
        # print(cursor[1])
        # print(cursor[2])
        # print(cursor[3])
    # window = Gtk.Window(title="Hello World")
    # window.show()
    # window.connect("destroy", Gtk.main_quit)
    # Gtk.main()

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
            print(line_num)
            print(type())
            pixels = pixlist[i].get_pixels_np.array()
            width = pixlist[i].get_width()
            height = pixlist[i].get_height()
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
    main()

# Debugging function
def line_num(onlyLineNum=False):
    if(onlyLineNum):
        return "line: " + str(inspect.currentframe().f_back.f_lineno)
    return "function: " \
           + inspect.currentframe().f_back.f_code.co_name \
           + ", line: " \
           + str(inspect.currentframe().f_back.f_lineno)