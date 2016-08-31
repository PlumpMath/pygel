# -*- coding: utf-8 -*-

from __future__ import print_function, division

import six
import os
import sys
import logging
import socketqueue
import socket
import Queue
import threading
import functools
import enum
import traceback

import socketqueue

from collections import deque


FORMAT = "%(asctime)s:%(name)s:%(levelname)s: %(message)s"

logger = logging.Logger(__name__, level=logging.DEBUG)

logger.addHandler(logging.StreamHandler())
formatter = logging.Formatter(fmt=FORMAT)
map(lambda x: x.setFormatter(formatter), logger.handlers)


threading.stack_size(4194304)


IO_IN, IO_OUT, IO_PRI, IO_ERR, IO_HUP = (socketqueue.IN,
                                         socketqueue.OUT,
                                         socketqueue.PRI,
                                         socketqueue.ERR,
                                         socketqueue.HUP)


class GelEvent():
    # TODO: it should use enum?
    Accept = True
    Repeat = True
    Cancel = False


class _GelQueue(Queue.Queue):

    @property
    def pipe(self):
        return self._in_pipe

    def _port_generator(self):
        start_port = 1025
        while True:
            yield start_port
            start_port += 1
            if start_port > 65535:
                start_port = 1025

    def _init_pipe(self):
        if sys.platform == "win32" or True:
            while True:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._port = self._ports.next()
                try:
                    self._socket.bind(("127.0.0.1", self._port))
                except socket.error:
                    continue
                self._in_pipe, self._out_pipe = (self._socket, self._socket)
                break
        else:
            self._in_pipe, self._out_pipe = os.pipe()

        self._watch_handler = self.reactor.register_io(self._in_pipe, self._on_data)

    def __init__(self, reactor):
        self.reactor = reactor
        self._ports = self._port_generator()
        self._init_pipe()
        # can't use super in old-style classes
        Queue.Queue.__init__(self).__init__()

    def _close(self):
        if sys.platform == "win32" or True:
            self._in_pipe.close()
            del self._in_pipe
        else:
            map(os.close, (self._in_pipe, self._out_pipe))

        self.reactor.remove_watch(self._watch_handler)

    def _on_data(self, *args):
        if sys.platform == "win32" or True:
            _, a = self._in_pipe.recvfrom(1)
            if a != self._in_pipe.getsockname():
                return
        else:
            os.read(self._in_pipe, 1)

        return cb, args, kwargs

    def put(self, data):
        Queue.Queue.put(self, data)
        if sys.platform == "win32" or True:
            self._out_pipe.sendto("\x00", self._in_pipe.getsockname())
        else:
            os.write(self._out_pipe, "\x00")

    def get(self, *args, **kwargs):
        return Queue.Queue.get(self, timeout=.1)


class Gel(object):

    class EvtType(object):
        TIMER = 0
        IO = 1
        OTHER = 2

    def __init__(self):
        self._handler = self._handler_generator()
        self._mutex = threading.Lock()
        self._socket_queue = socketqueue.SocketQueue()
        self._timers = set()
        self._io_cb = {}
        self._io_handlers = {}
        self._timer_handlers = {}
        self._idle_queue = _GelQueue(self)
        self._quit_queue = _GelQueue(self)

    def _handler_generator(self):
        cur_handle = 1
        while True:
            yield cur_handle
            cur_handle += 1

    def _timer(self, timeout, cb, *args, **kwargs):
        def _timer_callback(timer, cb, handler, *args,  **kwargs):
            with self._mutex:
                self._timers.remove(timer)
            self._idle_queue.put((cb, handler, args, kwargs))

        handler = self._handler.next()
        timer = threading.Timer(timeout, _timer_callback, kwargs=kwargs)

        timer.args = (timer, cb, handler) + args
        with self._mutex:
            self._timers.add(timer)
            self._timer_handlers[handler] = timeout

        timer.start()

    def fd_number(self, fd):
        if type(fd) is int:
            return fd
        if type(fd) in (file, socket):
            return fd.fileno()

    def register_io(self, fd, callback, mode=IO_IN):
        with self._mutex:
            handler = self._handler.next()
            fd_num = self.fd_number(fd)
            self._socket_queue.register(fd, mode)
            self._io_handlers.setdefault(fd_num, set())
            self._io_handlers[fd_num].add(handler)
            self._io_cb.setdefault(handler, set())
            self._io_cb[handler].add(callback)

    def unregister(self, handler):
        with self._mutex:
            fd = self._io_handlers.get(handler)
            if fd is not None:
                self._socket_queue.unregister(fd)
                del self._io_cb[handler]
                del self._io_handlers[fd]

    def idle_call(self, cb, *args, **kwargs):
        self._idle_queue.put((cb, None, args, kwargs))

    def deffer_to_thread(self, cb, *args, **kwargs):
        # TODO: use a thread pool?
        thread = threading.Thread(group="deffered", target=cb, name=cb.__name__,
                                  args=args, kwargs=kwargs)
        thread.start()

    def timeout_call(self, timeout, cb, *args, **kwargs):
        return self._timer(timeout / 1000.0, cb, *args, **kwargs)

    def timeout_seconds_call(self, timeout, cb, *args, **kwargs):
        return self._timer(timeout, cb, *args, **kwargs)

    def main_iteration(self, block=True):
        event = self._socket_queue.poll(timeout=-1 if block else 0)

        if event is self._quit_queue.pipe:
            self._quit_queue._on_data()
            return False

        elif event is self._idle_queue.pipe:
            self._handler_queue_event()
        else:
            self._handle_io_event(event)

        return True

    def main(self):
        while self.main_iteration():
            pass
        self._cancel_all_timers()

    def main_quit(self):
        self._quit_queue.put((cb))

    def _handle_io_event(self, event):
        cbs = []
        handlers_to_remove = []
        with self._mutex:
            for handler in self._handers_by_fd(event):
                cbs.append((handler, self._io_cb[handler]))

        for handler, cb in cbs:
            try:
                if not cb(): # if callback return False it should be unregistered
                    handlers_to_remove.append(handler)
            except Exception as e:
                handlers_to_remove.append(handler)
                logger.exception("%s", e)
                logger.exception("%s", traceback.format_exc())

        with self._mutex:
            map(self.unregister, handlers_to_remove)

    def _handler_queue_event(self):
        # runs the idle callback on the queue or timer callback
        cb, handler, args, kwargs = self._idle_queue._on_data()
        with self._mutex:
            if handler is None:
                evt_type = self.EvtType.OTHER
            elif handler in self._timer_handlers:
                evt_type = self.EvtType.TIMER
                timeout = self._timer_handlers[handler]
                del self._timer_handlers[handler]
            else: # should be a idle_call
                evt_type = self.EvtType.OTHER

        if evt_type == self.EvtType.TIMER:
            if self._safe_callback(cb, *args, **kwargs):
                self._timer(timeout, cb, *args, **kwargs)

        else:
            self._safe_callback(cb, *args, **kwargs)

    def _handers_by_fd(self, fd):

        import ipdb; ipdb.set_trace()
        for handler in self._io_handlers[fd]:
            yield handler

    def _safe_callback(self, cb, *args, **kwargs):
        try:
            return cb(*args, **kwargs)
        except Exception as e:
            logger.exception("%s", e)
            logger.exception("%s", traceback.format_exc())
        return False


    def _cancel_all_timers(self):
        with self._mutex:
            map(lambda timer: timer.cancel(), self._timers)
            self._timers.clear()









