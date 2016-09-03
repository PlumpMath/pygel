# -*- coding: utf-8 -*-

import os
import sys
import unittest

import functools
from gel.event_lib import inotify
import shutil
from gel.event_lib import file_monitor_linux

from gel import Gel


directory = 'file_monitor_testing'


class TimeoutError(AssertionError):
    pass


def gel_main(reactor):
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):

            def timeout_error():
                reactor.main_quit()
                # raise TimeoutError("callback took to long to execute")

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



class EventLibFileMonitorLinuxTestCase(unittest.TestCase):

    def setUp(self):
        try:
            self.tearDown()
        except:
            pass
        os.mkdir(directory)
        self.reactor = Gel()
        self.file_watch = file_monitor_linux.FileWatch(self.reactor)

    def tearDown(self):
        shutil.rmtree(directory)
        del self.file_watch

    def test_file_watcher(self):
        path = '%s/file_test' % directory

        @gel_quit(self.reactor)
        def callback(apath):
            self.assertEqual(apath, path)

        @gel_main(self.reactor)
        def actual_test():
            with open(path, "w") as w:
                w.write("hi")

            self.file_watch.watch_file(path, callback)
            with open(path, 'a') as w:
                w.write('olá')

        actual_test()

    def test_create_file_watcher_directory(self):
        def callback(path):
            return
        self.file_watch.watch_directory(directory, callback)
        self.assertEqual(list(self.file_watch.watching.keys())[0], directory)
        self.assertEqual(self.file_watch.watching_wd[self.file_watch.watching[directory]], callback)

    def test_directory_watcher(self):

        @gel_quit(self.reactor)
        def callback(apath):
            self.assertEqual(apath, directory)

        @gel_main(self.reactor)
        def actual_test():
            self.file_watch.watch_directory(directory, callback)

            with open('%s/file_%d' % (directory, 0), 'w') as w:
                w.write('oi%d' % 0)

        actual_test()
