#!/usr/bin/python3
#
# miniirc - A small-ish IRC framework.
#
# © 2018-2021 by luk3yx and other contributors of miniirc.
#

import atexit, collections, errno, threading, time, types, re, socket, ssl, sys

# The version string and tuple
ver = __version_info__ = (2,0,0,'a7')
version = 'miniirc IRC framework v2.0.0a7'
__version__ = '2.0.0a7'

# __all__ and _default_caps
__all__ = ['CmdHandler', 'Handler', 'IRC']
_default_caps = {'account-notify', 'account-tag', 'away-notify', 'cap-notify',
                 'chghost', 'extended-join', 'invite-notify', 'message-tags',
                 'oragono.io/maxline-2', 'server-time', 'sts'}

# Get the certificate list.
try:
    from certifi import where as get_ca_certs
except ImportError:
    def get_ca_certs():
        pass

# Create global handlers
_global_handlers = {}

class _Handler:
    __slots__ = ('func', 'cmdhandler', 'ircv3', 'run_in_thread')

    def __init__(self, func, *, cmdhandler, ircv3):
        self.func = func
        self.cmdhandler = cmdhandler
        self.ircv3 = ircv3
        self.run_in_thread = True

def _add_handler(handlers, events, ircv3, cmdhandler, colon):
    if colon:
        raise TypeError('The usage of colon=True is no longer supported')
    if not events:
        if not cmdhandler:
            raise TypeError('Handler() called without arguments.')
        events = (None,)

    def add_handler(func):
        handler = _Handler(func, cmdhandler=cmdhandler, ircv3=ircv3)
        for event in events:
            if event is not None:
                event = str(event).upper()
            if event not in handlers:
                handlers[event] = []
            if func not in handlers[event]:
                handlers[event].append(handler)

        return func

    return add_handler

def Handler(*events, ircv3=False, colon=False):
    return _add_handler(_global_handlers, events, ircv3, False, colon)

def CmdHandler(*events, ircv3=False, colon=False):
    return _add_handler(_global_handlers, events, ircv3, True, colon)

# Parse IRCv3 tags
_ircv3_tag_escapes = {':': ';', 's': ' ', 'r': '\r', 'n': '\n'}
def _tag_list_to_dict(tag_list):
    tags = {}
    for tag in tag_list:
        tag = tag.split('=', 1)
        if len(tag) == 1:
            tags[tag[0]] = ''
        elif len(tag) == 2:
            if '\\' in tag[1]: # Iteration is bad, only do it if required.
                value = ''
                escape = False
                for char in tag[1]: # TODO: Remove this iteration.
                    if escape:
                        value += _ircv3_tag_escapes.get(char, char)
                        escape = False
                    elif char == '\\':
                        escape = True
                    else:
                        value += char
            else:
                value = tag[1]
            tags[tag[0]] = value

    return tags

# Create the IRCv2/3 parser
IRCMessage = collections.namedtuple('IRCMessage', 'command hostmask tags args')
_msg_re = re.compile(
    r'^'
    r'(?:@([^ ]*) )?'                               # Tags
    r'(?::([^!@ ]*)(?:!([^@ ]*))?(?:@([^ ]*))? )?'  # Hostmask
    r'([^@: ][^ ]*)(?: (.*?)(?: :(.*))?)?'          # Command and arguments
    r'$'
)
def ircv3_message_parser(msg):
    match = _msg_re.match(msg)
    if not match:
        return

    # Process IRCv3 tags
    raw_tags = match.group(1)
    tags = {} if raw_tags is None else _tag_list_to_dict(raw_tags.split(';'))

    # Process arguments
    hostmask = (match.group(2) or '', match.group(3) or '',
                match.group(4) or '')
    cmd = match.group(5)

    # Get the command and arguments
    raw_args = match.group(6)
    args = [] if raw_args is None else raw_args.split(' ')

    trailing = match.group(7)
    if trailing:
        args.append(trailing)

    # Return the parsed data
    return IRCMessage(cmd.upper(), hostmask, tags, args)

# Escape tags
def _escape_tag(tag):
    tag = str(tag).replace('\\', '\\\\')
    for i in _ircv3_tag_escapes:
        tag = tag.replace(_ircv3_tag_escapes[i], '\\' + i)
    return tag

# Convert a dict into an IRCv3 tags string
def _dict_to_tags(tags):
    res = b'@'
    for tag, value in tags.items():
        if value or value == '':
            etag = _escape_tag(tag).replace('=', '-')
            if isinstance(value, str) and value:
                etag += '=' + _escape_tag(value)
            etag = (etag + ';').encode('utf-8')
            if len(res) + len(etag) > 4094:
                break
            res += etag
    if len(res) < 3:
        return b''
    return res[:-1] + b' '

# A wrapper for callable logfiles
class _Logfile:
    __slots__ = ('_buffer', '_func', '_lock')

    def write(self, data):
        with self._lock:
            self._buffer += data
            while '\n' in self._buffer:
                line, self._buffer = self._buffer.split('\n', 1)
                self._func(line)

    def __init__(self, func):
        self._buffer = ''
        self._func = func
        self._lock = threading.Lock()

# Replace invalid RFC1459 characters with Unicode lookalikes
def _prune_arg(arg):
    if arg.startswith(':'):
        arg = '\u0703' + arg[1:]
    return arg.replace(' ', '\xa0').replace('\r', '\xa0').replace('\n', '\xa0')

# Create the IRC class
class IRC:
    connected = None
    debug_file = sys.stdout
    _sendq = None
    msglen = 512
    _main_thread = None
    _sasl = False
    _unhandled_caps = None

    def __init__(self, ip, port, nick, channels=None, *, ssl=None, ident=None,
                 realname=None, persist=True, debug=False, ns_identity=None,
                 auto_connect=True, ircv3_caps=None, connect_modes=None,
                 quit_message='I grew sick and died.', ping_interval=60,
                 ping_timeout=None, verify_ssl=True, executor=None):
        # Set basic variables
        self.ip = ip
        self.port = int(port)
        self.nick = self.current_nick = nick
        if isinstance(channels, str):
            channels = map(str.lstrip, channels.split(','))
        self.channels = set(channels or ())
        self.ident = ident or nick
        self.realname = realname or nick
        self.ssl = ssl
        self.persist = persist
        self.ircv3_caps = set(ircv3_caps or ()) | _default_caps
        self.active_caps = set()
        self.isupport = {}
        self.connect_modes = connect_modes
        self.quit_message = quit_message
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.verify_ssl = verify_ssl
        self._executor = executor

        # Set the NickServ identity
        if ns_identity:
            if isinstance(ns_identity, str):
                self.ns_identity = tuple(ns_identity.split(' ', 1))
            else:
                self.ns_identity = tuple(map(str, ns_identity))
            assert len(self.ns_identity) == 2
        else:
            self.ns_identity = None

        # Set the debug file
        if not debug:
            self.debug_file = None
        elif hasattr(debug, 'write'):
            self.debug_file = debug
        elif callable(debug):
            self.debug_file = _Logfile(debug)

        # Add IRCv3 capabilities.
        if self.ns_identity:
            self.ircv3_caps.add('sasl')

        # Add handlers and set the default message parser
        self.change_parser()
        self._handlers = {}
        self._send_lock = threading.Lock()
        if ssl is None and self.port == 6697:
            self.ssl = True

        # Start the connection
        if auto_connect:
            self.connect()

    # Debug print()
    def debug(self, *args, **kwargs):
        if self.debug_file:
            print(*args, file=self.debug_file, **kwargs)
            if hasattr(self.debug_file, 'flush'):
                self.debug_file.flush()

    # Send raw messages
    def quote(self, *msg, force=False, tags=None):
        if not self.connected and not force:
            self.debug('>Q>', *msg)
            if not self._sendq:
                self._sendq = []
            self._sendq.append((tags, msg))
            return

        self.debug('>>>', *msg)
        msg = (' '.join(msg).encode('utf-8').replace(b'\r', b' ')
               .replace(b'\n', b' '))

        if len(msg) + 2 > self.msglen:
            msg = msg[:self.msglen - 2]
            if msg[-1] >= 0x80:
                msg = msg.decode('utf-8', 'ignore').encode('utf-8')

        if isinstance(tags, dict) and 'message-tags' in self.active_caps:
            msg = _dict_to_tags(tags) + msg

        self._send_lock.acquire()
        try: # Apparently try/finally is faster than "with".
            self.sock.sendall(msg + b'\r\n')
        except (AttributeError, BrokenPipeError):
            pass
        finally:
            self._send_lock.release()

    def send(self, command, *args, force=False, tags=None):
        if args:
            self.quote(
                command,
                *tuple(map(_prune_arg, args[:-1])) + (':' + args[-1],),
                force=force,
                tags=tags
            )
        else:
            self.quote(command, force=force, tags=tags)

    # User-friendly msg, notice, and CTCP functions.
    def msg(self, target, *msg, tags=None):
        self.quote('PRIVMSG', target, ':' + ' '.join(msg), tags=tags)

    def notice(self, target, *msg, tags=None):
        self.quote('NOTICE', target, ':' + ' '.join(msg), tags=tags)

    def ctcp(self, target, *msg, reply=False, tags=None):
        m = (self.notice if reply else self.msg)
        return m(target, '\x01{}\x01'.format(' '.join(msg)), tags=tags)

    def me(self, target, *msg, tags=None):
        return self.ctcp(target, 'ACTION', *msg, tags=tags)

    # Allow per-connection handlers
    def Handler(self, *events, ircv3=False, colon=False):
        return _add_handler(self._handlers, events, ircv3, False, colon)

    def CmdHandler(self, *events, ircv3=False, colon=False):
        return _add_handler(self._handlers, events, ircv3, True, )

    # The connect function
    def connect(self):
        self._send_lock.acquire()
        try:
            if self.connected is not None:
                self.debug('Already connected!')
                return
            self.connected = False
        finally:
            self._send_lock.release()

        self.debug('Connecting to', self.ip, 'port', self.port)
        self.sock = socket.create_connection(
            (self.ip, self.port),
            timeout=self.ping_timeout or self.ping_interval,
        )
        if self.ssl:
            self.debug('SSL handshake')
            ctx = ssl.create_default_context(cafile=get_ca_certs())
            if self.verify_ssl:
                assert ctx.check_hostname
            else:
                warnings.warn('Disabling verify_ssl is usually a bad idea.')
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            self.sock = ctx.wrap_socket(self.sock, server_hostname=self.ip)

        self._unhandled_caps = None
        self.current_nick = self.nick
        self.quote('CAP LS 302', force=True)
        self.quote('USER', self.ident, '0', '*', ':' + self.realname,
            force=True)
        self.quote('NICK', self.nick, force=True)
        atexit.register(self.disconnect)
        self.debug('Starting main loop...')
        self._sasl = self._pinged = False
        self._start_main_loop()

    def _start_main_loop(self):
        # Start the thread before updating _main_thread so that
        # wait_until_disconnected() works correctly.
        thread = threading.Thread(target=self._main)
        thread.start()
        self._main_thread = thread

    # Disconnect from IRC.
    def disconnect(self, msg=None, *, auto_reconnect=False):
        self.persist = auto_reconnect and self.persist
        self.connected = None
        self.active_caps.clear()
        atexit.unregister(self.disconnect)
        self._unhandled_caps = None
        try:
            self.quote('QUIT :' + str(msg or self.quit_message), force=True)
            self.sock.shutdown(socket.SHUT_RDWR)
        except:
            pass
        try:
            self.sock.close()
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
                    self.quote('CAP END', force=True)

    # Change the message parser
    def change_parser(self, parser=ircv3_message_parser):
        self._parse = parser

    # Start a handler function
    def _start_handler(self, handlers, msg):
        for handler in handlers:
            params = [self, msg.hostmask, list(msg.args)]
            if handler.ircv3:
                params.insert(2, types.MappingProxyType(msg.tags))
            if handler.cmdhandler:
                params.insert(1, msg.command)

            if not handler.run_in_thread:
                try:
                    handler.func(*params)
                except:
                    import traceback
                    traceback.print_exc()
            elif self._executor is not None:
                self._executor.submit(handler.func, *params)
            else:
                threading.Thread(target=handler.func, args=params).start()

    # Launch handlers
    def handle_msg(self, msg):
        handled = False
        for handlers in (_global_handlers, self._handlers):
            if msg.command in handlers:
                self._start_handler(handlers[msg.command], msg)
                handled = True

            if None in handlers:
                self._start_handler(handlers[None], msg)

        return handled

    # Launch IRCv3 handlers
    def _handle_cap(self, cap):
        cap = cap.lower()
        self.active_caps.add(cap)
        if self._unhandled_caps and cap in self._unhandled_caps:
            handled = self.handle_msg(IRCMessage(
                ('IRCv3 ' + cap).upper(), ('', '', ''), {},
                self._unhandled_caps[cap]
            ))
            if not handled:
                self.finish_negotiation(cap)

    # The main loop
    def _main(self):
        self.debug('Main loop running!')
        buffer = b''
        while True:
            try:
                assert len(buffer) < 65535, 'Very long line detected!'
                try:
                    raw = self.sock.recv(8192).replace(b'\r', b'\n')
                    if not raw:
                        raise ConnectionAbortedError
                    buffer += raw
                except socket.timeout:
                    if self._pinged:
                        raise
                    else:
                        self._pinged = True
                        if self.ping_timeout:
                            self.sock.settimeout(self.ping_timeout)
                        self.quote('PING', ':miniirc-ping', force=True)
                except socket.error as e:
                    if e.errno != errno.EWOULDBLOCK:
                        raise
            except (OSError, socket.error) as e:
                self.debug('Lost connection!', repr(e))
                self.disconnect(auto_reconnect=True)
                while self.persist:
                    time.sleep(5)
                    self.debug('Reconnecting...')
                    try:
                        self.connect()
                    except (OSError, socket.error):
                        self.debug('Failed to reconnect!')
                        self.connected = None
                    else:
                        return
                return

            raw = buffer.split(b'\n')
            buffer = raw.pop()
            for line in raw:
                line = line.decode('utf-8', 'replace')
                if not line:
                    continue

                self.debug('<<<', line)
                try:
                    msg = self._parse(line)
                    if isinstance(msg, IRCMessage):
                        self.handle_msg(msg)
                    else:
                        self.debug('Ignored message:', parsed_line)
                except:
                    import traceback
                    traceback.print_exc()
            del raw

    def wait_until_disconnected(self, *, _timeout=None):
        # The main thread may be replaced on reconnects
        while self._main_thread and self._main_thread.is_alive():
            self._main_thread.join(_timeout)

# Handle some IRC messages by default.
@Handler('001')
def _handler(irc, hostmask, args):
    irc.connected = True
    irc.isupport.clear()
    irc._unhandled_caps = None
    if irc.ping_interval:
        irc.sock.settimeout(irc.ping_interval)
    irc.debug('Connected!')
    if irc.connect_modes:
        irc.quote('MODE', irc.nick, irc.connect_modes)
    if not irc._sasl and irc.ns_identity:
        irc.debug('Logging in (no SASL, aww)...')
        irc.msg('NickServ', 'identify', *irc.ns_identity)
    if irc.channels:
        irc.debug('*** Joining channels...', irc.channels)
        irc.quote('JOIN', ','.join(irc.channels))

    with irc._send_lock:
        sendq, irc._sendq = irc._sendq, None
    if sendq:
        for tags, args in sendq:
            irc.quote(*args, tags=tags)

@Handler('PING')
def _handler(irc, hostmask, args):
    irc.send('PONG', *args, force=True)

@Handler('PONG')
def _handler(irc, hostmask, args):
    if args and args[-1] == 'miniirc-ping' and irc.ping_interval:
        irc._pinged = False
        if irc.ping_timeout:
            irc.sock.settimeout(irc.ping_interval)

@Handler('432', '433')
def _handler(irc, hostmask, args):
    if not irc.connected:
        try:
            return int(irc.nick[0])
        except (IndexError, ValueError):
            pass
        if len(irc.current_nick) >= irc.isupport.get('NICKLEN', 20):
            return
        irc.debug('WARNING: The requested nickname', repr(irc.current_nick),
            'is invalid. Trying again with', repr(irc.current_nick + '_') +
            '...')
        irc.current_nick += '_'
        irc.quote('NICK', irc.current_nick, force=True)

@Handler('NICK')
def _handler(irc, hostmask, args):
    if hostmask[0].lower() == irc.current_nick.lower():
        irc.current_nick = args[-1]

@Handler('PRIVMSG')
def _handler(irc, hostmask, args):
    if not version:
        return
    if args[-1].startswith('\x01VERSION') and args[-1].endswith('\x01'):
        irc.ctcp(hostmask[0], 'VERSION', version, reply=True)

# Handle IRCv3 capabilities
@Handler('CAP')
def _handler(irc, hostmask, args):
    if len(args) < 3:
        return
    cmd = args[1].upper()
    if cmd in ('LS', 'NEW'):
        caps = args[-1].split(' ')
        req = set()
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
        if irc.connected is None:
            return
        elif req:
            irc.quote('CAP REQ', ':' + ' '.join(req), force=True)
        elif cmd == 'LS' and not irc._unhandled_caps and args[2] != '*':
            irc._unhandled_caps = None
            irc.quote('CAP END', force=True)
    elif cmd == 'ACK':
        caps = args[-1].split(' ')
        for cap in caps:
            irc._handle_cap(cap)
    elif cmd == 'NAK':
        irc._unhandled_caps = None
        irc.quote('CAP END', force=True)
    elif cmd == 'DEL':
        for cap in args[-1].split(' '):
            cap = cap.lower()
            if cap in irc.active_caps:
                irc.active_caps.remove(cap)

# SASL
@Handler('IRCv3 SASL')
def _handler(irc, hostmask, args):
    if irc.ns_identity and (len(args) < 2 or 'PLAIN' in
            args[-1].upper().split(',')):
        irc.quote('AUTHENTICATE PLAIN', force=True)
    else:
        irc.quote('AUTHENTICATE *', force=True)
        irc.finish_negotiation('sasl')

@Handler('AUTHENTICATE')
def _handler(irc, hostmask, args):
    if args and args[0] == '+':
        from base64 import b64encode
        irc._sasl = True
        pw = '{0}\x00{0}\x00{1}'.format(*irc.ns_identity).encode('utf-8')
        irc.quote('AUTHENTICATE', b64encode(pw).decode('utf-8'), force=True)

@Handler('904', '905')
def _handler(irc, hostmask, args):
    if irc._sasl:
        irc._sasl = False
        irc.quote('AUTHENTICATE *', force=True)

@Handler('902', '903', '904', '905')
def _handler(irc, hostmask, args):
    irc.finish_negotiation('sasl')

# STS
@Handler('IRCv3 STS')
def _handler(irc, hostmask, args):
    if not irc.ssl and len(args) == 2:
        try:
            port = int(_tags_to_dict(args[1].split(','))['port'])
        except (IndexError, ValueError):
            return

        # Stop irc.wait_until_disconnected() from returning early
        irc._main_thread = threading.current_thread()

        persist = irc.persist
        irc.disconnect()
        irc.debug('STS detected, enabling TLS/SSL and changing the port to ',
                  port)
        irc.port = port
        irc.ssl = True
        time.sleep(1)
        irc.connect()
        irc.persist = persist
    else:
        irc.finish_negotiation('sts')

# Maximum line length
@Handler('IRCv3 oragono.io/maxline-2')
def _handler(irc, hostmask, args):
    try:
        irc.msglen = max(int(args[-1]), 512)
    except ValueError:
        pass

    irc.finish_negotiation(args[0])

# Handle ISUPPORT messages
@Handler('005')
def _handler(irc, hostmask, args):
    isupport = _tag_list_to_dict(args[1:-1])

    # Try and auto-detect integers
    remove = set()
    for key in isupport:
        try:
            isupport[key] = int(isupport[key])
            if key == 'NICKLEN':
                irc.current_nick = irc.current_nick[:isupport[key]]
        except ValueError:
            if key.endswith('LEN'):
                remove.add(key)
    for key in remove:
        del isupport[key]

    irc.isupport.update(isupport)

del _handler
