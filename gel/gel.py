# -*- coding: utf-8 -*-

from __future__ import print_function, division

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
import time

from .reactor.gel_reactor import GelReactor

from .constants import (IO_IN, EvtType)


Queue = six.moves.queue

logger = logging.getLogger('gel')
logger.setLevel(logging.WARNING)


class GelEvent(object):
    # TODO: it should use enum?
    Accept = True
    Repeat = True
    Cancel = False

class GelFactoryError(ImportError):
    pass

class GelExitError(OSError):
    pass


class Gel(object):

    def __init__(self, reactor=GelReactor):
        self._reactor = reactor()

    @classmethod
    def from_reactor(cls, event_loop='gel'):
        """
        factory class method to get the right reactor
        available options: gel, qt4, qt5
        """
        if event_loop.lower() in  ('gel', 'pygel'):
            return cls(reactor=GelReactor)
        elif event_loop.lower() in ('qt4', 'pyqt4'):
            from .reactor.qt4_reactor import Qt4Reactor
            return cls(reactor=Qt4Reactor)
        elif event_loop.lower() in ('qt5', 'pyqt5', 'qt'):
            from .reactor.qt5_reactor import Qt5Reactor
            return cls(reactor=Qt5Reactor)
        else:
            raise GelFactoryError("Can't use the event_loop '%s', choose one "
                                  "between gel, qt4 or qt5")

    def _handler_generator(self):
        cur_handle = 1
        while True:
            yield cur_handle
            cur_handle += 1

    def register_io(self, fd, callback, mode=IO_IN, *args, **kwargs):
        self._reactor.register_io(fd, callback, mode, *args, **kwargs)

    def unregister(self, handler):
        self._reactor.unregister_io(handler)

    def idle_call(self, cb, *args, **kwargs):
        self._reactor.idle_call(cb, *args, **kwargs)

    def threaded_wrapper(self, cb):
        """
        the same as wait_task but as an decorator
        decorates a task to run in a thread but behaving as a normal task

        it makes the function waits til the thread is ended,
        but the main_loop will continue to process events in meantime

        >>> @reactor.threaded_wrapper
        >>> def a_long_wait_task(*args, **kwargs):
        >>>     ....
        >>>
        >>> response = a_long_wait_task(*args, **kwargs)

        """

        @functools.wraps(cb)
        def decorated(*args, **kwargs):
            return self.wait_task(cb, *args, **kwargs)

        return decorated

    def selector(self, file_handlers, timeout_seconds=None):
        if not (isinstance, collections.Iterable):
            raise AttributeError("file handlers should be iterable")

        output = []

        def event_handler(event=None):
            if event is None:
                pass
            output.append(event)

        if timeout_seconds is not None:
            self.timeout_seconds_call(timeout_seconds, event_handler)

        registered = [self.register_io(file_handler, event_handler) for file_handler in file_handlers]

        while len(output) == 0 and self.main_iteration():
            pass

        if len(output) == 0: #  it means main_quit was called
            # once we already consumed the exit event, we need to resend it to the main loop
            self.main_quit()
            raise GelExitError('main loop exited before io response')

        # unregister io after call
        [self.unregister(i) for i in registered]

        return output[0]

    def wait_task(self, cb, *args, **kwargs):
        """
        spawns a task to a thread and waits the execution of the mainloop until the response
        the other events will continue to run in meantime
        """

        output = []

        def response_callback(status, response):
            output.append(status)
            output.append(response)

        @functools.wraps(cb)
        def callback(reactor, *args, **kwargs):
            try:
                ret = cb(*args, **kwargs)
            except Exception as e:
                self.idle_call(response_callback, False, e)
                return
            self.idle_call(response_callback, True, ret)

        self._reactor.deffer_to_thread(callback, *args, **kwargs)

        while len(output) == 0 and self.main_iteration():
            pass

        if len(output) == 0:
            # once we already consumed the exit event, we need to resend it to the main loop
            self.main_quit()
            raise GelExitError('main loop exited before task response')

        status, response = output

        if status is False:
            raise response
        else:
            return response

    def timeout_call(self, miliseconds, cb, *args, **kwargs):
        return self._reactor._timer(miliseconds / 1000.0, cb, *args, **kwargs)

    def timeout_seconds_call(self, seconds, cb, *args, **kwargs):
        return self._reactor._timer(seconds, cb, *args, **kwargs)

    def sleep(self, miliseconds):
        """
        sleeps while the reactor do other events
        :param timeout:
        """
        response = []
        def callback():
            response.append(True)
        self.timeout_call(miliseconds, callback)
        while not response and self.main_iteration():
            pass
        if not response:
            # once we already consumed the exit event, we need to resend it to the main loop
            self.main_quit()
            raise GelExitError('main loop exited before sleep is done')

    def sleep_seconds(self, seconds):
        return self.sleep(seconds * 1000)

    def main_iteration(self, block=True, timeout_seconds=None):
        return self._reactor.main_iteration(block, timeout_seconds)

    def main(self):
        self._reactor.main()

    def main_quit(self):
        self._reactor.main_quit()

