#!/usr/bin/python3
#
# Mini IRC framework
#

import atexit, copy, threading, socket, ssl, sys
from time import sleep
__all__ = ['Handler', 'IRC']

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

    # Debug print()
    def debug(self, *args, **kwargs):
        if self._debug:
            print(*args, **kwargs)

    # Send raw messages
    def quote(self, *msg, force = None):
        self.debug('>>>', *msg)
        if self.connected or force:
            if self.sendq:
                sendq      = self.sendq
                self.sendq = None
                for i in sendq:
                    self.quote(*i)
            msg = '{}\n'.format(' '.join(msg)).encode('utf-8')
            self.sock.send(msg)
        else:
            if not self.sendq:
                self.sendq = []
            self.sendq.append(msg)

    # User-friendly msg, notice, and ctcp functions.
    def msg(self, target, *msg):
        return self.quote('PRIVMSG {} :{}'.format(target, ' '.join(msg)))

    def notice(self, target, *msg):
        return self.quote('NOTICE {} :{}'.format(target, ' '.join(msg)))

    def ctcp(self, target, *msg):
        return self.msg(target, '\x01{}\x01'.format(' '.join(msg)))

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
            self.sock = ssl.wrap_socket(self.sock)
        self.sock.connect((self.ip, self.port))
        self.quote('USER', self.ident, '0', '*', ':' + self.realname,
            force = True)
        self.quote('NICK', self.nick, force = True)
        atexit.register(self.disconnect)
        self.debug('Starting main loop...')
        self.main()

    # An easier way to disconnect
    def disconnect(self, msg = 'I grew sick and died.'):
        self.persist = False
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
                    raw += self.sock.recv(4096)
                    if c > 100:
                        self.debug('Waited 100 times on the socket!')
                        raise NotImplementedError('Spam detected')
                except Exception as e:
                    self.debug('Lost connection! ', repr(e))
                    self.disconnect()
                    if self.persist:
                        sleep(5)
                        self.debug('Reconnecting...')
                        self._main_lock = None
                        self.connect()
                    return
            raw = raw.replace(b'\r', b'\n').split(b'\n')
            for line in raw:
                try:
                    line = line.decode('utf-8')
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
                                args = (self, hostmask, args))
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
      persist       = False,
      debug         = False,
      ns_identity   = None,
      auto_connect  = True
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
    if irc.ns_identity:
        irc.debug('Logging in...')
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

del _handler

# Debugging - Makes a bot join #lurk and print all PRIVMSGs.
if __name__ == '__main__':
    import os
    @Handler('PRIVMSG')
    def _handle(irc, hostmask, args):
        if args[-1] == ':,quit':
            irc.disconnect()
            print('Found ,quit')
        irc.debug(args[0], '<{}>'.format(hostmask[0]), args[1][1:])
    irc = IRC('xeroxirc.net', 6697, 'stdoutbot', ['#lurk'],
       debug = 'debug' in os.environ)
