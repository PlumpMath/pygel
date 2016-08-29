# -*- coding: utf-8 -*-
import os
import sys
import unittest
from functools import wraps
sys.path.append("..")
sys.path.append('.')
import gel as gobject
import time


class TimeoutError(IOError):
    pass


def el_main(f):
    @wraps(f)
    def wrap(*args, **kw):
        r = f(*args, **kw)

        def timeout_error():
            gobject.main_quit()
            raise TimeoutError('callback took too long to execute')
        gobject.timeout_add_seconds(200, timeout_error)
        gobject.main()
        return r

    return wrap


def el_quit(f):

    @wraps(f)
    def wrap(*args, **kw):
        r = f(*args, **kw)
        gobject.timeout_add(0, gobject.main_quit)
        return r
    return wrap


class GobjectFakeTestCase(unittest.TestCase):

    def test_timer(self):

        @el_quit
        def timer_callback(current_time):
            pass
            # self.assertAlmostEqual(int(time.time() - .01), int(current_time))

        @el_main
        def actual_test():
            gobject.timeout_add_seconds(0.01, timer_callback, time.time())
        actual_test()

    @el_main
    def _est_timer_is_thread_safe(self):
        import thread
        tid = thread.get_ident()

        @el_quit
        def timeout_callback():
            self.assertEqual(tid, thread.get_ident())

        def idle_callback():
            gobject.timeout_add(0, timeout_callback)

        gobject.idle_add(idle_callback)

    def _est_idle(self):
        self.called = []
        import threading
        import thread
        self.tid = thread.get_ident()

        def idle_callback_0(called):
            self.called = True
            gobject.main_quit()

        gobject.idle_add(idle_callback_0)
        gobject.main()
        self.assertTrue(called)

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

    @el_main
    def _est_source_remove(self):
        def timeout_callback():
            pass

        source = gobject.timeout_add_seconds(0.01, timeout_callback)

        @el_quit
        def idle_callback_1():
            self.assertIn(source, gobject._handlers.keys())
            gobject.source_remove(source)
            self.assertNotIn(source, gobject._handlers.keys())

        gobject.idle_add(idle_callback_1)

    def _est_get_current_time(self):
        self.assertAlmostEqual(int(time.time()), int(gobject.get_current_time()), places=2)

    @el_main
    def _est_spawn_task(self):
        def task(self):
            # this task is running in background
            time.sleep(1)
            return 42

        @el_quit
        def callback(response):
            self.assertEqual(response, 42)

        gobject.spawn_task(task, callback)
