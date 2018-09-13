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

connected = False

ip = 'xeroxirc.net'
port = 6697

# Welcome!
print("Welcome to stdinbot!", file=sys.stderr)
irc = IRC(ip, port, nick, channels, ident = ident, realname = realname,
    ns_identity = identity, debug = True, auto_connect = False)

# Handle normal messages
@irc.Handler('PRIVMSG')
def handle_privmsg(irc, hostmask, args):
    channel = args[0]
    args = args[-1][1:].split(' ')
    cmd = args[0].lower()
    # Unprefixed commands here
    if cmd.startswith("meep"):
        irc.msg(channel, "Meep™!")
    elif cmd.startswith('<'):
        # Prefixed commands
        cmd = cmd[1:]
        if cmd == 'yay':
            irc.msg(channel, "\u200bYay!")
        elif cmd == 'rev':
            if len(args) > 1:
                irc.msg(channel, "{}: {}".format(hostmask[0], ' '.join(args[1:])[::-1]))
            else:
                irc.msg(channel, "Invalid syntax! Syntax: <rev <string>")
        elif cmd == 'about':
            irc.msg(channel, 'I am stdinbot, a simple IRC bot that reads text from stdin and prints it to a channel.')
        elif print_cmds and cmd != '':
            print(' '.join(args)[1:])

# Read stdin
@irc.Handler('001')
def handle_stdin(irc, hostmask, args):
    qmsg = 'QUIT :I reached the end of my file, therefore my life™.'
    while True:
        try:
            line = '\u200b' + input().replace('\r', '').replace('\n', '  ')
        except:
            line = '\x04'
        if line == '\x04':
            irc.quote(qmsg)
            return os._exit(0)
        irc.msg(channels[0], line)

irc.connect()
