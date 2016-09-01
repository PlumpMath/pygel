# -*- coding: utf-8 -*-

from gel import gel

import sys
import unittest
import time
import functools


class TimeoutError(AssertionError):
    pass


def port_generator_helper():
    i = 1025
    while True:
        yield i
        i += 1
        if i > 65534:
            i = 1024


def gel_main(reactor):
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):

            def timeout_error():
                reactor.main_quit()
                raise TimeoutError("callback took to long to execute")

            reactor.timeout_seconds_call(2, timeout_error)
            r = f(*args, **kwargs)
            reactor.main()
        return decorated
    return decorator

def gel_quit(reactor):
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            r = f(*args, **kwargs)
            reactor.main_quit()
            return r

        return decorated
    return decorator


class GelTestCase(unittest.TestCase):

    def setUp(self):
        self.reactor = gel.Gel()

    def test_timeout_call(self):
        A = 1
        B = 2
        C = 3
        @gel_main(self.reactor)
        def timer():
            run_time = time.time()

            @gel_quit(self.reactor)
            def callback(a, b, c):
                cb_time = time.time()
                self.assertEqual(A, a)
                self.assertEqual(B, b)
                self.assertEqual(C, c)
                # check if the timer was dispared between 1 and 2 seconds
                # as we can't really tell if the time will be triggered exactly on time
                self.assertGreaterEqual(cb_time + .1, run_time)
                self.assertLessEqual(run_time, cb_time + 2)
            self.reactor.timeout_seconds_call(.1, callback, A, B, c=C)

        timer()

    def test_idle_call(self):

        A = 1
        B = 2
        C = 3
        @gel_main(self.reactor)
        def call_later():

            @gel_quit(self.reactor)
            def callback(a, b, c):
                self.assertEqual(A, a)
                self.assertEqual(B, b)
                self.assertEqual(C, c)
            self.reactor.idle_call(callback, A, B, c=C)

        call_later()


    def test_socket_accept(self):

        @gel_main(self.reactor)
        def actual_test():
            import socket
            port_generator = port_generator_helper()
            while True:
                s = socket.socket()
                try:
                    s.bind(("127.0.0.1", port_generator.next()))
                except socket.error:
                    continue
                s.listen(1)
                break


            @gel_quit(self.reactor)
            def callback(event):
                socket, addr = event.accept()
                self.assertIs(event, s)

            self.reactor.register_io(s, callback)
            client = socket.socket()
            client.connect(s.getsockname())

        actual_test()
