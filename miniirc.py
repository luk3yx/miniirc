#!/usr/bin/python3
#
# miniirc - A small-ish IRC framework.
#
# © 2018-2022 by luk3yx and other contributors of miniirc.
#

import atexit, threading, time, select, socket, ssl, sys, warnings

# The version string and tuple
ver = __version_info__ = (1, 10, 0)
version = 'miniirc IRC framework v1.10.0'
__version__ = '1.10.0'

# __all__ and _default_caps
__all__ = ['CmdHandler', 'Handler', 'IRC']
_default_caps = {'account-tag', 'away-notify', 'cap-notify', 'chghost',
                 'draft/message-tags-0.2', 'invite-notify', 'message-tags',
                 'oragono.io/maxline-2', 'server-time', 'sts'}

# Get the certificate list.
try:
    from certifi import where as get_ca_certs
except ImportError:
    def get_ca_certs():
        pass

# Create global handlers
_global_handlers = {}
_colon_warning = False


def _add_handler(handlers, events, ircv3, cmd_arg, colon):
    if (colon and _colon_warning and
            not all(str(e).upper().startswith('IRCV3 ') for e in events)):
        warnings.warn('Using colon=True or not specifying the colon '
                      'keyword argument to miniirc.Handler is deprecated.',
                      DeprecationWarning, stacklevel=3)

    if not events:
        if not cmd_arg:
            raise TypeError('Handler() called without arguments.')
        events = (None,)

    def add_handler(func):
        for event in events:
            if event is not None:
                event = str(event).upper()
            if event not in handlers:
                handlers[event] = []
            if func not in handlers[event]:
                handlers[event].append(func)

        f = getattr(func, '__func__', func)
        if ircv3:
            f.miniirc_ircv3 = True
        if cmd_arg:
            f.miniirc_cmd_arg = True
        if colon:
            f.miniirc_colon = True
        return func

    return add_handler


def Handler(*events, ircv3=False, colon=True):
    return _add_handler(_global_handlers, events, ircv3, False, colon)


def CmdHandler(*events, ircv3=False, colon=True):
    return _add_handler(_global_handlers, events, ircv3, True, colon)


# Parse IRCv3 tags
ircv3_tag_escapes = {':': ';', 's': ' ', 'r': '\r', 'n': '\n'}


def _tags_to_dict(tag_list, separator=';'):
    tags = {}
    if separator:
        tag_list = tag_list.split(separator)
    for tag in tag_list:
        tag = tag.split('=', 1)
        if len(tag) == 1:
            tags[tag[0]] = True
        elif len(tag) == 2:
            if '\\' in tag[1]:  # Iteration is bad, only do it if required.
                value = ''
                escape = False
                for char in tag[1]:  # TODO: Remove this iteration.
                    if escape:
                        value += ircv3_tag_escapes.get(char, char)
                        escape = False
                    elif char == '\\':
                        escape = True
                    else:
                        value += char
            else:
                value = tag[1] or True
            tags[tag[0]] = value

    return tags


# Create the IRCv2/3 parser
def ircv3_message_parser(msg):
    n = msg.split(' ')

    # Process IRCv3 tags
    if n[0].startswith('@'):
        tags = _tags_to_dict(n.pop(0)[1:])
    else:
        tags = {}

    # Process arguments
    if n[0].startswith(':'):
        while len(n) < 2:
            n.append('')
        hostmask = n[0][1:].split('!', 1)
        if len(hostmask) < 2:
            hostmask.append(hostmask[0])
        i = hostmask[1].split('@', 1)
        if len(i) < 2:
            i.append(i[0])
        hostmask = (hostmask[0], i[0], i[1])
        cmd = n[1]
    else:
        cmd = n[0]
        hostmask = (cmd, cmd, cmd)
        n.insert(0, '')

    # Get the command and arguments
    args = []
    c = 1
    for word in n[2:]:
        c += 1
        if word.startswith(':'):
            args.append(' '.join(n[c:]))
            break
        elif word:
            args.append(word)
        else:
            # RFC 1459 allows multiple spaces to separate parameters, but this
            # is very uncommon and could possibly happen if a server tries to
            # send an empty parameter
            raise ValueError('Ambiguous IRC message')

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
    for tag, value in tags.items():
        if value and value != '':
            etag = _escape_tag(tag).replace('=', '-')
            if value and isinstance(value, str):
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
    elif not arg:
        # Replace the argument with something to prevent misinterpretation
        arg = ' '
    return arg.replace(' ', '\xa0').replace('\r', '\xa0').replace('\n', '\xa0')


# Create the IRC class
class IRC:
    connected = None
    debug_file = sys.stdout
    sendq = None
    msglen = 512
    _main_thread = None
    _sasl = False
    _unhandled_caps = None

    # This will no longer be an alias in miniirc v2.0.0.
    # This is still a property to avoid breaking miniirc_matrix
    current_nick = property(lambda self: self._current_nick)

    # For backwards compatibility, irc.nick will return the current nickname.
    # However, changing irc.nick will change the desired nickname as well
    # TODO: Consider changing what irc.nick does if it won't break anything or
    # making desired_nick public
    @current_nick.setter
    def nick(self, new_nick):
        self._desired_nick = new_nick
        self._current_nick = new_nick

    def __init__(self, ip, port, nick, channels=None, *, ssl=None, ident=None,
                 realname=None, persist=True, debug=False, ns_identity=None,
                 auto_connect=True, ircv3_caps=None, connect_modes=None,
                 quit_message='I grew sick and died.', ping_interval=60,
                 ping_timeout=None, verify_ssl=True, server_password=None,
                 executor=None):
        # Set basic variables
        self.ip = ip
        self.port = int(port)
        self.nick = nick
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
        self.server_password = server_password
        self._keepnick_active = False
        self._executor = executor

        # Set the NickServ identity
        if not ns_identity or isinstance(ns_identity, str):
            self.ns_identity = ns_identity
        else:
            self.ns_identity = ' '.join(ns_identity)

        # Set the debug file
        if not debug:
            self.debug_file = None
        elif hasattr(debug, 'write'):
            self.debug_file = debug
        elif hasattr(debug, '__call__'):
            self.debug_file = _Logfile(debug)

        # Add IRCv3 capabilities.
        if self.ns_identity:
            self.ircv3_caps.add('sasl')

        # Add handlers and set the default message parser
        self.change_parser()
        self.handlers = {}
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
    def quote(self, *msg, force=None, tags=None):
        if not tags and msg and isinstance(msg[0], dict):
            tags = msg[0]
            msg = msg[1:]
        if not self.connected and not force:
            self.debug('>Q>', *msg)
            if not self.sendq:
                self.sendq = []
            if tags:
                msg = (tags,) + msg
            self.sendq.append(msg)
            return

        if (not isinstance(tags, dict)
                or ('message-tags' not in self.active_caps and
                    'draft/message-tags-0.2' not in self.active_caps)):
            tags = None
        self.debug('>3> ' + repr(tags) if tags else '>>>', *msg)
        msg = (' '.join(msg).replace('\x00', '\ufffd').encode('utf-8')
               .replace(b'\r', b' ') .replace(b'\n', b' '))

        if len(msg) + 2 > self.msglen:
            msg = msg[:self.msglen - 2]
            if msg[-1] >= 0x80:
                msg = msg.decode('utf-8', 'ignore').encode('utf-8')

        if tags:
            msg = _dict_to_tags(tags) + msg

        # Non-blocking sockets can't use sendall() reliably
        msg += b'\r\n'
        self._send_lock.acquire()
        sent_bytes = 0
        try:  # Apparently try/finally is faster than "with".
            while True:
                try:
                    # Attempt to send to the socket
                    sent_bytes += self.sock.send(msg[sent_bytes:])
                except ssl.SSLWantReadError:
                    # Wait for the socket to become ready again
                    readable, _, _ = select.select(
                        (self.sock,), (), (self.sock,),
                        self.ping_timeout or self.ping_interval
                    )
                    continue
                except (BlockingIOError, ssl.SSLWantWriteError):
                    pass
                else:
                    # Break if enough data has been written
                    if sent_bytes >= len(msg):
                        break

                # Otherwise wait for the socket to become writable
                select.select((), (self.sock,), (self.sock,),
                              self.ping_timeout or self.ping_interval)
        except socket.timeout:
            # Abort the connection if there was a timeout because the data may
            # have been partially written
            try:
                self.sock.close()
            except OSError:
                pass

            if force:
                raise
        except (AttributeError, BrokenPipeError):
            if force:
                raise
        finally:
            self._send_lock.release()

    def send(self, *msg, force=None, tags=None):
        if len(msg) > 1:
            self.quote(*tuple(map(_prune_arg, msg[:-1])) + (':' + msg[-1],),
                       force=force, tags=tags)
        else:
            self.quote(*msg, force=force, tags=tags)

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
    def Handler(self, *events, ircv3=False, colon=True):
        return _add_handler(self.handlers, events, ircv3, False, colon)

    def CmdHandler(self, *events, ircv3=False, colon=True):
        return _add_handler(self.handlers, events, ircv3, True, colon)

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

        self._current_nick = self._desired_nick
        self._unhandled_caps = None
        if self.server_password is not None:
            self.send('PASS', self.server_password, force=True)
        self.quote('CAP LS 302', force=True)
        self.quote('USER', self.ident, '0', '*', ':' + self.realname,
                   force=True)
        self.quote('NICK', self._desired_nick, force=True)
        atexit.register(self.disconnect)
        self.debug('Starting main loop...')
        self._sasl = self._pinged = self._keepnick_active = False
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
        self._current_nick = self._desired_nick
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
    def _start_handler(self, handlers, command, hostmask, tags, args):
        r = False
        for handler in handlers:
            r = True
            params = [self, hostmask, list(args)]
            if not hasattr(handler, 'miniirc_colon') and args and \
                    args[-1].startswith(':'):
                params[2][-1] = args[-1][1:]
            if hasattr(handler, 'miniirc_ircv3'):
                params.insert(2, dict(tags))
            if hasattr(handler, 'miniirc_cmd_arg'):
                params.insert(1, command)

            if self._executor is None:
                threading.Thread(target=handler, args=params).start()
            else:
                self._executor.submit(handler, *params)
        return r

    # Launch handlers
    def _handle(self, cmd, hostmask, tags, args):
        r = False
        cmd = str(cmd).upper()
        hostmask = tuple(hostmask)
        for handlers in (_global_handlers, self.handlers):
            if cmd in handlers:
                r = self._start_handler(handlers[cmd], cmd, hostmask, tags,
                                        args)

            if None in handlers:
                self._start_handler(handlers[None], cmd, hostmask, tags, args)

        return r

    # Launch IRCv3 handlers
    def _handle_cap(self, cap):
        cap = cap.lower()
        self.active_caps.add(cap)
        if self._unhandled_caps and cap in self._unhandled_caps:
            handled = self._handle(
                'IRCv3 ' + cap, ('CAP', 'CAP', 'CAP'), {},
                self._unhandled_caps[cap]
            )
            if not handled:
                self.finish_negotiation(cap)

    # The main loop
    def _main(self):
        # Make the socket non-blocking.
        self.sock.setblocking(False)

        self.debug('Main loop running!')
        buffer = b''
        while True:
            try:
                assert len(buffer) < 65535, 'Very long line detected!'
                try:
                    # Acquire the send lock when receiving data because I don't
                    # think you're supposed to call SSL functions from multiple
                    # threads at once
                    self._send_lock.acquire()
                    try:
                        raw = self.sock.recv(8192).replace(b'\r', b'\n')
                    finally:
                        self._send_lock.release()

                    if not raw:
                        raise ConnectionAbortedError
                    buffer += raw
                except (BlockingIOError, ssl.SSLWantReadError):
                    # Wait for the socket to become ready again
                    readable, _, _ = select.select(
                        (self.sock,), (), (self.sock,),

                        # self.ping_interval should be used when
                        # self.ping_timeout is None
                        (self._pinged and self.ping_timeout or
                         self.ping_interval)
                    )

                    # Handle ping timeouts
                    if not readable:
                        if self._pinged:
                            raise TimeoutError
                        self._pinged = True
                        self.quote('PING', ':miniirc-ping', force=True)
                except ssl.SSLWantWriteError:
                    select.select((), (self.sock,), (self.sock,),
                                  self.ping_timeout or self.ping_interval)

                # Attempt to change nicknames every 30 seconds
                if (self._keepnick_active and
                        time.monotonic() > self._last_keepnick_attempt + 30):
                    self.send('NICK', self._desired_nick, force=True)
                    self._last_keepnick_attempt = time.monotonic()
            except OSError as e:
                self.debug('Lost connection!', repr(e))
                self.disconnect(auto_reconnect=True)
                while self.persist:
                    time.sleep(5)
                    self.debug('Reconnecting...')
                    try:
                        self.connect()
                    except OSError:
                        self.debug('Failed to reconnect!')
                        self.connected = None
                    else:
                        return
                return

            raw = buffer.split(b'\n')
            buffer = raw.pop()
            for line in raw:
                line = line.decode('utf-8', 'replace')

                if line:
                    self.debug('<<<', line)
                    try:
                        result = self._parse(line)
                    except Exception:
                        result = None
                    if isinstance(result, tuple) and len(result) == 4:
                        self._handle(*result)
                    else:
                        self.debug('Ignored message:', line)
            del raw

    def wait_until_disconnected(self, *, _timeout=None):
        # The main thread may be replaced on reconnects
        while self._main_thread and self._main_thread.is_alive():
            self._main_thread.join(_timeout)

    def main(self):
        warnings.warn('The miniirc.IRC.main() function is deprecated and '
                      'should not be used.', DeprecationWarning, 2)
        # The main thread may be started after the if check and before
        # _start_main_loop. This function is deprecated so fixing this probably
        # isn't worthwhile.
        if not self._main_thread or not self._main_thread.is_alive():
            self._start_main_loop()


# Handle some IRC messages by default.
@Handler('001')
def _handler(irc, hostmask, args):
    irc.connected = True
    irc.isupport.clear()
    irc._unhandled_caps = None
    irc.debug('Connected!')

    # Update the current nickname and activate keepnick if required
    irc._last_keepnick_attempt = time.monotonic()
    irc._keepnick_active = args[0] != irc._desired_nick
    irc._current_nick = args[0]

    # Apply connection modes
    if irc.connect_modes:
        irc.quote('MODE', irc.current_nick, irc.connect_modes)

    # Log into NickServ if required
    if not irc._sasl and irc.ns_identity:
        irc.debug('Logging in (no SASL, aww)...')
        irc.msg('NickServ', 'identify ' + irc.ns_identity)

    # Join channels
    if irc.channels:
        irc.debug('*** Joining channels...', irc.channels)
        irc.quote('JOIN', ','.join(irc.channels))

    # Send any queued messages
    with irc._send_lock:
        sendq, irc.sendq = irc.sendq, None
    if sendq:
        for i in sendq:
            irc.quote(*i)


@Handler('PING', colon=True)
def _handler(irc, hostmask, args):
    irc.quote('PONG', *args, force=True)


@Handler('PONG', colon=False)
def _handler(irc, hostmask, args):
    if args and args[-1] == 'miniirc-ping' and irc.ping_interval:
        irc._pinged = False


@Handler('432', '433')
def _handler(irc, hostmask, args):
    if not irc.connected:
        try:
            return int(irc._current_nick[0])
        except ValueError:
            pass
        if len(irc._current_nick) >= irc.isupport.get('NICKLEN', 20):
            return
        irc.debug('WARNING: The requested nickname', repr(irc._current_nick),
                  'is invalid. Trying again with',
                  repr(irc._current_nick + '_') + '...')
        irc._current_nick += '_'
        irc.quote('NICK', irc.current_nick, force=True)


@Handler('NICK', colon=False)
def _handler(irc, hostmask, args):
    if hostmask[0].lower() == irc._current_nick.lower():
        irc._current_nick = args[-1]

        # Deactivate keepnick if the client has the right nickname
        if irc._current_nick.lower() == irc._desired_nick.lower():
            irc._keepnick_active = False


@Handler('PRIVMSG', colon=False)
def _handler(irc, hostmask, args):
    if not version:
        return
    if args[-1].startswith('\x01VERSION') and args[-1].endswith('\x01'):
        irc.ctcp(hostmask[0], 'VERSION', version, reply=True)


# Handle IRCv3 capabilities
@Handler('CAP', colon=False)
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


@Handler('AUTHENTICATE', colon=False)
def _handler(irc, hostmask, args):
    if args and args[0] == '+':
        from base64 import b64encode
        irc._sasl = True
        pw = irc.ns_identity.split(' ', 1)
        pw = '{0}\x00{0}\x00{1}'.format(*pw).encode('utf-8')
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
            port = int(_tags_to_dict(args[1], ',')['port'])
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
    del args[0], args[-1]
    isupport = _tags_to_dict(args, None)

    # Try and auto-detect integers
    remove = set()
    for key in isupport:
        try:
            isupport[key] = int(isupport[key])

            # Disable keepnick if the nickname is too long
            if key == 'NICKLEN' and len(irc._desired_nick) > isupport[key]:
                irc._keepnick_active = False
        except ValueError:
            if key.endswith('LEN'):
                remove.add(key)
    for key in remove:
        del isupport[key]

    irc.isupport.update(isupport)


# Attempt to get the desired nickname if the user that currently has it quits
@Handler('QUIT', 'NICK')
def _handler(irc, hostmask, args):
    if (irc.connected and irc._keepnick_active and
            hostmask[0].lower() == irc._desired_nick.lower()):
        irc.send('NICK', irc._desired_nick, force=True)
        irc._last_keepnick_attempt = time.monotonic()


# Stop trying to get the desired nickname if it's invalid or if nick changes
# aren't permitted
@Handler('432', '435', '447')
def _handler(irc, hostmask, args):
    irc._keepnick_active = False


_colon_warning = True
del _handler
