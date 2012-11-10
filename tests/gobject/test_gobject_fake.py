#-*- encoding: utf-8 -*-
import os
import sys
import unittest
sys.path.append("..")
sys.path.append('.')
import gel as gobject
import time

class TimeoutError(IOError):
    pass


def el_main(f):
    def wrap(*args, **kw):
        r = f(*args, **kw)
        def timeout_error():
            raise TimeoutError, 'callback took too long to execute'
        gobject.timeout_add_seconds(.2, timeout_error) 
        gobject.main()
        return r
    wrap.__name__ = f.__name__
    wrap.__doc__ = f.__doc__
    return wrap
    
def el_quit(f):
    def wrap(*args, **kw):
        r = f(*args, **kw)
        gobject.main_quit()
        return r
    wrap.__name__ = f.__name__
    wrap.__doc__ = f.__doc__
    return wrap

class GobjectFakeTestCase(unittest.TestCase):
    
    @el_main
    def test_timer(self):
        
        @el_quit
        def timer_callback(current_time):
            self.assertAlmostEqual(int(time.time() - 0.01), int(current_time))
        def callback_idle():
            gobject.timeout_add_seconds(0.01, timer_callback, time.time())
        
        gobject.idle_add(callback_idle)

    @el_main
    def test_timer_is_thread_safe(self):
        import thread 
        tid = thread.get_ident()
        
        @el_quit
        def timeout_callback():
            self.assertEqual(tid, thread.get_ident())
            
        def idle_callback():
            gobject.timeout_add(0, timeout_callback)
            
        gobject.idle_add(idle_callback)
        
        
    def _test_idle(self):
        self.called = []
        import threading, thread
        self.tid = thread.get_ident()

        def idle_callback_0(called):
            self.called = True
            gobject.main_quit()
        
        gobject.idle_add(idle_callback_0)
        gobject.main()
        self.assertTrue(called)
    
    def _test_io_add_watch(self):
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
            if all(can_out):
                gobject.main_quit()
            return True
        
        import socket  
        import random
        
        while 1:
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
    def test_source_remove(self):
        def timeout_callback():
            pass 
        
        source = gobject.timeout_add_seconds(0.01, timeout_callback)
        @el_quit
        def idle_callback_1():
            self.assertIn(source, gobject._handlers.keys())
            gobject.source_remove(source)
            self.assertNotIn(source, gobject._handlers.keys())
            
        gobject.idle_add(idle_callback_1)
        
       
    def test_get_current_time(self):
        self.assertAlmostEqual(int(time.time()), int(gobject.get_current_time()), places=2)