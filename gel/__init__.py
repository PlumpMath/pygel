# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

import time

__all__ = ['_IN', 'IO_OUT', 'IO_PRI', 'IO_ERR', 'IO_HUP',
           'timeout_add', 'timeout_add_seconds', 'io_add_watch',
           'main', 'main_iteration', 'main_quit', 'idle_add',
           'get_current_time', 'source_remove', 'Gel']

from .gel import Gel

IO_IN, IO_OUT, IO_PRI, IO_ERR, IO_HUP = (gel.IO_IN,
                                         gel.IO_OUT,
                                         gel.IO_PRI,
                                         gel.IO_ERR,
                                         gel.IO_HUP)


_global_reactor = Gel()


def timeout_add_seconds(interval, callback, *args):
    """
    the same of timeout_add, but interval is specified in seconds/s
    """
    return _global_reactor.timeout_seconds_call(interval, callback, *args)


def timeout_add(interval, callback, *args):
    """

    the gobject_fake.timeout_add() function (specified by callback) to be
    called at regular intervals (specified by interval). Adittional arguments
    to pass to callback canb e specified after callback.

    The function is called repeatedly until it returns False, at which point
    the timeout is automatically destroyed and the function will not be
    called again. THe first call to the function will be at the end of the
    first interval. Note that timeout functions may be deleayed, due to the
    processing of other event sources. Thus they should be relied on for
    precise timing. After each call to the timeout function, the time of next
    timeout is recalculated based on the currente time and the given interval
    (it does not try to 'catch up' time lost in delays).

    interval: the time between calls to the function, in milliseconds
    callback: the function to call
    *args:    zero or more arguments that will be passed to callback

    Retruns: an intenger ID of the event source

    """

    return _global_reactor.timeout_call(interval, callback, *args)


def idle_add(callback, *args):
    """
    callback: a function to call when gobject_fake is idle
    *args: optitional arguments
    Returns: an Integer ID
    """
    return _global_reactor.idle_call(callback, *args)



def source_remove(tag):
    """
    mocks's gobject source_remove

    The gobject_fake.source_remove() function removes the event source
    specified by tag (as returned by the timeout_add() and io_add_watch())

    handler: an Integer ID
    Returns: True if the event source was removed
    """
    _global_reactor.unregister(tag)


def get_current_time():
    """
    Returns: the current time as the number of seconds and microseconds from
    the epoch.
    """
    return time.time()


def io_add_watch(fd, condition, callback, *args):
    """
    fd :    a Python file object or an integer file descriptor ID
    condition :    a condition mask
    callback :    a function to call
    args :    additional arguments to pass to callback
    Returns :    an integer ID of the event source

    The gobject.io_add_watch() function arranges for the file
     (specified by fd) to be monitored by the main loop for the specified
     condition. fd may be a Python file object or an integer file descriptor.
      The value of condition is a combination of:
    gobject.IO_IN    There is data to read.
    gobject.IO_OUT    Data can be written (without blocking).
    gobject.IO_PRI    There is urgent data to read.
    gobject.IO_ERR    Error condition.
    gobject.IO_HUP    Hung up (the connection has been broken, usually for pipes and sockets).

    Additional arguments to pass to callback can be specified after
     callback. The idle priority may be specified as a keyword-value pair
      with the keyword "priority".
      The signature of the callback function is:

  def callback(source, cb_condition, ...)

    where source is fd, the file descriptor;
    cb_condition is the condition that triggered the signal;
     and, ... are the zero or more arguments that were passed to the
      gobject.io_add_watch() function.

    If the callback function returns FALSE it will be automatically
     removed from the list of event sources and will not be called again.
      If it returns TRUE it will be called again when the
       condition is matched.
    """

    return _global_reactor.register_io(fd, callback, condition, *args)


def main_iteration(block=True):
    """
    block :
        if True block if no events are pending

    Returns :
        True if the gtk.main_quit() function has been called for the innermost main loop.

    The gtk.main_iteration() function runs a single iteration of the mainloop. If no events are waiting to be processed PyGTK will block until the next event is noticed if block is True. This function is identical to the gtk.main_iteration_do() function.
    """
    _global_reactor.main_iteration(block=block)



def main():
    _global_reactor.main()

def main_quit():
    _global_reactor.main_quit()
