#-*- coding: utf-8 -*-

"""
monitoring files for changes, on linux try to use inotify,
on freebsd try to use kqueue, on windows try to use winapi,
if not available, use timers

depents on gobject or gobject_fake to work

@TODO:
    insert support to winapi


@Author: Marcelo Aires Caetano <marcelo.caetano@blu360.com.br>
@Date: 2012 may 06
"""

import sys

if 'linux' in sys.platform:
    try:
        from .file_monitor_linux import *
    except:
        from .file_monitor_generic import *

if 'darwin' in sys.platform or 'bsd' in sys.platform:
    try:
        from .file_monitor_bsd import *
    except:
        from .file_monitor_generic import *
    
#TODO: add suport to pyiocp

if 'win32' in sys.platform:
    try:
        from .file_monitor_windows import *
    except:
        from .file_monitor_generic import *
    