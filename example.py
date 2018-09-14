#!/usr/bin/python3

#
# Example miniirc-based bot
#
# © 2018 by luk3yx
#

import os, socket, sys, atexit
from miniirc import IRC

# Variables
nick     = 'miniirc-test' + str(hash('.'))[1:4] # Make a unique(-ish) nickname
ident    = nick
realname = 'Example miniirc bot - https://gitlab.com/luk3yx/stdinbot'
identity = None
# identity = '<username> <password>'
debug    = False
channels = ['#lurk']
prefix   = '`'

ip = 'xeroxirc.net'
port = 6697

# Welcome!
print('Welcome to {}!'.format(nick), file=sys.stderr)
irc = IRC(ip, port, nick, channels, ident = ident, realname = realname,
    ns_identity = identity, debug = debug, auto_connect = False)

# Handle normal messages
# This could probably be better than a large if/else statement.
@irc.Handler('PRIVMSG')
def handle_privmsg(irc, hostmask, args):
    channel = args[0]
    args = args[-1][1:].split(' ')
    cmd = args[0].lower()
    # Unprefixed commands here
    if cmd.startswith("meep"):
        irc.msg(channel, "Meep™!")
    elif cmd.startswith(prefix):
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
            irc.msg(channel, 'I am {}, an example miniirc bot.'.format(irc.nick))
        elif print_cmds and cmd != '':
            print(' '.join(args)[1:])

# Connect
irc.connect()
