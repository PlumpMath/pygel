import os
import sys
import unittest

from gel.event_lib import inotify
import socketqueue
import shutil
from gel.event_lib.inotify import (IN_CREATE, IN_DELETE,
                                   IN_WRITE, IN_MOVED_FROM,
                                   IN_MOVED_TO, IN_MOVE_SELF)


class EventLibInotifyTestCase(unittest.TestCase):

    def setUp(self):
        try:
            self.tearDown()
        except:
            pass
        os.mkdir("inotify_testing")

    def tearDown(self):
        shutil.rmtree('inotify_testing')

    def test_inotify_start(self):
        i = inotify.Inotify()
        self.assertGreater(i.fileno(), 0)

    def test_inotify_watch_directory_create_file(self):
        i = inotify.Inotify()
        masks = IN_CREATE
        i.add_watch("inotify_testing", masks)
        with open("inotify_testing/file", "w") as w:
            w.write("")
        result = [j for j in i.read()]
        self.assertTrue(result)

    def test_inotify_watch_directory_delete_file(self):
        i = inotify.Inotify()
        masks = IN_DELETE
        with open("inotify_testing/file", "w") as w:
            w.write("")

        i.add_watch("inotify_testing", masks)
        os.remove("inotify_testing/file")
        result = [j for j in i.read()]
        self.assertTrue(result)

    def test_inotify_watch_directory_move_file(self):
        i = inotify.Inotify()
        masks = IN_MOVED_FROM | IN_MOVED_TO
        with open("inotify_testing/file", "w") as w:
            w.write("")

        i.add_watch("inotify_testing", masks)
        shutil.move("inotify_testing/file", "inotify_testing/file2")
        result = [j for j in i.read()]
        self.assertTrue(result)

    def test_inotify_modify_file(self):
        i = inotify.Inotify()
        masks = inotify.IN_MODIFY

        with open("inotify_testing/file", "w") as w:
            w.write("a")

        i.add_watch('inotify_testing/file', masks)

        with open("inotify_testing/file", "a") as w:
            w.write("a")

        self.assertTrue([j for j in i.read()])
