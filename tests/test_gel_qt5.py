# -*- coding: utf-8 -*-

import sys
try:
    import PyQt5.QtCore
    pyqt5 = True
    from gel.reactor.qt5_reactor import Qt5Reactor
    app = PyQt5.QtCore.QCoreApplication(sys.argv)

except (ImportError):
    pyqt5 = False

from gel.gel import Gel

from .test_gel import GelTestCase
from unittest import skipIf

@skipIf(pyqt5 is False, "Couldn't find PyQt5 on your system.")
class PyQt5GelTestCase(GelTestCase):
    def setUp(self):
        self.reactor = Gel(reactor=Qt5Reactor)
