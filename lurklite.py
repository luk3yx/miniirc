#!/usr/bin/python3
#
# lurk lite: A "lightweight™" version of lurk.
#

from ast import literal_eval
from urllib.parse import quote as web_quote
from urllib.request import urlopen
import os, miniirc

# The environment variable prefix
environ_template = 'LURKLITE_{}'

# Create default variables.
defaults = {
    'ip':           'xeroxirc.net',
    'port':         6697,
    'nick':         'lurklite',
    'ident':        'lurklite',
    'channels':     '#lurk',
    'prefix':       ',',
    'identity':     ' ',
    'realname':     'A lightweight testing version of lurk.',
    'ignored':      'lurk',
    'admins':       'unaffiliated/luk3yx,xIRC/ServerAdmin/luk3yx',
    'connect_modes': '+i',
    'tempcmd_file': 'tempcmds.db',
    'tempcmd_url':  'https://lurk-tempcmds.appspot.com/yaycmd/{}'
}

# Load a dict-based database
def get_database(path, obj = dict):
    try:
        with open(path) as f:
            n = literal_eval(f.read())
    except:
        n = None

    if type(n) != obj:
        n = obj()

    return n

# Run a tempcmd
def run_tempcmd(irc, channel, hostmask, cmd, args, allow_aliases = True, *,
  pre = ''):
    db   = get_database(tempcmd_file)
    code = db.get(cmd)
    if not code:
        cmd = 'µ' + cmd
        code = db.get(cmd)
        if not code:
            return

    nick = hostmask[0]
    if code.startswith('.') and allow_aliases and ' ' not in code: # Command aliases
        return run_tempcmd(irc, channel, hostmask, code[1:], args,
            allow_aliases = False, pre = pre)
    if code.startswith('lisp('): # LISP code
        code = code[4:]
        code = "__builtins__['lisp'] = load('https://raw.githubusercontent.com/norvig/pytudes/master/py/lispy.py'); lisp.global_env['read'] = lambda : lisp.read(lisp.InPort(lisp.StringIO.StringIO({1}))); lisp.global_env['getarg'] = {0}.__getitem__; lisp.global_env['getargs'] = lambda : {1}; r = lisp.eval(lisp.parse({2})); print(r) if r != None else ''".format(tuple(args), repr(' '.join(args)), repr(code))
        code = tempcmd_url.format(web_quote(code))
    if code.startswith('lambda'): # Python code
        code = 'from __future__ import division, generators, nested_scopes,'   \
            'print_function, unicode_literals; __builtins__[\'chr\'] = unichr' \
            '; print(({}){})'.format(code, tuple(args))
        code = tempcmd_url.format(web_quote(code))
    elif code.startswith('function('): # node.js code
        code = web_quote('({}){}'.format(code, tuple(args)))
        code = ('https://untitled-2khw8qubudu1.runkit.sh/?code={}&nick={}'
            '&channel={}&host={}').format(code, web_quote(nick),
            web_quote(channel), web_quote(hostmask[-1]))
    if code.startswith('https://'): # URL code
        try:
            code = code.format(*[web_quote(a) for a in args],
                args = web_quote(' '.join(args)), nick = nick)
            result = urlopen(code).read().decode('utf-8')
            if len(result) > 400:
                raise TypeError()
            elif result.startswith('TypeError: <lambda>() takes '):
                result = 'Invalid syntax! This command takes ' + \
                    result[28:-1] + '.'
        except Exception as e:
            irc.debug('Error running tempcmd:', repr(e), cmd)
            result = 'Invalid syntax!'
    else: # String-formatted code
        try:
            _a = ' '.join(args)
            result = code.format(*args, nick = nick, sender = channel,
                host = hostmask[2], hostmask = '{}!{}@{}'.format(*hostmask),
                args = _a, ARGS = _a.upper(), NICK = nick.upper())
        except Exception as e:
            irc.debug('Error running tempcmd:', repr(e), cmd)
            code   = ''
            result = 'Invalid syntax!'
        if code.startswith('*') and code.endswith('*') and len(result) > 2:
            return irc.me(channel, '\u200b' + result[1:-1])
    irc.msg(channel, pre + nick + ':', result)

# The PRIVMSG handler
@miniirc.Handler('PRIVMSG')
def handle_privmsg(irc, hostmask, args):
    channel = args[0]
    args = args[-1][1:].split(' ')

    # [off] handling
    pre = ''
    if args[0].startswith('[off]'):
        pre = '[off] '
        args[0] = args[0][5:]
        if args[0] == '':
            del args[0]
        if len(args) < 1:
            return

    # MT nick handling
    nick = hostmask[0]
    if args[0].startswith('<') and args[0].endswith('>') and \
       args[0][1].isalnum():
        nick = '{}@{}'.format(args[0][1:-1], nick)

        del args[0]
        if len(args) > 0 and args[0] == '':
            del args[0]

    # Ignores
    if nick in ignored or hostmask[2] in ignored:
        return

    if len(args) <= 0:
        args.append('')

    cmd = args[0].lower()

    # Unprefixed commands here
    if cmd.startswith('yay'):
        irc.msg(channel, pre + 'Yay!')
    elif cmd.startswith('ouch'):
        irc.msg(channel, pre + 'Ouch.')
    elif cmd.startswith(irc.nick.lower() + '!'):
        irc.msg(channel, pre + nick + '!')
    elif cmd.startswith(prefix):
        # Prefixed commands
        cmd = cmd[len(prefix):]

        del args[0]

        # Admin-only commands
        if hostmask[2] in admins:
            if cmd in ('join', 'part', 'quit', 'privmsg'):
                return irc.quote(cmd.upper(), *args)

        # Non-admin commands
        if cmd == 'yay':
            irc.msg(channel, pre + 'Yay!')
        elif len(cmd) > 0:
            # Tempcmd parser
            run_tempcmd(irc, channel, (nick, hostmask[1], hostmask[2]), cmd,
                args, pre = pre)


# A environment-or-default function
def pref(name):
    n = environ_template.format(name.upper())
    e = os.environ.get(n)
    if e:
        del os.environ[n]
    return e or defaults.get(name) or '???'

# Start the socket
_irc = miniirc.IRC(
    pref('ip'), pref('port'), pref('nick'), pref('channels').split(','),
    ident = pref('ident'), realname = pref('realname'),
    ns_identity = pref('identity'), connect_modes = pref('connect_modes'),
    debug = pref('debug') == 'DEBUG'
)

# Other variables
ignored      = set(pref('ignored').split(','))
admins       = set(pref('admins').split(','))
tempcmd_file = pref('tempcmd_file')
tempcmd_url  = pref('tempcmd_url')
prefix       = pref('prefix')
