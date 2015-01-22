#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import time
import json
import ast
import signal
import socket
import tempfile

if sys.version_info.major < 3:
    str = unicode

try:
    from PyQt5 import QtCore, QtNetwork
except:
    from PyQt4 import QtCore, QtNetwork

from .session import Session
from ..utils import encoding

LOCAL_BACKEND_SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "main.py"))

class Backend(QtCore.QObject):
    # Errors of Backend
    FailedToStart = 0
    Crashed = 1
    Timedout = 2
    WriteError = 4
    ReadError = 3
    UnknownError = 5
    # ------------- States of Backend
    NotRunning = 0
    Starting = 1
    Running = 2
    # ------------- Signals
    error = QtCore.pyqtSignal(int)
    started = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(int)
    stateChanged = QtCore.pyqtSignal(int)
    
    def __init__(self, name, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.name = name
        self.sessions = {}
        self._state = self.NotRunning
        self.multiplexer = None
        self.notifier = None

    def _set_state(self, state):
        self._state = state
        self.stateChanged.emit(state)

    def state(self):
        return self._state

    #------------ Sockets
    def startNotifier(self):
        address = tempfile.mktemp(prefix="pmx")
        self.notifier = QtNetwork.QLocalServer(self)
        self.notifier.listen(address)
        self.notifier.newConnection.connect(self.on_notifier_newConnection)
        return address

    def startMultiplexer(self, address):
        self.multiplexer = socket.socket(socket.AF_UNIX)
        self.multiplexer.connect(address)

    def execute(self, command, args = None):
        if args is None:
            args = []
        data = {"command": command, "args": args}
        self.multiplexer.send(json.dumps(data).encode(encoding.FS_ENCODING))
        result = self.multiplexer.recv(4096)
        return json.loads(result.decode(encoding.FS_ENCODING))

    def on_notifier_newConnection(self):
        connection = self.notifier.nextPendingConnection()
        connection.readyRead.connect(lambda con = connection: self.socketReadyRead(con))
        
    def socketReadyRead(self, connection):
        message = json.loads(encoding.from_fs(connection.readAll().data()))
        sid = message['sid']
        if sid in self.sessions:
            result = self.sessions[sid].message(message)
        else:
            result = False
        connection.write(json.dumps(result).encode(encoding.FS_ENCODING))

    def start(self):
        self._set_state(self.Running)
        self.started.emit()
        
    def stop(self):
        self.execute("proc_buryall")
        self._set_state(self.NotRunning)
        self.finished.emit(0)

    def platform(self):
        return self.execute("platform")

    def session(self):
        session = Session(self)
        self.sessions[session.sid()] = session
        return session

class LocalBackend(Backend):
    def __init__(self, parent = None):
        Backend.__init__(self, 'local', parent)
        self.process = QtCore.QProcess(self)
        self.protocol = 'ipc' if sys.platform.startswith('linux') else 'tcp'
        self.address = None

    def start(self):
        self._set_state(self.Starting)
        args = [LOCAL_BACKEND_SCRIPT, "-t", self.protocol]
        if self.address is not None:
            args.extend(["-a", self.address])

        self.process.readyReadStandardError.connect(self.backend_start_readyReadStandardError)
        self.process.readyReadStandardOutput.connect(self.backend_start_readyReadStandardOutput)
        self.process.start(sys.executable, args)

    def stop(self):
        Backend.stop(self)
        os.kill(self.process.pid(), signal.SIGTERM)
        self.process.waitForFinished()

    #------------ Process Start Signal
    def backend_start_readyReadStandardOutput(self):
        connectionString = encoding.from_fs(self.process.readAllStandardOutput()).splitlines()[1]
        self.startMultiplexer(connectionString)
        self.execute("setup_channel", self.startNotifier())
        self.process.readyReadStandardError.disconnect(self.backend_start_readyReadStandardError)
        self.process.readyReadStandardOutput.disconnect(self.backend_start_readyReadStandardOutput)
        self.process.readyReadStandardError.connect(self.backend_readyReadStandardError)
        self.process.readyReadStandardOutput.connect(self.backend_readyReadStandardOutput)
        self.process.finished.connect(self.backend_finished)
        self.process.error.connect(self.backend_error)
        self._set_state(self.Running)
        self.started.emit()

    def backend_start_readyReadStandardError(self):
        print(encoding.from_fs(self.process.readAllStandardError()))
        self.process.readyReadStandardError.disconnect(self.backend_start_readyReadStandardError)
        self.process.readyReadStandardOutput.disconnect(self.backend_start_readyReadStandardOutput)
        self.error.emit(self.ReadError)
        self.finished.emit(-1)

    #------------ Process Normal Signals
    def backend_finished(self):
        self.finished.emit(0)

    def backend_error(self, error):
        self.error.emit(error)

    def backend_readyReadStandardError(self):
        print(encoding.from_fs(self.process.readAllStandardError()))
    
    def backend_readyReadStandardOutput(self):
        print(encoding.from_fs(self.process.readAllStandardOutput()))
    
    # -------------- set backend process attrs and settings
    def setWorkingDirectory(self, directory):
        self.process.setWorkingDirectory(directory)

    def setProtocol(self, protocol):
        self.protocol = protocol

    def setAddress(self, address):
        self.address = address


class BackendManager(QtCore.QObject):
    def __init__(self, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.backends = []
    
    def stopAll(self):
        for backend in self.backends:
            if backend.state() == Backend.Running:
                backend.stop()
    
    def backend(self, name, address):
        backend = Backend(name, parent = self)
        backend.startMultiplexer(address)
        backend.execute("setup_channel", backend.startNotifier())
        self.backends.append(backend)
        return backend
        
    def localBackend(self, workingDirectory = None, protocol = None, address = None):
        backend = LocalBackend(self)
        
        if protocol is not None:
            backend.setProtocol(protocol)
        
        if workingDirectory:
            backend.setWorkingDirectory(workingDirectory)
            
        if address is not None:
            backend.setAddress(address)

        self.backends.append(backend)
        return backend
