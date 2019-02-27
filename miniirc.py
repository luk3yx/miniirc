#!/usr/bin/python3
#
# miniirc - A small-ish backwards-compatible IRC framework.
#
# © 2018 by luk3yx and other developers of miniirc.
#

import atexit, threading, socket, ssl, sys
from time import sleep

# The version string and tuple
ver     = (1,0,9)
version = 'miniirc IRC framework v1.0.9'

# __all__ and _default_caps
__all__ = ['Handler', 'IRC']
_default_caps = {'account-tag', 'cap-notify', 'chghost',
    'draft/message-tags-0.2', 'invite-notify', 'message-tags', 'server-time',
    'sts'}

# Get the certificate list.
try:
    from certifi import where as get_ca_certs
except ImportError:
    get_ca_certs = lambda : None

# Create global handlers
_global_handlers = {}

def _add_handler(handlers, events, ircv3):
    def _finish_handler(func):
        for event in events:
            event = str(event).upper()
            if event not in handlers:
                handlers[event] = []
            if func not in handlers[event]:
                handlers[event].append(func)
        if ircv3:
            func.miniirc_ircv3 = True
        return func

    return _finish_handler

def Handler(*events, ircv3 = False):
    return _add_handler(_global_handlers, events, ircv3)

# Create the IRCv2/3 parser
ircv3_tag_escapes = {':': ';', 's': ' ', 'r': '\r', 'n': '\n'}
def ircv3_message_parser(msg):
    n = msg.split(' ')

    # Process IRCv3 tags
    tags = {}
    if n[0].startswith('@'):
        i = n[0][1:].split(';')
        del n[0]
        for tag in i:
            tag = tag.split('=', 1)
            if len(tag) == 1:
                tags[tag[0]] = True
            elif len(tag) == 2:
                if '\\' in tag[1]: # Iteration is bad, only do it if required.
                    value  = ''
                    escape = False
                    for char in tag[1]: # TODO: Remove this iteration.
                        if escape:
                            value += ircv3_tag_escapes.get(char) or char
                            escape = False
                        elif char == '\\':
                            escape = True
                        else:
                            value += char
                else:
                    value = tag[1]
                tags[tag[0]] = value

    # Process arguments
    if n[0].startswith(':'):
        while len(n) < 2:
            n.append('')
        hostmask = n[0][1:].split('!')
        if len(hostmask) < 2:
            hostmask.append(hostmask[0])
        i = hostmask[1].split('@')
        if len(i) < 2:
            i.append(i[0])
        hostmask = (hostmask[0], i[0], i[1])
        cmd      = n[1]
    else:
        cmd      = n[0]
        hostmask = (cmd, cmd, cmd)
        n.insert(0, ':??!??@??')

    # Get the command and arguments
    args = []
    c = 1
    for i in n[2:]:
        c += 1
        if i.startswith(':'):
            args.append(' '.join(n[c:]))
            break
        else:
            args.append(i)

    # Return the parsed data
    return cmd, hostmask, tags, args

# Escape tags
def _escape_tag(tag):
    tag = str(tag).replace('\\', '\\\\')
    for i in ircv3_tag_escapes:
        tag = tag.replace(ircv3_tag_escapes[i], '\\' + i)
    return tag

# Convert a dict into an IRCv3 tags string
def _dict_to_tags(tags):
    res = b'@'
    for tag in tags:
        if tags[tag]:
            etag = _escape_tag(tag).replace('=', '-')
            if type(tags[tag]) == str:
                etag += '=' + _escape_tag(tags[tag]) + ';'
            etag = (etag + ';').encode('utf-8')
            if len(res) + len(etag) > 4095:
                break
            res += etag
    if len(res) < 3:
        return b''
    return res[:-1] + b' '

# Create the IRC class
class IRC:
    connected       = None
    debug_file      = sys.stdout
    sendq           = None
    _main_lock      = None
    _sasl           = False
    _unhandled_caps = None

    # Debug print()
    def debug(self, *args, **kwargs):
        if self.debug_file:
            print(*args, **kwargs, file = self.debug_file)
            if hasattr(self.debug_file, 'flush'):
                self.debug_file.flush()

    # Send raw messages
    def quote(self, *msg, force = None, tags = None):
        if not tags and len(msg) > 0 and type(msg[0]) == dict:
            tags = msg[0]
            msg  = msg[1:]
        if type(tags) != dict or 'message-tags' not in self.active_caps or \
          'draft/message-tags-0.2' not in self.active_caps:
            tags = None
        if self.connected or force:
            self.debug('>3> ' + str(tags) if tags else '>>>', *msg)
            if self.sendq and self.connected:
                sendq, self.sendq = self.sendq, None
                for i in sendq:
                    self.quote(*i)
            msg = ' '.join(msg).replace('\r', ' ').replace('\n', ' ').encode(
                'utf-8')[:510]
            if tags and len(tags) > 0:
                msg = _dict_to_tags(tags) + msg
            self.sock.sendall(msg + b'\r\n')
        else:
            self.debug('>Q>', *msg)
            if not self.sendq:
                self.sendq = []
            if tags:
                msg = (tags,) + msg
            self.sendq.append(msg)

    # User-friendly msg, notice, and ctcp functions.
    def msg(self, target, *msg, tags = None):
        self.quote('PRIVMSG', str(target), ':' + ' '.join(msg), tags = tags)

    def notice(self, target, *msg, tags = None):
        self.quote('NOTICE',  str(target), ':' + ' '.join(msg), tags = tags)

    def ctcp(self, target, *msg, reply = False, tags = None):
        m = (self.notice if reply else self.msg)
        return m(target, '\x01{}\x01'.format(' '.join(msg)), tags = tags)

    def me(self, target, *msg, tags = None):
        return self.ctcp(target, 'ACTION', *msg, tags = tags)

    # Allow per-connection handlers
    def Handler(self, *events, ircv3 = False):
        return _add_handler(self.handlers, events, ircv3)

    # The connect function
    def connect(self):
        if self.connected != None:
            self.debug('Already connected!')
            return
        self.connected = False
        self.debug('Connecting to', self.ip, 'port', self.port)
        addrinfo  = socket.getaddrinfo(self.ip, self.port, 0,
            socket.SOCK_STREAM)[0]
        self.sock = socket.socket(*addrinfo[:2])
        if self.ssl:
            self.debug('SSL handshake')
            if self.verify_ssl:
                self.sock = ssl.wrap_socket(self.sock,
                    cert_reqs=ssl.CERT_REQUIRED, ca_certs = get_ca_certs(),
                        do_handshake_on_connect = True)
            else:
                self.sock = ssl.wrap_socket(self.sock,
                    do_handshake_on_connect = True)
        self.sock.connect(addrinfo[4])
        if self.ssl and self.verify_ssl:
            ssl.match_hostname(self.sock.getpeercert(), self.ip)
        # Begin IRCv3 CAP negotiation.
        self._unhandled_caps = None
        self.quote('CAP LS 302', force = True)
        self.quote('USER', self.ident, '0', '*', ':' + self.realname,
            force = True)
        self.quote('NICK', self.nick, force = True)
        atexit.register(self.disconnect)
        self.debug('Starting main loop...')
        self.main()

    # An easier way to disconnect
    def disconnect(self, msg = None, *, auto_reconnect = False):
        self.persist   = auto_reconnect and self.persist
        self.connected = None
        msg            = msg or self.quit_message
        atexit.unregister(self.disconnect)
        self._unhandled_caps = None
        try:
            self.quote('QUIT :' + str(msg), force = True)
            self.sock.shutdown()
        except:
            pass

    # Finish capability negotiation
    def finish_negotiation(self, cap):
        self.debug('Capability', cap, 'handled.')
        if self._unhandled_caps:
            cap = cap.lower()
            if cap in self._unhandled_caps:
                del self._unhandled_caps[cap]
            if len(self._unhandled_caps) < 1:
                self._unhandled_caps = None
                if not self.connected:
                    self.quote('CAP END', force = True)

    # Change the message parser
    def change_parser(self, parser = ircv3_message_parser):
        self._parse = parser

    # Launch handlers
    def _handle(self, cmd, hostmask, tags, args):
        r        = False
        cmd      = str(cmd).upper()
        hostmask = tuple(hostmask)
        for handlers in (_global_handlers, self.handlers):
            if cmd in handlers:
                for handler in handlers[cmd]:
                    r = True
                    params = [self, hostmask, list(args)]
                    if hasattr(handler, 'miniirc_ircv3'):
                        params.insert(2, dict(tags))
                    t = threading.Thread(target = handler,
                        args = params)
                    t.start()
        return r

    # Launch IRCv3 handlers
    def _handle_cap(self, cap):
        cap = cap.lower()
        self.active_caps.add(cap)
        if self._unhandled_caps and cap in self._unhandled_caps:
            handled = self._handle('IRCv3 ' + cap,
                ('CAP', 'CAP', 'CAP'), {}, self._unhandled_caps[cap])
            if not handled:
                self.finish_negotiation(cap)

    # The main loop
    def _main(self):
        self.debug('Main loop running!')
        while True:
            raw = b''
            c = 0
            while not raw.endswith(b'\n'):
                c += 1
                try:
                    raw += self.sock.recv(4096).replace(b'\r', b'\n')
                    if c > 1000:
                        self.debug('Waited 1,000 times on the socket!')
                        raise Exception('Spam detected')
                except Exception as e:
                    self.debug('Lost connection! ', repr(e))
                    self.disconnect(auto_reconnect = True)
                    if self.persist:
                        sleep(5)
                        self.debug('Reconnecting...')
                        self._main_lock = None
                        self.connect()
                    return
            raw = raw.split(b'\n')
            for line in raw:
                try:
                    line = line.decode('utf-8', errors = 'replace')
                except UnicodeDecodeError:
                    self.debug('Bad line:', line)
                    line = ''
                if len(line) > 0:
                    self.debug('<<<', line)
                    result = self._parse(line)
                    if type(result) == tuple and len(result) == 4:
                        self._handle(*result)
                    else:
                        self.debug('Ignored message:', line)

    # Thread the main loop
    def main(self):
        if self._main_lock and self._main_lock.is_alive():
            self.debug('Main loop already running!')
            return self._main_lock
        self.debug('Creating new thread...')
        self._main_lock = threading.Thread(target = self._main)
        self._main_lock.start()
        return self._main_lock

    # Initialize the class
    def __init__(self, ip, port, nick, channels = None, *,
      ssl           = None, # None: Auto
      ident         = None,
      realname      = None,
      persist       = True,
      debug         = False,
      ns_identity   = None,
      auto_connect  = True,
      ircv3_caps    = set(),
      connect_modes = None,
      quit_message  = 'I grew sick and died.',
      verify_ssl    = True
      ):
        # Set basic variables
        self.ip             = ip
        self.port           = int(port)
        self.nick           = nick
        self.channels       = set(channels or ())
        self.ident          = ident    or nick
        self.realname       = realname or nick
        self.ssl            = ssl
        self.persist        = persist
        self.ns_identity    = ns_identity
        self.ircv3_caps     = set(ircv3_caps or ()) | _default_caps
        self.active_caps    = set()
        self.connect_modes  = connect_modes
        self.quit_message   = quit_message
        self.verify_ssl     = verify_ssl

        # Set the debug file
        if not debug:
            self.debug_file = None
        elif hasattr(debug, 'write'):
            self.debug_file = debug

        # Add IRCv3 capabilities.
        if self.ns_identity:    self.ircv3_caps.add('sasl')

        # Add handlers and set the default message parser
        self.change_parser()
        self.handlers       = {}
        if ssl == None and self.port == 6697:
            self.ssl = True

        # Start the connection
        if auto_connect:
            self.connect()

# Create basic handlers, so the bot will work.
@Handler('001')
def _handler(irc, hostmask, args):
    irc.connected = True
    irc._unhandled_caps = None
    irc.debug('Connected!')
    if irc.connect_modes:
        irc.quote('MODE', irc.nick, irc.connect_modes)
    if not irc._sasl and irc.ns_identity:
        irc.debug('Logging in (no SASL, aww)...')
        irc.msg('NickServ', 'identify ' + irc.ns_identity)
    irc.debug('*** Joining channels...', irc.channels)
    irc.quote('JOIN', ','.join(irc.channels))

@Handler('PING')
def _handler(irc, hostmask, args):
    args.insert(0, 'PONG')
    irc.quote(' '.join(args), force = True)

@Handler('432', '433')
def _handler(irc, hostmask, args):
    if not irc.connected:
        try:
            return int(irc.nick[0])
        except:
            pass
        if len(irc.nick) > 20:
            return
        print('WARNING: The requested nickname', repr(irc.nick), 'is invalid or'
            ' already in use. Trying again with', repr(irc.nick + '_') + '...',
            file=sys.stderr)
        irc.nick += '_'
        irc.quote('NICK', irc.nick, force = True)

@Handler('NICK')
def _handler(irc, hostmask, args):
    if hostmask[0].lower() == irc.nick.lower():
        irc.nick = args[-1]

@Handler('PRIVMSG')
def _handler(irc, hostmask, args):
    if not version:
        return
    if args[-1].startswith(':\x01VERSION') and args[-1].endswith('\x01'):
        irc.ctcp(hostmask[0], 'VERSION', version, reply = True)

# Handle IRCv3 capabilities
@Handler('CAP')
def _handler(irc, hostmask, args):
    if len(args) < 3:
        return
    cmd = args[1].upper()
    if cmd in ('LS', 'NEW') and args[-1].startswith(':'):
        caps = args[-1][1:].split(' ')
        req  = set()
        if not irc._unhandled_caps:
            irc._unhandled_caps = {}
        for raw in caps:
            raw = raw.split('=', 1)
            cap = raw[0].lower()
            if cap in irc.ircv3_caps:
                irc._unhandled_caps[cap] = raw
                if cap == 'sts':
                    irc._handle_cap(cap)
                else:
                    req.add(cap)
        if len(req) > 0:
            irc.quote('CAP REQ', ':' + ' '.join(req), force = True)
        elif cmd == 'LS' and len(irc._unhandled_caps) == 0 and args[2] != '*':
            irc._unhandled_caps = None
            irc.quote('CAP END', force = True)
    elif cmd == 'ACK':
        if args[-1].startswith(':'):
            args[-1] = args[-1][1:]
        caps = args[-1].split(' ')
        for cap in caps:
            irc._handle_cap(cap)
    elif cmd == 'NAK':
        irc._unhandled_caps = None
        irc.quote('CAP END', force = True)
    elif cmd == 'DEL':
        for cap in args[-1][1:].split(' '):
            cap = cap.lower()
            if cap in irc.active_caps:
                irc.active_caps.remove(cap)

# SASL
@Handler('IRCv3 SASL')
def _handler(irc, hostmask, args):
    if irc.ns_identity and (len(args) < 2 or 'PLAIN' in
      args[-1].upper().split(',')):
        irc.quote('AUTHENTICATE PLAIN', force = True)
    else:
        irc._sasl = False
        irc.quote('AUTHENTICATE *', force = True)
        irc.finish_negotiation('sasl')

@Handler('AUTHENTICATE')
def _handler(irc, hostmask, args):
    if len(args) > 0 and args[0] == '+':
        from base64 import b64encode
        irc._sasl = True
        pw = irc.ns_identity.split(' ', 1)
        pw = '{0}\x00{0}\x00{1}'.format(*pw).encode('utf-8')
        irc.quote('AUTHENTICATE', b64encode(pw).decode('utf-8'), force = True)

@Handler('904', '905')
def _handler(irc, hostmask, args):
    irc._sasl = False
    irc.quote('AUTHENTICATE *', force = True)

@Handler('902', '903', '904', '905')
def _handler(irc, hostmask, args):
    irc.finish_negotiation('sasl')

@Handler('IRCv3 STS')
def _handler(irc, hostmask, args):
    if not irc.ssl and len(args) == 2:
        params = args[-1].split(',')
        port = None
        for i in params:
            n = i.split('=')
            if len(n) == 2 and n[0] == 'port':
                port = n[1]
                break
        try:
            port = int(port)
        except:
            port = None
        if port:
            persist = irc.persist
            irc.disconnect()
            irc.debug('NOTICE: An IRCv3 STS has been detected, the port will',
                'be changed to', port, 'and TLS/SSL will be enabled.')
            irc.port = port
            irc.ssl  = True
            sleep(1)
            irc.connect()
            irc.persist = persist
            return

    irc.finish_negotiation('sts')

del _handler
