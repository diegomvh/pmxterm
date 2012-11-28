#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This code is based on the source of pyqterm from Henning Schroeder (henning.schroeder@gmail.com)
# License: GPL2

import sys
import os
import threading
import time
import signal
import struct
import select
import subprocess
import array
from multiprocessing import Queue

from vt100 import Terminal

class WinTerminal(Terminal):
    def __init__(self, w, h):
        Terminal.__init__(self, w, h)
        self.vt100_mode_lfnewline = False
    
def synchronized(func):
    def wrapper(self, *args, **kwargs):
        try:
            self.lock.acquire()
        except AttributeError:
            self.lock = threading.RLock()
            self.lock.acquire()
        try:
            result = func(self, *args, **kwargs)
        finally:
            self.lock.release()
        return result
    return wrapper

class Multiplexer(object):
    def __init__(self, queue, timeout = 60*60*24):
        # Session
        self.session = {}
        self.queue = queue
        self.timeout = timeout

        # Supervisor
        self.signal_stop = 0
        self.thread = threading.Thread(target = self.proc_thread)
        self.thread.start()

    def stop(self):
        # Stop supervisor thread
        self.signal_stop = 1
        self.thread.join()

    def proc_resize(self, sid, w, h):
        self.session[sid]['term'].set_size(w, h)
        self.session[sid]['w'] = w
        self.session[sid]['h'] = h


    @synchronized
    def proc_keepalive(self, sid, w, h, command = None):
        if not sid in self.session:
            # Start a new session
            self.session[sid] = {
                'state':'unborn',
                'term':	WinTerminal(w, h),
                'time':	time.time(),
                'w':	w,
                'h':	h}
            return self.__proc_spawn(sid, command)
        elif self.session[sid]['state'] == 'alive':
            self.session[sid]['time'] = time.time()
            # Update terminal size
            if self.session[sid]['w'] != w or self.session[sid]['h'] != h:
                self.proc_resize(sid, w, h)
            return True
        else:
            return False

    def __proc_spawn(self, sid, command):
        # Session
        self.session[sid]['state'] = 'alive'
        w, h = self.session[sid]['w'], self.session[sid]['h']
        process = subprocess.Popen(command, shell = True, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        def enqueue_output(output, queue):
            while True:
                data = output.read(1)
                queue.put(data)
        queue = Queue()
        thread = threading.Thread(target=enqueue_output, args=(process.stdout, queue))
        thread.daemon = True
        thread.start()
        self.session[sid]['process'] = process
        self.session[sid]['thread'] = thread
        self.session[sid]['queue'] = queue
        self.session[sid]['pid'] = process.pid
        self.proc_resize(sid, w, h)
        return True


    def proc_waitfordeath(self, sid):
        try:
            os.close(self.session[sid]['fd'])
        except (KeyError, IOError, OSError):
            pass
        if sid in self.session:
            if 'fd' in self.session[sid]:
                del self.session[sid]['fd']
        try:
            os.waitpid(self.session[sid]['pid'], 0)
        except (KeyError, IOError, OSError):
            pass
        if sid in self.session:
            if 'pid' in self.session[sid]:
                del self.session[sid]['pid']
        self.session[sid]['state'] = 'dead'
        return True


    def proc_bury(self, sid):
        if self.session[sid]['state'] == 'alive':
            try:
                os.kill(self.session[sid]['pid'], signal.SIGTERM)
            except (IOError, OSError):
                pass
        self.proc_waitfordeath(sid)
        if sid in self.session:
            del self.session[sid]
        return True


    @synchronized
    def proc_buryall(self):
        for sid in self.session.keys():
            self.proc_bury(sid)


    @synchronized
    def proc_read(self, sid):
        """
        Read from process
        """
        if sid not in self.session:
            return False
        elif self.session[sid]['state'] != 'alive':
            return False
        queue = self.session[sid]['queue']
        term = self.session[sid]['term']
        data = ""
        try:
            while True:
                data += queue.get_nowait()
        except Exception, ex:
            pass
        if data:
            term.write(data)
        return bool(data)


    @synchronized
    def proc_write(self, sid, d):
        """
        Write to process
        """
        if sid not in self.session:
            return False
        elif self.session[sid]['state'] != 'alive':
            return False
        try:
            term = self.session[sid]['term']
            process = self.session[sid]['process']
            process.stdin.write(term.pipe(d))
            term.write(d)
            self.queue.put(sid)
            process.stdin.flush()
        except (IOError, OSError):
            return False
        return True


    @synchronized
    def proc_dump(self, sid):
        """
        Dump terminal output
        """
        if sid not in self.session:
            return False
        return self.session[sid]['term'].dump()


    @synchronized
    def proc_getalive(self):
        """
        Get alive sessions, bury timed out ones
        """
        sids = []
        now = time.time()
        for sid in self.session.keys():
            then = self.session[sid]['time']
            if (now - then) > self.timeout:
                self.proc_bury(sid)
            elif 'queue' in self.session[sid] and self.session[sid]['state'] == 'alive':
                sids.append(sid)
        return sids

    def proc_thread(self):
        """
        Supervisor thread
        """
        while not self.signal_stop:
            for sid in self.proc_getalive():
                if self.proc_read(sid):
                    self.session[sid]["changed"] = time.time()
                    self.queue.put(sid)
                    time.sleep(0.002)
        self.proc_buryall()

    def is_session_alive(self, sid):
        return self.session.get(sid, {}).get('state') == 'alive'
        
    def session_pid(self, sid):
        return self.session.get(sid, {}).get("pid", None)
        
    def last_session_change(self, sid):
        return self.session.get(sid, {}).get("changed", None)
