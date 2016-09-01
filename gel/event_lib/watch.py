import sys
import os
from . import file_monitor

modules = {}

def mtime(file):
    try:
        return os.path.getmtime(file)
    except:
        return 0

def module_file(mod):
    try:
        f = mod.__file__
        if not f or not os.path.exists(f):
            return False
        if f[-1] in ('c', 'o') and f[-3:-1] == 'py':

            f = f[:-1]
        return f
    except Exception as e:
        return False

def module_table():
    global modules
    for i in sys.modules.copy():
        f = module_file(sys.modules[i])
        if not f:
            continue
        modules[i] = {
            'module': sys.modules[i],
            'file': os.path.abspath(f),
            'mtime': mtime(f)
            }

def reload_module(m):
    global modules

    if os.path.splitext(sys.modules[m].__file__)[1] in ('.pyc', '.pyo'):
        try:
            os.remove(sys.modules[m].__file__)
        except:
            pass
    try:
        reload(modules[m]['module'])
    except:
        pass

def get_file_module(wd):
    global modules
    for i in modules:
        if wd == modules[i]['file']:
            return i

def watch(cb=None):
    global modules
    fw = file_monitor.FileWatch()

    module_table()

    def callback(wd):
        if wd == '__main__':
            return
        module_table()
        module_name = get_file_module(wd)
        global modules;
        print " * Reloading Module <%s>" % str(module_name)
        reload(sys.modules[module_name])
        if cb:
            cb()
        return True

    for i in modules:
        f = modules[i]['file']
        #print "watching file: ", f
        try:
            fw.watch_file(f, callback)
        except:
            print "error watching", f
