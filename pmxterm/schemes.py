#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4 import QtGui

from colortrans import SHORT2RGB_DICT

class ColorSchema(object):
    def __init__(self, name, settings):
        self.name = name
        self.colormap = dict(map(lambda (key, rgb): (key, QtGui.QColor(rgb)), settings.iteritems()))


    def background(self, intensive = False):
        return self.colormap[intensive and 11 or 1]
        
    def foreground(self, intensive = False):
        return self.colormap[intensive and 10 or 0]
    
    def color(self, index, intensive = False):
        if isinstance(index, int):
            if intensive:
                index += 8
            if index + (intensive and 4 or 2) in self.colormap:
                return self.colormap[index + (intensive and 4 or 2)]
            return QtGui.QColor("#" + SHORT2RGB_DICT[index])
            
vim = ColorSchema("vim",{
     0:"#000000",
     1:"#FFFFFF",
     2:"#000000",
     3:"#C00000",
     4:"#008000",
     5:"#808000",
     6:"#0000C0",
     7:"#C000C0",
     8:"#008080",
     9:"#C0C0C0",
    10:"#4D4D4D",
    11:"#FFFFFF",
    12:"#808080",
    13:"#FF6060",
    14:"#00FF00",
    15:"#FFFF00",
    16:"#8080FF",
    17:"#FF40FF",
    18:"#00FFFF",
    19:"#FFFFFF",
})

linux = ColorSchema("linux",{
     0:"#b2b2b2",
     1:"#000000",
     2:"#000000",
     3:"#b21818",
     4:"#18b218",
     5:"#b26818",
     6:"#1818b2",
     7:"#b218b2",
     8:"#18b2b2",
     9:"#b2b2b2",
    10:"#ffffff",
    11:"#686868",
    12:"#686868",
    13:"#ff5454",
    14:"#54ff54",
    15:"#ffff54",
    16:"#5454ff",
    17:"#ff54ff",
    18:"#54ffff",
    19:"#ffffff",
})
