#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

__doc__ = """Simple terminal/console widget for PyQt4 and PyQt5 with vt100 support.
This terminal is based on the source of pyqterm from Henning Schroeder (henning.schroeder@gmail.com) 
https://bitbucket.org/henning/pyqtermwidget
"""

if __name__ == "__main__":
    setup(
        name = "pyqterm",
        version = "0.2",
        description = "Simple terminal/console widget for PyQt4 and PyQt5 with vt100 support",
        author="Diego van Haaster",
        author_email="diegomvh@gmail.com",
        url="https://github.com&",
        zip_safe=True,
        license="GPL2",
        keywords="pyqt pyqt4 pyqt5 console terminal shell vt100 widget",
        packages = find_packages(),
        install_requires = [ 'pyzmq' ]
    )
