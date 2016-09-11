from PyQt4.QtCore import (QObject, QCoreApplication, QTimer, Qt,
                          QMetaObject, QEventLoop, QSocketNotifier,
                          QMutex, QThread, QThreadPool, QRunnable,
                          pyqtSignal, pyqtSlot)

import uuid

import six

import socket

from ..constants import IO_IN, IO_OUT, IO_PRI, IO_ERR, IO_HUP

from . import BaseReactor, BaseReactorNoMeta


class Lock(object):

    def __init__(self):
        self._mutex = QMutex()

    def __enter__(self):
        self._mutex.lock()

    def __exit__(self, type, value, tb):
        self._mutex.unlock()

    def acquire(self):
        self._mutex.lock()

    def release(self):
        self._mutex.unlock()


class Thread(QRunnable):
    def __init__(self, parent, cb, *args, **kwargs):
        QRunnable.__init__(self)
        self._mutex = Lock()
        self._parent = parent
        with self._mutex:
            self._cb = cb
            self._args = args
            self._kwargs = kwargs
            self._parent._threads.add(self)

    def run(self):
        with self._mutex:
            self._parent._threads.remove(self)
            self._cb(*self._args, **self._kwargs)


class _CallAfter(QObject):

    activate = pyqtSignal([str])

    def __init__(self, callback, parent=None):
        super(_CallAfter, self).__init__(parent)
        self.activate.connect(self._call, Qt.QueuedConnection)
        if not callable(callback):
            raise Qt5ReactorError('callback should be callable')
        self._callback = callback

    @pyqtSlot(str)
    def _call(self, id):
        self._callback(id)


class Qt4ReactorError(AttributeError):
    pass

# @six.add_metaclass(BaseReactor)
class Qt4Reactor(QObject, BaseReactorNoMeta):

    _exiting_signal = pyqtSignal(name='exiting')

    constants = {IO_IN: QSocketNotifier.Read,
                 IO_OUT: QSocketNotifier.Write,
                 IO_PRI: QSocketNotifier.Read,
                 IO_ERR: QSocketNotifier.Exception,
                 IO_HUP: QSocketNotifier.Exception}

    def __init__(self, instance=None):
        QObject.__init__(self)

        if instance is None:
            # gets the global instance
            instance = QCoreApplication.instance()

        elif not isinstance(instance, QCoreApplication):
            raise Qt5ReactorError("instance should be None or an valid QApplication")

        self._handlers = self._handler_generator()

        self._mutex = Lock()
        self._exit_mutex = Lock()
        self._idle_caller = _CallAfter(self._idle_callback, self)
        self._idle_handlers = {}

        self._reactor = instance
        self._timers = {}
        self._io_handlers = {}
        self._threads = set()
        self.__exiting = False
        self._exiting_signal.connect(self._on_exit)

    @property
    def _exiting(self):
        with self._exit_mutex:
            return self.__exiting

    @_exiting.setter
    def _exiting(self, value):
        with self._exit_mutex:
            self.__exiting = value

    def _on_exit(self):
        self._exiting = True

    def _handler_generator(self):
        cur_handle = 1
        while True:
            yield cur_handle
            cur_handle += 1

    def _timer(self, seconds, cb, *args, **kwargs):
        timer = QTimer()
        timer.setInterval(int(seconds * 1000))
        timer.setSingleShot(True)

        def _timer_cb():
            with self._mutex:
                if timer in self._timers:
                    del self._timers[timer]
                else: return
            if self._safe_callback(cb, *args, **kwargs):
                self._timer(timeout, cb, *args, **kwargs)

        with self._mutex:
            # we need to store the callback to avoid python to collect the no
            # referenced closure
            # buggy eik!
            self._timers[timer] = _timer_cb
        timer.timeout.connect(_timer_cb, Qt.QueuedConnection)
        timer.start()

    def register_io(self, fd, callback, mode, *args, **kwargs):
        handler = six.next(self._handlers)
        notifier = QSocketNotifier(self.fd_number(fd), self.constants[mode])
        with self._mutex:
            self._io_handlers[handler] = notifier

        def _io_cb(*_):
            if not self._safe_callback(callback, fd, *args, **kwargs):
                self.unregister_io(handler)

        with self._mutex:
            # we need to store the closure callback to avoid the garbage collector
            # from collecting the closure
            self._io_handlers[handler] = (notifier, _io_cb)

        notifier.setEnabled(True)
        notifier.activated.connect(_io_cb)

    def fd_number(self, fd):
        if type(fd) is int:
            return fd
        if type(fd) in (file, socket.socket):
            return fd.fileno()

    def unregister_io(self, handler):
        with self._mutex:
            notifier, _ = self._io_handlers[handler]
            notifier.setEnabled(False)
            notifier.deleteLater()
            del self._io_handlers[handler]

    def idle_call(self, cb, *args, **kwargs):
        id = str(uuid.uuid4())
        with self._mutex:
            self._idle_handlers[id] = (cb, args, kwargs)
        self._idle_caller.activate.emit(id)

    def _idle_callback(self, id):
        with self._mutex:
            cb, args, kwargs = self._idle_handlers[id]
            del self._idle_handlers[id]
        self._safe_callback(cb, *args, **kwargs)

    def main_iteration(self, block=True, timeout_miliseconds=None):
        if block is True or timeout_miliseconds is not None:
            flags = QEventLoop.WaitForMoreEvents
        else:
            flags = QEventLoop.AllEvents
        if timeout_miliseconds is None:
            self._reactor.processEvents(flags)
        else:
            self._reactor.processEvents(flags, timeout_miliseconds)
        # returns True if there is no exiting call, otherwise..
        return not self._exiting

    def main(self):
        self._reactor.exec_()

    def main_quit(self):
        self._exiting_signal.emit()
        self._reactor.exit(0)

    def _cancel_all_timers(self):
        with self._mutex:
            for timer, cb in self._timers.items():
                timer.stop()
            self._timers.clear()

    def deffer_to_thread(self, cb, *args, **kwargs):
        args = (self, ) + args
        thread = Thread(self, cb, *args, **kwargs)
        QThreadPool.globalInstance().start(thread)

