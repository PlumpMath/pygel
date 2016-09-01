# -*- coding: utf-8 -*-

import six
import os
import sys
import unittest
from functools import wraps
import gel as gobject
import time


class TimeoutError(IOError):
    pass

def gel_main(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        def timeout_error():
            gobject.main_quit()
            raise TimeoutError("callback took to long to execute")

        gobject.timeout_add_seconds(2, timeout_error)
        r = f(*args, **kwargs)
        gobject.main()
    return decorated


def gel_quit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        r = f(*args, **kwargs)
        gobject.main_quit()
        return r

    return decorated



class GobjectFakeTestCase(unittest.TestCase):

    def test_timer(self):

        @gel_quit
        def timer_callback(current_time):
            pass
            # self.assertAlmostEqual(int(time.time() - .01), int(current_time))

        @gel_main
        def actual_test():
            gobject.timeout_add_seconds(0.01, timer_callback, time.time())
        actual_test()

    @gel_main
    def test_timer_is_thread_safe(self):
        thread = six.moves._thread
        tid = thread.get_ident()

        @gel_quit
        def timeout_callback():
            self.assertEqual(tid, thread.get_ident())

        def idle_callback():
            gobject.timeout_add(0, timeout_callback)

        gobject.idle_add(idle_callback)

    def test_idle(self):

        A = 1

        @gel_quit
        def idle(a):
            self.assertTrue(a, A)
            self.assertFalse(True)

        @gel_main
        def actual_test():
            gobject.idle_add(callback)

    def _est_io_add_watch(self):
        can_out = [False, False]
        socket_client = socket.socket()
        socket_server = socket.socket()

        def io_add_watch_callback_in(source, condition):
            self.assertIs(source.__class__, socket)
            self.assertEqual(condition, gobject.IO_IN)
            socket_server.accept()
            can_out[0] = True

        def io_add_watch_callback_out(source, condition):
            self.assertIs(source.__class__, socket)
            self.assertEqual(condition, gobject.IO_OUT)
            can_out[1] = True

        def idle_callback_2():
            import ipdb
            ipdb.set_trace()
            if all(can_out):
                gobject.main_quit()
            return True

        import socket
        import random

        while True:
            port = random.randint(1024, 65535)
            try:
                socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                socket_server.bind(('127.0.0.1', port))
                socket_server.listen(1)
            except Warning:
                pass

        gobject.io_add_watch(socket_server, gobject.IO_IN, io_add_watch_callback_in)
        gobject.io_add_watch(socket_client, gobject.IO_OUT, io_add_watch_callback_out)
        gobject.idle_add(idle_callback_2)
        gobject.main()
        self.assertTrue(all(can_out))

    @gel_main
    def test_source_remove(self):
        def timeout_callback():
            pass

        source = gobject.timeout_add_seconds(0.01, timeout_callback)

        @gel_quit
        def idle_callback_1():
            gobject.source_remove(source)

        gobject.idle_add(idle_callback_1)

    def test_get_current_time(self):
        self.assertAlmostEqual(int(time.time()), int(gobject.get_current_time()), places=2)

