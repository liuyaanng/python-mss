#!/usr/bin/env python
# coding: utf-8
''' Helpers and base class of the MSS module. See __init__.py. '''

from __future__ import division, print_function, unicode_literals

from struct import pack
from sys import maxsize
from zlib import compress, crc32

__all__ = ['MSS', 'ScreenshotError', 'arch', 'mss']


class ScreenshotError(Exception):
    ''' Error handling class. '''


# C'est parti mon kiki !
class MSS(object):
    ''' This class will be overloaded by a system specific one. '''

    image = None

    def enum_display_monitors(self, screen=0):
        ''' Get positions of one or more monitors.

            If the monitor has rotation, you have to deal with it
            inside this method.

            Parameters:
             - screen - int - grab one screenshot of all monitors (screen=-1)
                              grab one screenshot by monitor (screen=0)
                              grab the screenshot of the monitor N (screen=N)

            Returns a dict:
            {
                'left':   the x-coordinate of the upper-left corner,
                'top':    the y-coordinate of the upper-left corner,
                'width':  the width,
                'height': the height
            }
        '''
        raise NotImplementedError('Subclasses need to implement this!')

    def get_pixels(self, monitor):
        ''' Retrieve screen pixels for a given monitor.

            `monitor` is a dict with:
            {
                'left':   the x-coordinate of the upper-left corner,
                'top':    the y-coordinate of the upper-left corner,
                'width':  the width,
                'heigth': the height
            }
        '''
        raise NotImplementedError('Subclasses need to implement this!')

    def save(self,
             output='screenshot-%d.png',
             screen=0,
             callback=lambda *x: True):
        ''' Grab a screenshot and save it to a file.

            Parameters:
             - output - string - the output filename. It can contain '%d' which
                                 will be replaced by the monitor number.
             - screen - int - grab one screenshot of all monitors (screen=-1)
                              grab one screenshot by monitor (screen=0)
                              grab the screenshot of the monitor N (screen=N)
             - callback - function - in case where output already exists, call
                                     the defined callback function with output
                                     as parameter. If it returns True, then
                                     continue; else ignores the monitor and
                                     switches to ne next.

            This is a generator which returns created files.
        '''

        # Monitors screen shots!
        for i, monitor in enumerate(self.enum_display_monitors(screen)):
            if screen <= 0 or (screen > 0 and i + 1 == screen):
                fname = output
                if '%d' in output:
                    fname = output.replace('%d', str(i + 1))
                callback(fname)
                self.to_png(data=self.get_pixels(monitor),
                            width=monitor[b'width'],
                            height=monitor[b'height'],
                            output=fname)
                yield fname

    def to_png(self, data, width, height, output):
        ''' Dump data to the image file.
            Pure python PNG implementation.
            http://inaps.org/journal/comment-fonctionne-le-png
        '''

        # pylint: disable=R0201, R0914

        b = pack
        line = (width * 3 + 3) & -4
        padding = 0 if line % 8 == 0 else (line % 8) // 2
        png_filter = b(b'>B', 0)
        scanlines = b''.join(
            [png_filter + data[y * line:y * line + line - padding]
             for y in range(height)])

        magic = b(b'>8B', 137, 80, 78, 71, 13, 10, 26, 10)

        # Header: size, marker, data, CRC32
        ihdr = [b'', b'IHDR', b'', b'']
        ihdr[2] = b(b'>2I5B', width, height, 8, 2, 0, 0, 0)
        ihdr[3] = b(b'>I', crc32(b''.join(ihdr[1:3])) & 0xffffffff)
        ihdr[0] = b(b'>I', len(ihdr[2]))

        # Data: size, marker, data, CRC32
        idat = [b'', b'IDAT', compress(scanlines), b'']
        idat[3] = b(b'>I', crc32(b''.join(idat[1:3])) & 0xffffffff)
        idat[0] = b(b'>I', len(idat[2]))

        # Footer: size, marker, None, CRC32
        iend = [b'', b'IEND', b'', b'']
        iend[3] = b(b'>I', crc32(iend[1]) & 0xffffffff)
        iend[0] = b(b'>I', len(iend[2]))

        with open(output, 'wb') as fileh:
            fileh.write(magic)
            fileh.write(b''.join(ihdr))
            fileh.write(b''.join(idat))
            fileh.write(b''.join(iend))
            return

        err = 'Error writing data to "{}".'.format(output)
        raise ScreenshotError(err)


def mss(*args, **kwargs):
    ''' Factory returning a proper MSS class instance.

        It detects the plateform we are running on
        and choose the most adapted mss_class to take
        screenshots.

        It then proxies its arguments to the class for
        instantiation.
    '''

    from platform import system

    operating_system = system().lower()
    if operating_system == 'darwin':
        from .darwin import MSSMac as mss_class
    elif operating_system == 'linux':
        from .linux import MSSLinux as mss_class
    elif operating_system == 'windows':
        from .windows import MSSWindows as mss_class
    else:
        err = 'System "{}" not implemented.'.format(operating_system)
        raise ScreenshotError(err)

    return mss_class(*args, **kwargs)


def arch():
    ''' Detect OS architecture.
        Returns an int: 32 or 64
    '''

    return 64 if maxsize > 2 ** 32 else 32
