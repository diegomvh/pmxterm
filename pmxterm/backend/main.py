#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import zmq
import argparse
import tempfile
import re
import json
import stat
import signal
from urlparse import urlparse

from multiprocessing import Process, Queue
from multiplexer import Multiplexer
    
from utils import get_pmxterm_dir

# ===========
# = Workers =
# ===========
def worker_multiplexer(queue, notifier, addr):
    multiplexer = Multiplexer(notifier)
    
    context = zmq.Context()
    zrep = context.socket(zmq.REP)
    
    if addr.scheme in ["tcp", "udp"]:
        port = None
        try:
            port = addr.port
        except:
            pass
        if not port:
            addr = "%s://%s" % (addr.scheme, addr.netloc)
            port = zrep.bind_to_random_port(addr)
            addr = "%s:%d" % (addr, port)
        else:
	       addr = "%s://%s" % (addr.scheme, addr.netloc)
	       zrep.bind(addr)
    else:
        addr = "%s://%s" % (addr.scheme, addr.path)
        zrep.bind(addr)
    queue.put(("shell_address", addr))
    
    while True:
        pycmd = zrep.recv_pyobj()
        method = getattr(multiplexer, pycmd["command"], None)
        if method is not None:
            zrep.send_pyobj(method(*pycmd["args"]))
        else:
            zrep.send_pyobj(None)


def worker_notifier(queue, addr):
    context = zmq.Context()
    zpub = context.socket(zmq.PUB)

    if addr.scheme in ["tcp", "udp"]:
        port = None
        try:
            port = addr.port
        except:
            pass
        if not port:
            addr = "%s://%s" % (addr.scheme, addr.netloc)
            port = zpub.bind_to_random_port(addr)
            addr = "%s:%d" % (addr, port)
        else:
	       addr = "%s://%s" % (addr.scheme, addr.netloc)
	       zpub.bind(addr)
    else:
        addr = "%s://%s" % (addr.scheme, addr.path)
        zpub.bind(addr)
    queue.put(("pub_address", addr))
    
    while True:
        data = queue.get()
        zpub.send(data)


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
    elif args.type == "tcp":
        address = args.address if args.address is not None else '127.0.0.1'
        pub_addr = "tcp://%s" % address
        rep_addr = "tcp://%s" % address
        if args.pub_port is not None:
            pub_addr += ":%i" % args.pub_port
        if args.rep_port is not None:
            rep_addr += ":%i" % args.rep_port
    return urlparse(rep_addr), urlparse(pub_addr)

if __name__ == "__main__":
    rep_addr, pub_addr = get_addresses(parse_arguments())
    
    if not rep_addr or not pub_addr:
        print "Address error, please read help"
        sys.exit(-1)

    queue_multiplexer = Queue()
    queue_notifier = Queue()
    
    # Start the multiplexer
    mproc = Process(target=worker_multiplexer, args=(queue_multiplexer, queue_notifier, rep_addr))
    mproc.start()
    
    # Start the notifier
    nproc = Process(target=worker_notifier, args=(queue_notifier, pub_addr))
    nproc.start()
    
    info = dict([queue_multiplexer.get(), queue_notifier.get()])
    descriptor, name = tempfile.mkstemp(prefix="backend-", suffix=".json", dir = get_pmxterm_dir(), text = True)
    tempFile = os.fdopen(descriptor, 'w+')
    tempFile.write(json.dumps(info))
    tempFile.close()
    os.chmod(name, stat.S_IREAD | stat.S_IWRITE)
    
    print "To connect another client to this backend, use:"
    print name
    print ";".join(map(lambda socket: "%s=%s" % socket, info.items()))
    sys.stdout.flush()
    
    def signal_handler(signal, frame):
        nproc.terminate()
        mproc.terminate()
        os.unlink(tempFile)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
