#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import zmq
import argparse
from multiprocessing import Process, Queue

from multiplexer import Multiplexer

# ===========
# = Workers =
# ===========
def worker_multiplexer(queue, addr):
    multiplexer = Multiplexer(queue)
    
    context = zmq.Context()
    zrep = context.socket(zmq.REP)
    
    if addr.endswith(":0"):
        addr = addr[:-2]
        addr = "%s:%d" % (addr, zrep.bind_to_random_port(addr))
    else:
        zrep.bind(addr)

    queue.put(addr)

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
    
    if addr.endswith(":0"):
        addr = addr[:-2]
        addr = "%s:%d" % (addr, zpub.bind_to_random_port(addr))
    else:
        zpub.bind(addr)
    
    queue.put(addr)
    
    while True:
        data = queue.get()
        zpub.send(data)


# ==============
# = Parse args =
# ==============
DESCRIPTION = 'pmxterm backend.'

# Dictionary of command-line help messages
HELP = {
    'rep': "address for REQ/REP zmq socket",
    'pub': "address for PUB/SUB zmq socket"
}

def parse():
    """Creates argument parser for parsing command-line arguments. Returns parsed
    arguments in a form of a namespace.
    """
    # Setting up argument parses
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('-r', metavar='<rep>', dest='rep', type=str, default="ipc:///tmp/pmxrep", help=HELP['rep'])
    parser.add_argument('-p', metavar='<pub>', dest='pub', type=str, default="ipc:///tmp/pmxpub", help=HELP['pub'])
    # Parsing and hacks
    args = parser.parse_args()
    return args

def main(rep_addr, pub_addr):
    queue = Queue()
    
    # Start the multiplexer
    mproc = Process(target=worker_multiplexer, args=(queue, rep_addr))
    mproc.start()
    
    # Start the notifier
    nproc = Process(target=worker_notifier, args=(queue, pub_addr))
    nproc.start()
    
    a1, a2 = queue.get(), queue.get()
    print a1, a2

if __name__ == "__main__":
    args = parse()
    main(args.rep, args.pub)
