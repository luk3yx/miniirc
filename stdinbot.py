#!/usr/bin/python3

#
# stdinbot - Read text from stdin and send it to an IRC channel
#
# © 2018 by luk3yx
#

import os, socket, sys, atexit
from miniirc import IRC

# Variables
nick = 'stdinbot'
ident = nick
realname = 'Reads stdin from a terminal'
identity = False
# identity = '<username> <password>'
print_cmds = False

channels = ['#lurk']
debug    = False

ip = 'xeroxirc.net'
port = 6697

# Welcome!
print("Welcome to stdinbot!", file=sys.stderr)
irc = IRC(ip, port, nick, channels, ident = ident, realname = realname,
    ns_identity = identity, debug = debug, auto_connect = False)

# Read stdin
@irc.Handler('001')
def handle_stdin(irc, hostmask, args):
    qmsg = 'I reached the end of my file, therefore my life™.'
    while True:
        try:
            line = '\u200b' + input().replace('\r', '').replace('\n', '  ')
        except:
            line = '\x04'
        if line == '\x04':
            irc.disconnect(qmsg)
            return os._exit(0)
        irc.msg(channels[0], line)

irc.connect()
