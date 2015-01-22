#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import stat
import signal
import tempfile
import constants
import socket
import json

from multiprocessing import Process, Queue
from multiprocessing.reduction import recv_handle, send_handle
from multiplexer import Multiplexer

procs = set()
shutdown = False

# ===========
# = Workers =
# ===========
def worker_multiplexer(queue_multiplexer, queue_notifier):
    global shutdown
    
    multiplexer = Multiplexer(queue_notifier)    
    should_continue = True
    while not shutdown and should_continue:
        pycmd = queue_multiplexer.get()
        method = getattr(multiplexer, pycmd["command"], None)
        if method:
            queue_multiplexer.put(method(*pycmd["args"]))
        should_continue = pycmd["command"] != "proc_buryall"
        
def worker_notifier(queue_notifier):
    global shutdown
    
    channels = {}
    should_continue = True
    while not shutdown and should_continue:
        message = queue_notifier.get()
        if message['cmd'] == 'send':
            channel = channels[message['channel']]
            channel.send(json.dumps(message['payload']).encode(constants.FS_ENCODING))
            channel.recv(4096)
        elif message['cmd'] == 'buried_all':
            for channel in channels.values():
                channel.close()
            should_continue = False
        elif message['cmd'] == 'setup_channel':
            s = socket.socket(socket.AF_UNIX)
            s.connect(message['address'])
            channels[message['id']] = s
            
def worker_client(queue_multiplexer, queue_notifier, sock):
    global shutdown

    _id = sock.fileno()
    should_continue = True
    while not shutdown and should_continue:
        data = sock.recv(4096)
        print(data)
        pycmd = json.loads(data.decode(constants.FS_ENCODING))
        if pycmd["command"] == "setup_channel":
            queue_notifier.put({'cmd': 'setup_channel', 'id': _id, 'address': pycmd["args"]})
            result = True
        else:
            pycmd["args"].insert(0, _id)
            queue_multiplexer.put(pycmd)
            result = queue_multiplexer.get()
        sock.send(json.dumps(result).encode(constants.FS_ENCODING))
        should_continue = pycmd["command"] != "proc_buryall"

# ==============
# = Parse args =
# ==============
DESCRIPTION = 'pmxterm backend.'

# Dictionary of command-line help messages
HELP = {
    'rep_port': 'Port number of the request/responce socket',
    'pub_port': 'Port number of the publisher socket',
    'type': 'The zmq socket type "ipc", "tcp"',
    'address': 'TCP and UDP bind address'
}

def parse_arguments():
    """Creates argument parser for parsing command-line arguments. Returns parsed
    arguments in a form of a namespace.
    """
    # Setting up argument parses
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('-t', metavar='<type>', dest='type', type=str, default="tcp", help=HELP['type'])
    parser.add_argument('-a', metavar='<address>', dest='address', type=str, help=HELP['address'])
    parser.add_argument('-pp', metavar='<pub_port>', dest='pub_port', type=int, help=HELP['pub_port'])
    parser.add_argument('-rp', metavar='<rep_port>', dest='rep_port', type=int, help=HELP['rep_port'])
    args = parser.parse_args()
    if args.type == "ipc" and args.address is not None:
        parser.print_help()
        sys.exit()
    return args

def get_addresses(args):
    pub_addr = rep_addr = None
    if args.type == "ipc":
        pub_addr = "ipc://%s" % tempfile.mkstemp(prefix="pmx")[1]
        rep_addr = "ipc://%s" % tempfile.mkstemp(prefix="pmx")[1]
        return (rep_addr, False), (pub_addr, False)
    elif args.type == "tcp":
        address = args.address if args.address is not None else '127.0.0.1'
        pub_addr = "tcp://%s" % address
        rep_addr = "tcp://%s" % address
        pub_port = rep_port = True
        if args.pub_port is not None:
            pub_port = False
            pub_addr += ":%i" % args.pub_port
        if args.rep_port is not None:
            rep_port = False
            rep_addr += ":%i" % args.rep_port
        return (rep_addr, rep_port), (pub_addr, pub_port)
    return None, None

# Install singla handler
def signal_handler(signum, frame):
    global shutdown
    shutdown = True
    for proc in procs:
        proc.terminate()
        proc.join()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
if sys.platform == "win32":
    signal.signal(signal.SIGBREAK, signal_handler)

if __name__ == "__main__":
    #rep_addr, pub_addr = get_addresses(parse_arguments())

    #if not rep_addr or not pub_addr:
    #    print("Address error, please read help")
    #    sys.exit(-1)

    address = tempfile.mktemp(prefix="pmx")
    server = socket.socket(socket.AF_UNIX)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    server.bind(address)
    server.listen(5)

    print("To connect a client to this backend, use:")
    print(address)
    sys.stdout.flush()
    
    queue_multiplexer = Queue()
    queue_notifier = Queue()
    
    # Start the multiplexer
    mproc = Process(target=worker_multiplexer,
        args=(queue_multiplexer, queue_notifier), name="multiplexer"
    )
    mproc.start()
    procs.add(mproc)

    # Start the notifier
    nproc = Process(target=worker_notifier,
        args=(queue_notifier, ), name="notifier"
    )
    nproc.start()
    procs.add(nproc)
    while not shutdown:
        conn, address = server.accept()

        # Start the notifier
        cproc = Process(target=worker_client, 
            args=(queue_multiplexer, queue_notifier, conn), name="client"
        )
        cproc.start()
        procs.add(cproc)
        
        conn.close()