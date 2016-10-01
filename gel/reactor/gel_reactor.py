# -*- coding: utf-8 -*-

"""
low level gel reactor for compatibility layer
"""

from __future__ import print_function, division, absolute_import

import collections
import six
import os
import sys
import logging
import socketqueue
import socket
import threading
import functools
import traceback

from ..constants import (IO_IN, IO_OUT,
                         IO_ERR, IO_HUP, IO_PRI,
                         EvtType)

from . import BaseReactor

threading.stack_size(4194304)

logger = logging.getLogger('gel')

Queue = six.moves.queue



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
        if sys.platform == "win32":
            while True:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._port = six.next(self._ports)
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
        if sys.platform == "win32":
            self._in_pipe.close()
            del self._in_pipe
        else:
            map(os.close, (self._in_pipe, self._out_pipe))

        self.reactor.remove_watch(self._watch_handler)

    def _on_data(self, *args):
        if sys.platform == "win32":
            _, a = self._in_pipe.recvfrom(1)
            if a != self._in_pipe.getsockname():
                return
        else:
            os.read(self._in_pipe, 1)

    def put(self, data):
        Queue.Queue.put(self, data)
        if sys.platform == "win32":
            self._out_pipe.sendto("\x00", self._in_pipe.getsockname())
        else:
            os.write(self._out_pipe, b"\x00")

    def get(self, *args, **kwargs):
        return Queue.Queue.get(self, timeout=.1)


class GelReactor(BaseReactor):

    IO_IN, IO_OUT, IO_PRI, IO_ERR, IO_HUP = (IO_IN, IO_OUT,
                                             IO_PRI, IO_ERR,
                                             IO_HUP)

    def __init__(self):
        self._handler = self._handler_generator()
        self._mutex = threading.Lock()
        self._current_thread = threading.current_thread()
        self._socket_queue = socketqueue.SocketQueue()
        self._timers = set()
        self._io_cb = {}
        self._io_handlers = {}
        self._io_fd = {}
        self._timer_handlers = {}
        self._idle_queue = _GelQueue(self)
        self._quit_queue = _GelQueue(self)

    def _timer(self, timeout, cb, *args, **kwargs):
        def _timer_callback(timer, cb, handler, *args,  **kwargs):
            if hasattr(timer, "cancelled"):
                return
            with self._mutex:
                if timer not in self._timers:
                    pass
                else: self._timers.remove(timer)
            self._idle_queue.put((cb, handler, args, kwargs))

        handler = six.next(self._handler)
        timer = threading.Timer(timeout, _timer_callback, kwargs=kwargs)

        timer.args = (timer, cb, handler) + args
        with self._mutex:
            self._timers.add(timer)
            self._timer_handlers[handler] = timeout

        timer.start()

    def fd_number(self, fd):
        if type(fd) is int:
            return fd
        if type(fd) in (file, socket.socket):
            return fd.fileno()

    def register_io(self, fd, callback, mode=IO_IN, *args, **kwargs):
        with self._mutex:
            handler = six.next(self._handler)
            self._socket_queue.register(fd, mode)
            self._io_handlers.setdefault(fd, set())
            self._io_handlers[fd].add(handler)
            self._io_fd[handler] = fd
            self._io_cb[handler] = (callback, args, kwargs)

    def deffer_to_thread(self, cb, *args, **kwargs):
        """
        deffer execution to thread injecting the reactor in the thread
        example:

        def response():
            print("this task is called in main thread.")

        def threaded_task(reactor, *args, **kwargs):
            print(args, kwargs)
            reactor.idle_call(response)

        reactor.deffer_to_thread(threaded_task, 1, 2, 3, x=4)
        """
        # TODO: use a thread pool?
        args = (self, ) + args
        thread = threading.Thread(target=cb, name=cb.__name__,
                                  args=args, kwargs=kwargs)
        thread.start()

    def unregister_io(self, handler):
        with self._mutex:
            fd = self._io_fd.get(handler)
            if fd is not None:
                del self._io_cb[handler]
                self._io_handlers[fd].remove(handler)
                self._socket_queue.unregister(fd)

    def idle_call(self, cb, *args, **kwargs):
        self._idle_queue.put((cb, None, args, kwargs))

    def timeout_call(self, timeout, cb, *args, **kwargs):
        return self._timer(timeout / 1000.0, cb, *args, **kwargs)

    def main_iteration(self, block=True, timeout_seconds=None):
        if threading.current_thread() is not self._current_thread:
            raise OSError("can't run main iteration inside another thread"
                          " than the thread that created the reactor.")
        try:
            if timeout_seconds is None:
                event = self._socket_queue.poll(timeout=-1 if block else 0)[0][0]
            else:
                event = self._socket_queue.poll(timeout=timeout_seconds)
        except IndexError:
            # this exception will be caugth whenever using block=False or timeout
            return True

        if event is self._quit_queue.pipe:
            self._quit_queue._on_data()
            self._quit_queue.get()
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
        self._quit_queue.put(True)
        pass

    def _handle_io_event(self, event):
        cbs = []
        handlers_to_remove = []
        with self._mutex:
            for handler in self._handlers_by_fd(event):
                cbs.append((handler, self._io_cb[handler]))

        for handler, cb in cbs:
            cb, args, kwargs = cb
            try:
                if not cb(event, *args, **kwargs): # if callback return False it should be unregistered
                    handlers_to_remove.append(handler)
            except Exception as e:
                handlers_to_remove.append(handler)
                logger.exception("%s", e)
                logger.exception("%s", traceback.format_exc())

        [self.unregister_io(i) for i in handlers_to_remove]

    def _handler_queue_event(self):
        # runs the idle callback on the queue or timer callback
        self._idle_queue._on_data()
        data = self._idle_queue.get()
        cb, handler, args, kwargs = data

        with self._mutex:
            if handler is None:
                evt_type = EvtType.OTHER
            elif handler in self._timer_handlers:
                evt_type = EvtType.TIMER
                timeout = self._timer_handlers[handler]
                del self._timer_handlers[handler]
            else: # should be a idle_call
                evt_type = EvtType.OTHER

        if evt_type == EvtType.TIMER:
            if self._safe_callback(cb, *args, **kwargs):
                self._timer(timeout, cb, *args, **kwargs)

        else:
            self._safe_callback(cb, *args, **kwargs)

    def _handlers_by_fd(self, fd):
        for handler in self._io_handlers[fd]:
                yield handler

    def _cancel_all_timers(self):
        with self._mutex:
            for timer in self._timers:
                timer.cancelled = True
                timer.cancel()
            self._timers.clear()
