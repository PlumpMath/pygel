#-*- encoding: utf-8 -*-
import os
import sys
import unittest
sys.path.append("..")
sys.path.append('.')
from event_lib import inotify
import shutil
from event_lib import file_monitor_linux

import gel as gobject


directory = 'file_monitor_testing'
class TimeoutError(IOError):
    pass


def el_main(f):
    def wrap(*args, **kw):
        r = f(*args, **kw)
        def timeout_error():
            raise TimeoutError, 'callback took too long to execute'
        gobject.timeout_add(50, timeout_error) 
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

class EventLibFileMonitorLinuxTestCase(unittest.TestCase):
    def setUp(self):
        try:
            self.tearDown()
        except:
            pass
        os.mkdir(directory)
        self.file_watch = file_monitor_linux.FileWatch(gobject)
    
    def tearDown(self):
        shutil.rmtree(directory)
        del self.file_watch
 
    @el_main 
    def test_file_watcher(self):
        path =  '%s/file_test' % directory
        with open(path, "w") as w:
            w.write("hi")
        
        @el_quit
        def callback(apath):
            self.assertEqual(apath, path)
            
        self.file_watch.watch_file(path, callback)
        with open(path, 'a') as w:
            w.write('olá')
            
    def test_create_file_watcher_directory(self):
        def callback(path):
            return 
        self.file_watch.watch_directory(directory, callback)
        self.assertEqual(self.file_watch.watching.keys()[0], directory)
        self.assertEqual(self.file_watch.watching_wd[self.file_watch.watching[directory]], callback)
            
    @el_main
    def test_directory_watcher(self):
        
        @el_quit 
        def callback(apath):
            self.assertEqual(apath, directory)
        
        self.file_watch.watch_directory(directory, callback)
        
        with open('%s/file_%d' % (directory, 0),'w') as w:
            w.write('oi%d' %0)