from __future__ import print_function, absolute_import, division

import os
import struct
import fcntl
import termios
import time
import ctypes

import six

import logging

logger = logging.getLogger('gel.inotify')


"""
--CONSTANTS--

IN_ACCESS                   : file was accessed.

IN_MODIFY = 2               : file was modified.

IN_ATTRIB = 4               : metadata changed.

IN_WRITE = 8                : writtable file was closed.

IN_CLOSE = 0x10             : unwrittable file was closed.

IN_OPEN = 0x20              : file was oppened.

IN_MOVED_FROM = 0x40        : file/dir in a watched dir was moved from X.
                              can trace the full move of an item when
                              IN_MOVED_TO is available too, in this case if the
                              moved item is itself watched, its path will be
                              updated (see IN_MOVE_SELF).

IN_MOVED_TO = 0x80          : file/dir was moved to Y in a watched DIR (see
                              IN_MOVE_FROM).

IN_CREATE = 0x100           : file/dir was created in watched directory.

IN_DELETE = 0x200           : file/dir was deleted in watched directory.

IN_DELETE_SELF = 0x400      : watched item itself was deleted.

IN_MOVE_SELF = 0x800        : watched item itself was moved, currentily its full
                              pathname destination can only be traced if its
                              source directory and destination directory are
                              both watched. Otherwise, the file is still being
                              watched but you cannot rely anymore on the given
                              path.

IN_UNMOUNT = 0x2000         : backing fs was unmounted. Notified to all watches
                              located on this fs.

IN_Q_OVERFLOW = 0x4000      : event queued overfloed. This event doesn't belongs
                              to any particular watch.

IN_IGNORED = 0x8000         : raised on watched item removing. Probably uselless
                              for you, prefer instead IN_DELETE*

IN_ONLYDIR = 0x1000000      : only watch the path if is a directory (lk 2.6.15).
                              Usable when calling .add_watch.

IN_DONT_FOLLOW = 0x2000000  : don't follow symlink (lk 2.6.15).

IN_MASK_ADD = 0x20000000    : to update a mak without overwriting the previous
                              value (lk 2.6.14). Useful when updating a watch.

IN_ISDIR = 0x40000000       : event occurred against directory. It is always
                              piggybacked to an event. you better not use that

IN_ONESHOT = 0x80000000     : unregister automatically the watch after the first
                              event.

"""


IN_ACCESS = 1               # file was accessed.
IN_MODIFY = 2               # file was modified
IN_ATTRIB = 4               # metadata changed.
IN_WRITE = 8                # writtable file was closed.
IN_CLOSE = 0x10             # unwrittable file was closed.
IN_OPEN = 0x20              # file was oppened.
IN_MOVED_FROM = 0x40        # file/dir in a watched dir was moved from X.
                            # can trace the full move of an item when
                            # IN_MOVED_TO is available too, in this case if the
                            # moved item is itself watched, its path will be
                            # updated (see IN_MOVE_SELF).
IN_MOVED_TO = 0x80          # file/dir was moved to Y in a watched DIR (see
                            # IN_MOVE_FROM).
IN_CREATE = 0x100           # file/dir was created in watched directory
IN_DELETE = 0x200           # file/dir was deleted in watched directory
IN_DELETE_SELF = 0x400      # watched item itself was deleted.
IN_MOVE_SELF = 0x800        # watched item itself was moved, currentily its full
                            # pathname destination can only be traced if its
                            # source directory and destination directory are
                            # both watched. Otherwise, the file is still being
                            # watched but you cannot rely anymore on the given
                            # path.
IN_UNMOUNT = 0x2000         # backing fs was unmounted. Notified to all watches
                            # located on this fs.
IN_Q_OVERFLOW = 0x4000      # event queued overfloed. This event doesn't belongs
                            # to any particular watch.
IN_IGNORED = 0x8000         # raised on watched item removing. Probably uselless
                            # for you, prefer instead IN_DELETE*
IN_ONLYDIR = 0x1000000      # only watch the path if is a directory (lk 2.6.15).
                            # Usable when calling .add_watch.
IN_DONT_FOLLOW = 0x2000000  # don't follow symlink (lk 2.6.15).
IN_MASK_ADD = 0x20000000    # to update a mak without overwriting the previous
                            # value (lk 2.6.14). Useful when updating a watch.
IN_ISDIR = 0x40000000       # event occurred against directory. It is always
                            # piggybacked to an event. better not use that.
IN_ONESHOT = 0x80000000     # unregister automatically the watch after the first
                            # event


libc = ctypes.cdll.LoadLibrary('')

def geterr(): return libc.__errno_location()

last_error = libc.strerror
last_error.restype = ctypes.c_char_p



def binary_type(string):
    if six.PY2:
        return string
    else:
        # TODO: is some downcases nowadays?
        # assumes linux is always using utf-8
        return bytes(string, "utf-8")


class Inotify(object):

    def __init__(self):
        self.libc = libc
        self.fd = libc.inotify_init()
        if self.fd == -1:
            raise OSError(last_error())

    def fileno(self):
        return self.fd

    def read(self, timeout=None):
        size_int = ctypes.c_int()
        count = 0
        while fcntl.ioctl(self.fd, termios.FIONREAD, size_int)==-1:
            time.sleep(1)
            if timeout:
                count+=1
                if count > timeout:
                    yield ()
                    return

        size = size_int.value
        data = os.read(self.fd, size)
        deb = 0
        while deb < size:
            fin = deb+16
            wd, mask, cookie, name_len = struct.unpack(b'iIII', data[deb:fin])
            deb, fin = fin, fin+name_len
            name = struct.unpack(b'%ds' % name_len, data[deb:fin])[0].rstrip(b'\0').decode('utf-8')
            deb = fin
            yield wd, mask, cookie, name

    def add_watch(self, path, mask):
        """
        add a path to watch,
        path may be relative,
        and the mask is one of the constants starting with IN
        """
        path = binary_type(os.path.abspath(path))
        wd = self.libc.inotify_add_watch(self.fd, path, mask)
        if wd == -1:
            logger.warning("ADD error: %s", last_error())
        return wd

    def rm_watch(self, wd):
        ret = self.libc.inotify_rm_watch(self.fd, wd)
        if ret == -1:
            logger.warning("remove error %s", last_error())

    def close(self):
        os.close(self.fd)

    def __del__(self):
        try:
            self.close()
        except:
            pass

## used to test if the platform supports inotify
inotify = Inotify()
inotify.close()
del inotify
