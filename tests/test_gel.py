# -*- coding: utf-8 -*-

from gel import Gel, GelFactoryError

import socket
import six
import sys
import unittest
import time
import functools


# we're not making any tests on qt4 because using pyqt4 and pyqt5 in the same process will lead to failiures
# but the low level api for the reactor not changed at all in qt4 and qt5, so we expect qt4 should work as well qt5


class TimeoutError(AssertionError):
    pass


def port_generator_helper():
    i = 1025
    while True:
        yield i
        i += 1
        if i > 65534:
            i = 1024


GEL_TIMEOUT = 2000.0 # Seconds


def gel_main(reactor):
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):

            st = time.time()
            def timeout_error():
                print(time.time() - st)
                reactor.main_quit()
                raise TimeoutError("callback took to long to execute")

            reactor.timeout_seconds_call(GEL_TIMEOUT, timeout_error)
            reactor.idle_call(f, *args, **kwargs)
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
        self.reactor = Gel()

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
                    s.bind(("127.0.0.1", six.next(port_generator)))
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

    def test_main_iteration_with_block_false_should_return_True_with_no_events(self):
        self.assertTrue(self.reactor.main_iteration(block=False))

    def test_sleep(self):
        start = time.time()
        self.reactor.sleep(200)
        current = time.time()
        # assure that the sleep time is almost the sleep we asked for
        wait_time = current - start
        self.assertLessEqual(wait_time, .220)
        self.assertGreaterEqual(wait_time, .190)

    def test_wait_task(self):

        def threaded_task(a, b):
            return a * b

        ret = self.reactor.wait_task(threaded_task, 3, 4)
        self.assertEqual(ret, 3 * 4)

    def test_wait_task_throwns_an_exception_inside_thread_should_raises_that_exception_in_the_current_execution_flow(self):
        def threaded_task():
            return 0/0
        self.assertRaises(ZeroDivisionError, self.reactor.wait_task, threaded_task)

    def test_threaded_wrapper(self):

        @self.reactor.threaded_wrapper
        def threaded_task():
            time.sleep(0.1)
            return 10

        self.assertEqual(10, threaded_task())

    def test_selector(self):

        @gel_main(self.reactor)
        def actual_test():

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            s.sendto(b"", ("", 1))
            _, port = s.getsockname()

            def timeout():
                s.sendto(b"\x00", s.getsockname())

            self.reactor.timeout_seconds_call(0.1, timeout)
            response = self.reactor.selector([s])

            self.assertEqual(s, response)
            self.assertEqual(s.recvfrom(1), (b'\x00', ('127.0.0.1', s.getsockname()[1])))
            self.reactor.main_quit()

        actual_test()

    def test_selector_with_timeout_timed_out(self):
        @gel_main(self.reactor)
        def actual_test():

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(b"", ("", 1))
            _, port = s.getsockname()

            def timeout():
                s.sendto(b"\x00", s.getsockname())

            self.reactor.timeout_seconds_call(0.3, timeout)
            response = self.reactor.selector([s], 0.1)

            self.assertIsNone(response)
            self.reactor.main_quit()

        actual_test()

    def test_selector_with_timeout(self):
        @gel_main(self.reactor)
        def actual_test():

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            s.sendto(b"", ("", 1))
            _, port = s.getsockname()

            def timeout():
                s.sendto(b"\x00", s.getsockname())

            self.reactor.timeout_seconds_call(0.01, timeout)
            response = self.reactor.selector([s], 0.2)

            self.assertEqual(s, response)
            self.assertEqual(s.recvfrom(1), (b'\x00', ('127.0.0.1', s.getsockname()[1])))
            self.reactor.main_quit()

        actual_test()



class TestGelFactory(unittest.TestCase):

    def test_non_available_reactor_should_fail(self):
        self.assertRaises(GelFactoryError, Gel.from_reactor, ('cocoa'))

    def test_factory_with_no_arguments_should_use_gel_reactor(self):
        from gel.reactor.gel_reactor import GelReactor
        gel = Gel.from_reactor()
        self.assertIsInstance(gel._reactor, GelReactor)

    def test_factory_use_qt5_reactor(self):
        from gel.reactor.qt5_reactor import Qt5Reactor
        from PyQt5.QtCore import QCoreApplication

        # we need an qt application in orther to use a qt reactor
        app = QCoreApplication(sys.argv)

        gel = Gel.from_reactor(event_loop='qt5')
        self.assertIsInstance(gel._reactor, Qt5Reactor)

        gel = Gel.from_reactor(event_loop='pyqt5')
        self.assertIsInstance(gel._reactor, Qt5Reactor)

        gel = Gel.from_reactor(event_loop='qt')
        self.assertIsInstance(gel._reactor, Qt5Reactor)

