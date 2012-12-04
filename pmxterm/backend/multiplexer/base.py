#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time

class Multiplexer(object):
    TERMINAL_CLASS = None
    def __init__(self, command="/bin/bash", timeout=60*60*24):
        self.sessions = {}
        self.default_command = command
        self.timeout = timeout

    def create_session(self, sid, width, height):
        self.sessions[sid] = {
            'state': 'unborn',
            'term': TERMINAL_CLASS(width, height),
            'time': time.time(),
            'width':	width,
            'height':	height,
            'changed': None
            'pid': None
        }
        return self.sessions[sid]
                
    def get_session(self, sid):
        return session

    def get_or_create_session(self, sid):
        return session, created

    def remove_session(self, sid):
        del self.sessions[sid]

    def platform(self):
        return sys.platform

    def is_session_alive(self, sid):
        return self.sessions.get(sid, {}).get('state') == 'alive'

    def last_session_change(self, sid):
        return self.sessions.get(sid, {}).get("changed")

    def session_pid(self, sid):
        return self.sessions.get(sid, {}).get("pid")