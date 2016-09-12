from abc import ABCMeta, abstractmethod
import six

import logging
import traceback

logger = logging.getLogger('gel')

if not hasattr(six.moves.builtins, 'file'):
    import io
    six.moves.builtins.file = io.FileIO

class BaseReactorNoMeta(object):
    def _safe_callback(self, cb, *args, **kwargs):
        try:
            return cb(*args, **kwargs)
        except AssertionError as e:
            raise(e)
        except Exception as e:
            logger.exception("%s", e)
            logger.exception("%s", traceback.format_exc())
        return False

    def _handler_generator(self):
        cur_handle = 1
        while True:
            yield cur_handle
            cur_handle += 1


@six.add_metaclass(ABCMeta)
class BaseReactor(BaseReactorNoMeta):

    @abstractmethod
    def _timer(self, seconds, cb, *args, **kwargs):
        pass

    @abstractmethod
    def register_io(self, fd, callback, mode, *args, **kwargs):
        pass

    @abstractmethod
    def unregister_io(self, handler):
        pass

    @abstractmethod
    def idle_call(self, cb, *args, **kwargs):
        pass

    @abstractmethod
    def main_iteration(self, block=True, timeout=None):
        pass

    @abstractmethod
    def main(self):
        pass

    @abstractmethod
    def main_quit(self):
        pass

    @abstractmethod
    def _cancel_all_timers(self):
        pass

