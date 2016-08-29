# -*- coding: utf-8 -*-

from __future__ import print_function
import gel

A = 99
B = 100
C = 3020

def test_idle_add():
    print("test_idle_add passed")

def test_timer():
    def cb():
        print("timer1 passed")

    def cb1(a, b, c):
        assert a == A
        assert b == B
        assert c == C

        print("timer2 passed")

    gel.timeout_add(10, cb)
    gel.timeout_add_seconds(.5, cb1, A, B, C)

def test_io_add_watch():
    import socket
    s = socket.socket()
    s2 = socket.socket()
    s.bind(("", 23455))
    s.listen(1)

    def on_data():
        assert s1.recv(256) == "test1"
        print("io_add_watch passed")

    def on_connect():
        s1 = s.accept()[0]
        gel.io_add_watch(s1, gel.IO_IN, on_data)
        
    gel.io_add_watch(s, gel.IO_IN, on_connect)

    def run():
        s2.connect(("", 23455))
        s2.send("test1")

    gel.idle_add(run)

gel.idle_add(test_idle_add)
# gel.idle_add(test_timer)
# gel.idle_add(test_io_add_watch)
gel.timeout_add_seconds(10, gel.main_quit)

gel.main()
