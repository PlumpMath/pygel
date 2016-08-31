# -*- coding: utf-8 -*-

from gel import gel

import sys
import unittest
import time
import functools


class TimeoutError(IOError):
    pass


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


    def test_idle_call(self):
        A = 1
        B = 2
        C = 3
        @gel_main(self.reactor)
        def timer():

            @gel_quit(self.reactor)
            def callback(a, b, c):
                self.assertEqual(A, b)
                self.assertEqual(B, b)
                self.assertEqual(C, c)
            self.reactor.timeout_seconds_call(0.01, callback, A, B, c=C)

        timer()
