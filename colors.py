#! /usr/bin/env python

# Display the colors available in a terminal.

print "16-color mode:"
for color in range(0, 16):
    print "\033[1;49m0\033[m",
    for i in range(0, 20):
        print "\033[%s;%sm%02s-%02s\033[m" % (str(i), str(color + 30), str(i), str(color)),
    print

# Programs like ls and vim use the first 16 colors of the 256-color palette.
#print "256-color mode:"
#for color in range(0, 256) :
#    for i in range(0, 3) :
#        print "\033[38;5;%sm%03s\033[m" % (str(color), str(color)),
#    print