#!/usr/bin/python3
#
# Mini IRC framework
#

import atexit, copy, threading, socket, ssl, sys
from time import sleep
__all__ = ['Handler', 'IRC']
version = 'miniirc IRC framework v0.2'

# Get the certificate list.
try:
    from certifi import where as get_ca_certs
except ImportError:
    get_ca_certs = lambda : None

# Create global handlers
_global_handlers = {}

def _add_handler(handlers, events):
    def _finish_handler(func):
        for event in events:
            event = str(event).upper()
            if event not in handlers:
                handlers[event] = []
            if func not in handlers[event]:
                handlers[event].append(func)
        return func

    return _finish_handler

def Handler(*events):
    return _add_handler(_global_handlers, events)

# Create the IRC class
class IRC:
    connected  = False
    sendq      = None
    _main_lock = None
    _sasl      = False

    # Debug print()
    def debug(self, *args, **kwargs):
        if self._debug:
            print(*args, **kwargs)

    # Send raw messages
    def quote(self, *msg, force = None):
        if self.connected or force:
            self.debug('>>>', *msg)
            if self.sendq and self.connected:
                sendq      = self.sendq
                self.sendq = None
                for i in sendq:
                    self.quote(*i)
            msg = ' '.join(msg).encode('utf-8')[:510] + b'\r\n'
            self.sock.send(msg)
        else:
            self.debug('>Q>', *msg)
            if not self.sendq:
                self.sendq = []
            self.sendq.append(msg)

    # User-friendly msg, notice, and ctcp functions.
    def msg(self, target, *msg):
        return self.quote('PRIVMSG', str(target),
            ':' + ' '.join(msg).replace('\r', ' ').replace('\n', ' '))

    def notice(self, target, *msg):
        return self.quote('NOTICE', str(target),
            ':' + ' '.join(msg).replace('\r', ' ').replace('\n', ' '))

    def ctcp(self, target, *msg, reply = False):
        m = (self.notice if reply else self.msg)
        return m(target, '\x01{}\x01'.format(' '.join(msg)))

    def me(self, target, *msg):
        return self.ctcp(target, 'ACTION', *msg)

    # Allow per-connection handlers
    def Handler(self, *events):
        return _add_handler(self.handlers, events)

    # The connect function
    def connect(self):
        if self.connected:
            self.debug('Already connected!')
            return
        self.debug('Connecting to', self.ip, 'port', self.port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.ssl:
            self.debug('SSL handshake')
            if self.verify_ssl:
                self.sock = ssl.wrap_socket(self.sock,
                    cert_reqs=ssl.CERT_REQUIRED, ca_certs = get_ca_certs(),
                        do_handshake_on_connect = True)
            else:
                self.sock = ssl.wrap_socket(self.sock,
                    do_handshake_on_connect = True)
        self.sock.connect((self.ip, self.port))
        if self.ssl and self.verify_ssl:
            ssl.match_hostname(self.sock.getpeercert(), self.ip)
        # Iterate over the caps list to make it easier to pick up ACKs and NAKs.
        for cap in self.ircv3_caps:
            self.debug('Requesting IRCv3 capability', cap)
            self.quote('CAP', 'REQ', ':' + cap, force = True)
        self.quote('USER', self.ident, '0', '*', ':' + self.realname,
            force = True)
        self.quote('NICK', self.nick, force = True)
        atexit.register(self.disconnect)
        self.debug('Starting main loop...')
        self.main()

    # An easier way to disconnect
    def disconnect(self, msg = 'I grew sick and died.', *,
      auto_reconnect = False):
        self.persist   = auto_reconnect and self.persist
        self.connected = False
        atexit.unregister(self.disconnect)
        try:
            self.quote('QUIT :' + msg, force = True)
            self.sock.shutdown()
        except:
            pass

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
                    n = line.split(' ')
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
                    else:
                        cmd      = n[0].upper()
                        hostmask = (cmd, cmd, cmd)
                        n.insert(0, ':??!??@??')

                    # Get the command and arguments
                    cmd  = n[1].upper()
                    args = []
                    c = 1
                    for i in n[2:]:
                        c += 1
                        if i.startswith(':'):
                            args.append(' '.join(n[c:]))
                            break
                        else:
                            args.append(i)
                    self.debug('<<<', hostmask, cmd, args)

                    # Launch all handlers for the command
                    if cmd in self.handlers:
                        for handler in self.handlers[cmd]:
                            t = threading.Thread(target = handler,
                                args = (self, hostmask, copy.copy(args)))
                            t.start()

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
      verify_ssl    = True
      ):
        # Set basic variables
        self.ip             = ip
        self.port           = int(port)
        self.nick           = nick
        self.channels       = channels or ()
        self.ident          = ident    or nick
        self.realname       = realname or nick
        self.ssl            = ssl
        self.persist        = persist
        self._debug         = debug
        self.ns_identity    = ns_identity
        self.ircv3_caps     = set(ircv3_caps or [])
        self.verify_ssl     = verify_ssl

        # Add SASL
        if self.ns_identity:
            self.ircv3_caps.add('sasl')

        # Add handlers
        self.handlers       = copy.deepcopy(_global_handlers)
        if ssl == None and port == 6697:
            self.ssl = True

        # Start the connection
        if auto_connect:
            self.connect()

# Create basic handlers, so the bot will work.
@Handler('001')
def _handler(irc, hostmask, args):
    irc.connected = True
    irc.debug('Connected!')
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

# SASL
@Handler('CAP')
def _handler(irc, hostmask, args):
    if len(args) < 3 or not irc.ns_identity:
        return
    elif args[1] == 'ACK' and args[2].replace(':', '', 1).startswith('sasl'):
        irc.quote('AUTHENTICATE PLAIN', force = True)

@Handler('AUTHENTICATE')
def _handler(irc, hostmask, args):
    if len(args) > 0 and args[0] == '+':
        from base64 import b64encode
        irc._sasl = True
        pw = irc.ns_identity.split(' ')
        pw = '{0}\x00{0}\x00{1}'.format(*pw).encode('utf-8')
        irc.quote('AUTHENTICATE', b64encode(pw).decode('utf-8'), force = True)

@Handler('904', '905')
def _handler(irc, hostmask, args):
    irc._sasl = False
    irc.quote('AUTHENTICATE *', force = True)

@Handler('903', '904', '905')
def _handler(irc, hostmask, args):
    if len(irc.ircv3_caps) < 2:
        irc.quote('CAP END', force = True)

del _handler
