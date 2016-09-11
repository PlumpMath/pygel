
from __future__ import print_function, division, absolute_import

import sys
import os

assert 'linux' in sys.platform


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
IN_ACCESS = 1
IN_MODIFY = 2
IN_ATTRIB = 4
IN_WRITE = 8
IN_CLOSE = 0x10
IN_OPEN = 0x20
IN_MOVED_FROM = 0x40
IN_MOVED_TO = 0x80
IN_CREATE = 0x100
IN_DELETE = 0x200
IN_DELETE_SELF = 0x400
IN_MOVE_SELF = 0x800
IN_UNMOUNT = 0x2000
IN_Q_OVERFLOW = 0x4000
IN_IGNORED = 0x8000
IN_ONLYDIR = 0x1000000
IN_DONT_FOLLOW = 0x2000000
IN_MASK_ADD = 0x20000000
IN_ISDIR = 0x40000000
IN_ONESHOT = 0x80000000

try:
    #trying to use ctypes version
    from . import inotify
    #using this shit to force eclipse pydev to stop complaing!
    del inotify
    from .inotify import Inotify
except Exception as e:
    print(e, type(e))
    #not available, using pyinotify
    import pyinotify


    class Inotify(object):

        def __init__(self):
            self._wm = pyinotify.WatchManager()

        def add_watch(self, path, mask):
            return self._wm.add_watch(path, mask).keys()[0]

        def rm_watch(self, wd):
            return self._wm.rm_watch(wd)

        def close(self):
            return self._wm.close()

        def read(self):
            notifier = pyinotify.Notifier(self._wm)
            while notifier.check_events(0):
                e = notifier.check_events()
                notifier.read_events()
                yield (e, None, None, None)
            return


        def __del__(self):
            try:
                self.close()
            except:
                pass

class FileError(Exception):
    pass

class FileWatchError(Exception):
    pass

from gel import Gel
from gel.constants import IO_IN, IO_OUT
import types

class FileWatch(object):

    def __init__(self, reactor=None):
        self.reactor = reactor
        if reactor is None:
            self.reactor = Gel()
        self._notify = Inotify()
        self.watching = {}
        self.watching_wd = {}
        self.watching_file = {}
        monitor = IO_IN | IO_OUT
        self.reactor.register_io(self._notify, self._callback, monitor)

    def _callback(self, *args):
        for i in self._notify.read():
            wd, _, _, _ = i
            try:
                #TODO ADD a way to return the file modified, created or etc if the observing is a directory
                path, mask = self.watching_file[wd]
                cb = self.watching_wd[wd]
                cb(path)
                return True

            except Exception as e:
                #raise
                pass
            try:
                self.watching_wd[wd](wd)
            except:
                pass
        return True

    def watch_file(self, path, callback, mask=IN_MODIFY | IN_DELETE_SELF |
                                    IN_MOVE_SELF | IN_MASK_ADD | IN_ATTRIB):
        if not callable(callback):
            raise TypeError("callback must be a function.")

        if not os.path.exists(path):
            raise FileError("the path '%s' doesn't exists." % path)

        if os.path.isdir(path):
            raise FileError("the path '%s' is a directory." % path)
        if path in self.watching:
            self.remove_watch(path)
        wd = self._notify.add_watch(path, mask)
        self.watching[path] = wd
        self.watching_wd[wd] = callback
        self.watching_file[wd] = (path, mask)

    def watch_directory(self, path, callback, mask=IN_CREATE | IN_DELETE |
                                    IN_WRITE |IN_MOVED_FROM |
                                    IN_MOVED_TO | IN_MOVE_SELF):
        if not os.path.isdir(path):
            raise FileError(("the path '%s' doesn't exists"
                             " or is not a directory") % path)
        if not callable(callback):
            raise TypeError("callback must be a function.")

        if path in self.watching:
            self.remove_watch(path)

        wd = self._notify.add_watch(path, mask)
        self.watching[path] = wd
        self.watching_wd[wd] = callback
        self.watching_file[wd] = (path, mask)

    def remove_watch(self, path):
        try:
            wd = self.watching[path]
            self._notify.rm_watch(wd)
            del self.watching[path]
            del self.watching_wd[wd]
        except:
            raise FileWatchError("not watching path %s" % path)

