# -*- coding: utf-8 -*-
"""


  Event Library very similar to gobject/glib/GIO, but pure python
  author: Marcelo Aires Caetano
  date: 15 apr 2012, 27 apr 2012
  email: marcelo@fiveti.com

  this module tryes to implement all gobject functions,
  except the functions concerning to types, because python already has strong
  types, and the gobject types was made to be used in c, not in python


This module must be tread safe, so, the timers must call queues to be executed
in the main thread, ok?
the MPAssyncQueue will be used by sockets and will only work with the main method
"""
import socketqueue as _socketqueue
import time as _time
import socket as _socket
import Queue as _Queue
import traceback as _traceback
import random as _random
import threading as _threading
from threading import Lock as _Lock
_threading.stack_size(4194304)
_lock = _Lock()

class _Timer(object):
    def __init__(self, interval, function, args=()):
        self.interval = interval
        self.function = function
        self.args = args
        self.running = False
        self.queue = _Queue.Queue()
        self.queue_continue = _Queue.Queue()

    def start(self):
        def timer(interval, function, args, queue, queue_cont):
            self.running = True
            while 1:
                try:
                    queue.get(timeout=interval)
                    break
                except _Queue.Empty:
                    try:
                        function(*args)
                    except:
                        print _traceback.print_exc()
                    if not queue_cont.get():
                        break
            self.running = False
        t = _threading.Thread(target=timer, name='timer', args=(self.interval,
                                                           self.function,
                                                           self.args,
                                                           self.queue,
                                                           self.queue_continue))
        t.start()
    def cont(self):
        self.queue_continue.put(1)

    def cancel(self):
        if self.running:
            self.queue.put(1)
            self.queue_continue.put(0)

__all__ = [
        '_IN', 'IO_OUT', 'IO_PRI', 'IO_ERR', 'IO_HUP',
        'timeout_add', 'timeout_add_seconds', 'io_add_watch',
        'main', 'main_quit', 'idle_add', 'get_current_time',
        'source_remove'
        ]
_socket_queue = None
_queue = None
_main = False
_main_thread = _threading.current_thread()
_timeout_add_list = []

IO_IN, IO_OUT, IO_PRI, IO_ERR, IO_HUP = _socketqueue.IN,\
                                        _socketqueue.OUT,\
                                        _socketqueue.PRI,\
                                        _socketqueue.ERR,\
                                        _socketqueue.HUP

_handlers = {}
_handler_id = 0
_io_handlers = {}
_io_handlers_fd = {}
_idle_handlers = {}

def _get_all_timers():
    global _handlers
    for i in _handlers.keys():
        try:
            _handlers[i].join
            assert _handlers[i].isAlive()
            assert not _handlers[i].isFinished()
            yield _handlers[i]
        except:
            pass


def _timeout_add(miliseconds, callback, source=None, *args):
    """
    for internal use.
    mock's gobject timeout_add and returns a timer as a handler
    """
    global _main

    global _handler_id
    global _handlers
    global _queue
    if source == None:
        _handler_id += 1
        source = _handler_id

    seconds = miliseconds / 1000.
    def cb1(callback, source, *args):
        global _handlers
        if source in _handlers:
            if callback(*args) == True:
                _timeout_add(miliseconds, callback, source, *args)

    def cb():
        """
        used queues to the timer be executed into the same thread
        that's hes called.
        """
        _queue.put((cb1, callback, source, args))

    if _main: 
        try:
            t = _handlers[source]
            t.cont()
        except:
            t = _Timer(seconds, cb)
            _handlers[source] = t
            t.start()

    else:
        global _timeout_add_list
        _timeout_add_list.append((seconds,cb, source))

        _handlers[source] = -1

    return source

def timeout_add_seconds(interval, callback, *args):

    """
    the same of timeout_add, but interval is specified in seconds/s
    """

    return timeout_add(int(interval * 1000.), callback, *args)

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

    return _timeout_add(interval, callback, None, *args)

def idle_add(callback, *args):
    """
    callback: a function to call when gobject_fake is idle
    *args: optitional arguments
    Returns: an Integer ID
    """
    global _handler_id
    global _idle_handlers
    _handler_id += 1
    handler = _handler_id
    _idle_handlers[handler] = (callback, args)
    return handler

def get_io_handlers_descriptor(fd):
    """
    returns the full list of source tag for a socket or other fd
    if no io handler registered, returns None
    """
    try:
        return _io_handlers_fd[fd]
    except:
        return None 

def source_remove(tag):
    """
    mocks's gobject source_remove

    The gobject_fake.source_remove() function removes the event source 
    specified by tag (as returned by the timeout_add() and io_add_watch())

    handler: an Integer ID
    Returns: True if the event source was removed
    """
    _handlers = globals()['_handlers']
    global _io_handlers
    global _idle_handlers
    global _io_handlers_fd
    global _socket_queue
    try:
        if tag in _handlers:
            if _handlers[tag] != -1:
                _handlers[tag].cancel()
            del _handlers[tag]
            return True

        if tag in _io_handlers:
            fd, _ = _io_handlers[tag]
            del _io_handlers[tag]
            _socket_queue.unregister(fd)
            del _io_handlers_fd[fd]
            return True

        if tag in _idle_handlers:
            del _idle_handlers[tag]
            return True

        return False

    except Exception, e:
        print e, type (e), "<--- source remove"
        print _traceback.print_exc()
        return False


def get_current_time():
    """
    Returns: the current time as the number of seconds and microseconds from
    the epoch.
    """
    return _time.time()

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


    global _socket_queue
    global _handler_id
    global _io_handlers
    global _io_handlers_fd
    if not _socket_queue:
        _socket_queue = _socketqueue.SocketQueue()

    if not _io_handlers.has_key(fd):
        _socket_queue.register(fd, condition)
        _handler_id += 1
        handler = _handler_id
        _io_handlers[handler] = (fd, (callback, args))
        _io_handlers_fd[fd] =  (handler, (callback, args))




def main():
    global _socket_queue
    global _io_handlers_fd
    if not _socket_queue:
        _socket_queue = _socketqueue.SocketQueue()
    global _queue
    global _timeout_add_list 
    _handlers = globals()['_handlers']
    if not _queue:
        _queue = _GobjectQueue()

    def on_queue_callback(queue):
        cb1, callback, source, args = _queue.get()
        cb1(callback, source, *args)

    _queue.callback.append(on_queue_callback)
    global _main
    _main = True

    #starting hanged timers
    for i in _timeout_add_list:
        seconds, cb, source = i
        t = _Timer(seconds, cb)
        t.start()
        _handlers[source] = t
    _timeout_add_list = []


    def __main():
        f = _socket_queue.poll(timeout=1)
        if not f:
            # running idle queue
            global _idle_handlers
            to_remove = []
            for i in _idle_handlers:
                try:
                    func, a = _idle_handlers[i]
                    if func(*a) != True:
                        to_remove.append(i)
                except Exception, e:
                    print e, type(e), "exception!"
                    print _traceback.print_exc()
            for i in to_remove:
                #removing from list idles that not returned True
                del _idle_handlers[i]

        else:
            for fd, event_type in f:
                #processing all events
                try:
                    handler, func = _io_handlers_fd[fd]
                    func, args = func
                    try:
                        if not func(fd, event_type, *args):
                            source_remove(handler)
                    except Exception, e:
                        print e, type(e), "socket exception"
                        print _traceback.print_exc()
                except Exception, e:
                    print "*** error on processing event"
                    print "unregistering io"
                    print e, type(e)
                    print _traceback.print_exc()
                    _socket_queue.unregister(fd)


    while _main:
        try:
            __main()
        except KeyboardInterrupt:
            print "\rStopped by CTRL+C"
            _cancel_all_timers(1)
            break 
    _cancel_all_timers()

def _cancel_all_timers(command=0):
    global _handlers
    for source in _handlers:
        try:
            seconds = _handlers[source].interval
            cb = _handlers[source].function
            _handlers[source].cancel()
        except Exception, e:
            pass#print e, type(e)

        if command:
            # if the timer was stopped by a ctrl+c, so when main is called again
            # the timer will reborn.
            global _timeout_add_list
            _timeout_add_list.append((seconds,cb, source))

def main_quit():
    global _main
#    _cancel_all_timers()
    _main = False
    #for i in _get_all_timers():
    #    i.join()



class _GobjectQueue(_Queue.Queue):


    def __init__(self, *args):
        self.callback = []
        self.sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        while 1:
            try:
                """
                @todo: use pipes instead sockets for every SO that's not windows.
                """
                self.port = _random.randint(1025, 65534)
                self.sock.bind(("127.0.0.1", self.port))
                break
            except Exception, e:
                print e, type(e)
                print "o.O"
                continue
        io_add_watch(self.sock, IO_IN, self._on_data)
        _Queue.Queue.__init__(self, *args)

    def put(self, data):
        _Queue.Queue.put(self, data)
        self.sock.sendto("1", self.sock.getsockname())

    def get(self, *args, **kw):
        r = _Queue.Queue.get(self, timeout=0.1)
        return r

    def _on_data(self, *args):
        d, a = self.sock.recvfrom(1)
        if a != self.sock.getsockname():
            return

        for i in self.callback:
            try:
                i(self)
            except:
                pass
        return True
