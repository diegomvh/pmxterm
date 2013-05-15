#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import zmq
import time
import json
import ast
import signal

from PyQt4 import QtCore

from .zeromqt import ZmqSocket
from .session import Session

LOCAL_BACKEND_SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "main.py"))


class Backend(QtCore.QObject):
    started = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(int)
    
    def __init__(self, name, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.name = name
        self.sessions = {}
        

    #------------ Sockets
    def startMultiplexer(self, address):
        self.multiplexer = ZmqSocket(zmq.REQ, self)
        self.multiplexer.connect(address)
    
    def startNotifier(self, address):
        self.notifier = ZmqSocket(zmq.SUB, self)
        self.notifier.readyRead.connect(self.notifier_readyRead)
        self.notifier.subscribe(b"") #All
        self.notifier.connect(address)
        
    def execute(self, command, args = None):
        if args is None:
            args = []
        self.multiplexer.send_pyobj({"command": command, "args": args})
        return self.multiplexer.recv_pyobj()

    def notifier_readyRead(self):
        message = self.notifier.recv_multipart()
        if len(message) % 2 == 0:
            for sid, payload in [message[x: x + 2] for x in xrange(0, len(message), 2)]:
                if sid in self.sessions:
                    try:
                        self.sessions[sid].screenReady.emit(ast.literal_eval(payload))
                    except:
                        self.sessions[sid].readyRead.emit()
        else:
            print("algo esta mal con %s" % data)
        
            
    def start(self):
        self.started.emit()
        
    def close(self):
        self.execute("proc_buryall")
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
        self.ready = False


    def start(self):
        args = [LOCAL_BACKEND_SCRIPT, "-t", self.protocol]
        if self.address is not None:
            args.extend(["-a", self.address])

        self.process.readyReadStandardError.connect(self.backend_start_readyReadStandardError)
        self.process.readyReadStandardOutput.connect(self.backend_start_readyReadStandardOutput)
        self.process.start(sys.executable, args)


    def close(self):
        Backend.close(self)
        os.kill(self.process.pid(), signal.SIGTERM)
        self.process.waitForFinished()

        
    #------------ Process Start Signal
    def backend_start_readyReadStandardOutput(self):
        connectionString = str(self.process.readAllStandardOutput(), "utf-8").splitlines()[-1]
        data = ast.literal_eval(connectionString)
        self.startMultiplexer(data["multiplexer"])
        self.startNotifier(data["notifier"])
        self.process.readyReadStandardError.disconnect(self.backend_start_readyReadStandardError)
        self.process.readyReadStandardOutput.disconnect(self.backend_start_readyReadStandardOutput)
        self.process.readyReadStandardError.connect(self.backend_readyReadStandardError)
        self.process.readyReadStandardOutput.connect(self.backend_readyReadStandardOutput)
        self.process.finished.connect(self.backend_finished)
        self.started.emit()


    def backend_start_readyReadStandardError(self):
        print(str(self.process.readAllStandardError(), "utf-8"))
        self.process.readyReadStandardError.disconnect(self.backend_start_readyReadStandardError)
        self.process.readyReadStandardOutput.disconnect(self.backend_start_readyReadStandardOutput)
        self.finished.emit(-1)


    #------------ Process Normal Signals
    def backend_finished(self):
        self.finished.emit(0)


    def backend_readyReadStandardError(self):
        print(str(self.process.readAllStandardError(), "utf-8"))

        
    def backend_readyReadStandardOutput(self):
        print(str(self.process.readAllStandardOutput(), "utf-8"))
        
    
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
    
    def closeAll(self):
        for backend in self.backends:
            backend.close()
    
    def backend(self, name, connectionString):
        data = ast.literal_eval(connectionString)
        backend = Backend(name, parent = self)
        backend.startMultiplexer(data["multiplexer"])
        backend.startNotifier(data["notifier"])
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
