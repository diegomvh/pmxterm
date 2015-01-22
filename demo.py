#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os

try:
    from PyQt5 import QtGui, QtCore, QtWidgets
except:
    from PyQt4 import QtGui, QtCore
    QtWidgets = QtGui

from pmxterm.terminal import TerminalWidget
from pmxterm.frontend.manager import Backend, BackendManager
from pmxterm.schemes import ColorScheme

ColorScheme.loadSchemes(os.path.abspath("schemes"))

class TabbedTerminal(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super(TabbedTerminal, self).__init__(parent)
        self.setTabPosition(QtWidgets.QTabWidget.South)
        self._new_button = QtWidgets.QPushButton(self)
        self._new_button.setText("New")
        self._new_button.clicked.connect(self.new_terminal)
        self.setCornerWidget(self._new_button)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setWindowTitle("Terminal")
        self._terms = []
        self.tabCloseRequested[int].connect(self._on_close_request)
        self.currentChanged[int].connect(self._on_current_changed)
        # Manager
        self.backendManager = BackendManager(parent = self)
        QtWidgets.QApplication.instance().lastWindowClosed.connect(self.backendManager.stopAll)
        
    def run_local_backend(self):
        self.backend = self.backendManager.localBackend()
        self.backend.started.connect(self.new_terminal)
        self.backend.start()
        
    def run_remote_backend(self, address):
        self.backend = self.backendManager.backend("remote", address)
        self.backend.started.connect(self.new_terminal)
        self.backend.start()
        
    def _on_close_request(self, idx):
        term = self.widget(idx)
        term.stop()

    def _on_current_changed(self, idx):
        term = self.widget(idx)
        self._update_title(term)
    
    def new_terminal(self):
        # Create session
        if self.backend.state() == Backend.Running:
            session = self.backend.session()
            term = TerminalWidget(session, parent = self)
            term.sessionClosed.connect(self.on_session_closed)
            self.addTab(term, "Terminal")
            self._terms.append(term)
            self.setCurrentWidget(term)
            session.start()
            term.setFocus()
        
    def timerEvent(self, event):
        self._update_title(self.currentWidget())

    def _update_title(self, term):
        if term is None:
            self.setWindowTitle("Terminal")
            return
        idx = self.indexOf(term)
        title = "Terminal"
        self.setTabText(idx, title)
        self.setWindowTitle(title)
    
    def on_session_closed(self):
        term = self.sender()
        try:
            self._terms.remove(term)
        except:
            pass
        self.removeTab(self.indexOf(term))
        widget = self.currentWidget()
        if widget:
            widget.setFocus()
        if self.count() == 0:
            self.new_terminal()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = TabbedTerminal()
    # win.run_local_backend()
    win.run_remote_backend(sys.argv[1])
    win.resize(800, 600)
    win.show()
    app.exec_()

