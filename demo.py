#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os

from PyQt4 import QtGui, QtCore

from pmxterm import TerminalWidget
from pmxterm.session import Session, BackendManager


class TabbedTerminal(QtGui.QTabWidget):

    
    def __init__(self, parent=None):
        super(TabbedTerminal, self).__init__(parent)
        self.setTabPosition(QtGui.QTabWidget.South)
        self._new_button = QtGui.QPushButton(self)
        self._new_button.setText("New")
        self._new_button.clicked.connect(self.new_terminal)
        self.setCornerWidget(self._new_button)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setWindowTitle("Terminal")
        self._terms = []
        self.tabCloseRequested[int].connect(self._on_close_request)
        self.currentChanged[int].connect(self._on_current_changed)
        self.backendManager = BackendManager(parent = self)
        self.localBackend = self.backendManager.localBackend()
        self.localBackend.started.connect(self.new_terminal)
        #self.localBackend = self.backendManager.backend("Morena", "{'multiplexer': 'tcp://10.0.0.1:56621', 'notifier': 'tcp://10.0.0.1:54742'}")
        QtGui.QApplication.instance().lastWindowClosed.connect(self.localBackend.close)
        self.localBackend.start()
        
    def _on_close_request(self, idx):
        term = self.widget(idx)
        term.stop()
        
            
    def _on_current_changed(self, idx):
        term = self.widget(idx)
        self._update_title(term)

    
    def new_terminal(self):
        # Create session
        session = self.localBackend.session()
        term = TerminalWidget(session, parent = self)
        term.sessionClosed.connect(self._on_session_closed)
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
        print term.info()
        title = "Terminal"
        self.setTabText(idx, title)
        self.setWindowTitle(title)

    
    def _on_session_closed(self):
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
    app = QtGui.QApplication(sys.argv)
    win = TabbedTerminal()
    win.resize(800, 600)
    win.show()
    app.exec_()

