#!/bin/false
import collections, functools, miniirc, pathlib, queue, random, re, socket, \
       threading, time
from miniirc import IRCMessage

MINIIRC_V2 = miniirc.ver >= (2, 0, 0)
if MINIIRC_V2:
    def fill_in_hostmask(cmd, hostmask):
        while len(hostmask) < 3:
            hostmask += ('',)
        return hostmask[:3]

    def test_fill_in_hostmask():
        assert fill_in_hostmask('A', ()) == ('', '', '')
        assert fill_in_hostmask('A', ('B',)) == ('B', '', '')
        assert fill_in_hostmask('A', ('B', 'C')) == ('B', 'C', '')
        assert fill_in_hostmask('A', ('B', 'C', 'D')) == ('B', 'C', 'D')
else:
    def fill_in_hostmask(cmd, hostmask):
        if len(hostmask) == 0:
            return (cmd, cmd, cmd)
        while len(hostmask) < 3:
            hostmask += (hostmask[-1],)
        return hostmask[:3]

    def test_fill_in_hostmask():
        assert fill_in_hostmask('A', ()) == ('A', 'A', 'A')
        assert fill_in_hostmask('A', ('B',)) == ('B', 'B', 'B')
        assert fill_in_hostmask('A', ('B', 'C')) == ('B', 'C', 'C')
        assert fill_in_hostmask('A', ('B', 'C', 'D')) == ('B', 'C', 'D')

def test_message_parser():
    p = miniirc.ircv3_message_parser
    for i in range(4):
        hostmask = fill_in_hostmask('PRIVMSG', ('n', 'u', 'h')[:i])
        hostmask_s = ':n!u@h'[:i * 2] + (' ' if i else '')
        if MINIIRC_V2:
            assert (p(hostmask_s + 'PRIVMSG #channel :Hello world!') ==
                    IRCMessage('PRIVMSG', hostmask, {},
                               ['#channel', 'Hello world!']))
        else:
            assert (p(hostmask_s + 'PRIVMSG #channel :Hello world!') ==
                    ('PRIVMSG', hostmask, {}, ['#channel', ':Hello world!']))

    hostmask = fill_in_hostmask('Hi', ())
    empty_tag = '' if MINIIRC_V2 else True
    assert (p(r'@tag1=value\:\swith\s\\spaces\rand\nnewlines;tag2;tag3= Hi') ==
            ('HI' if MINIIRC_V2 else 'Hi', hostmask,
             {'tag1': 'value; with \\spaces\rand\nnewlines', 'tag2': empty_tag,
              'tag3': empty_tag}, []))

if MINIIRC_V2:
    def verify_handler(event, cmdhandler, colon, ircv3):
        handler = miniirc._global_handlers[event][-1]
        assert handler.cmdhandler == cmdhandler
        assert not colon
        assert handler.ircv3 == ircv3
        assert handler.run_in_thread
else:
    def verify_handler(event, cmdhandler, colon, ircv3):
        func = miniirc._global_handlers[event][-1]
        assert hasattr(func, 'miniirc_colon') == colon
        assert hasattr(func, 'miniirc_cmd_arg') == cmdhandler
        assert hasattr(func, 'miniirc_ircv3') == ircv3

def test_Handler(monkeypatch):
    if not MINIIRC_V2:
        monkeypatch.setattr(miniirc, '_colon_warning', False)
    try:
        tmp, miniirc._global_handlers = miniirc._global_handlers, {}
        @miniirc.Handler('test', 1, ircv3=True, colon=False)
        def f(irc, hostmask, tags, args):
            ...
        verify_handler('TEST', False, False, True)

        if not MINIIRC_V2:
            @miniirc.CmdHandler('test2', 2, colon=True)
            def f2(irc, command, hostmask, args):
                ...
            verify_handler('2', True, True, False)

        @miniirc.CmdHandler()
        def f3(irc, command, hostmask, args):
            ...
        verify_handler(None, True, not MINIIRC_V2, False)

        expected = {
            'TEST': [f],
            '1': [f],
            None: [f3]
        }

        if MINIIRC_V2:
            assert miniirc._global_handlers.keys() == expected.keys()
        else:
            expected['2'] = expected['TEST2'] = [f]
            assert miniirc._global_handlers == expected
    finally:
        miniirc._global_handlers = tmp

def test_version():
    setup_py = pathlib.Path(__file__).resolve().parent / 'setup.py'
    with setup_py.open() as f:
        match = re.search(r"version *= '([0-9\.a-z]+)',", f.read())
    assert match
    assert miniirc.__version__ == match.group(1)

    assert ('.'.join(map(str, miniirc.ver[:3])) + ''.join(miniirc.ver[3:])
            == miniirc.__version__)
    assert miniirc.version == 'miniirc IRC framework v' + miniirc.__version__

def test_dict_to_tags():
    dict_to_tags = miniirc._dict_to_tags
    tags_dict = collections.OrderedDict((
        ('abc', True), ('def', False), ('ghi', ''), ('jkl', 'test\r\n; ')
    ))
    assert dict_to_tags(tags_dict) == rb'@abc;ghi;jkl=test\r\n\:\s '

def test_logfile():
    msgs = []
    logfile = miniirc._Logfile(msgs.append)
    logfile.write('Hello world!\nThis is a test\rmessage\nto test the ')
    logfile.write('_Logfile class.')
    logfile.write('\n')
    print('This is', 'the final line', file=logfile)
    assert msgs == [
        'Hello world!',
        'This is a test\rmessage',
        'to test the _Logfile class.',
        'This is the final line'
    ]

class DummyIRC(miniirc.IRC):
    def __init__(self, ip='', port=0, nick='', *args, **kwargs):
        kwargs['auto_connect'] = False
        super().__init__(ip, port, nick, *args, **kwargs)

class IRCQuoteWrapper(DummyIRC):
    res = None
    TEST_FUNC = 'quote'
    def quote(self, *args, force=None, tags=None):
        assert self.res is None
        self.res = (' '.join(args), tags)

    @classmethod
    def test(cls, *args, **kwargs):
        self = cls()
        getattr(self, cls.TEST_FUNC)(*args, **kwargs)
        return self.res

    @classmethod
    def make_test(cls, test_func):
        class res(cls):
            TEST_FUNC = test_func
        res.__name__ = res.__qualname__ = 'test_' + test_func
        return res.test

def test_irc_send():
    test = IRCQuoteWrapper.make_test('send')
    assert test('a') == ('a', None)
    assert test('a', 'Hello world!', 'b') == ('a Hello\xa0world! :b', None)
    assert (test('', 'abc def\r\n', ':ghi', ':jkl', tags={'a': 'b'}) ==
            (' abc\xa0def\xa0\xa0 \u0703ghi ::jkl', {'a': 'b'}))

irc_msg_funcs = {
    'msg': 'PRIVMSG {} :{}',
    'notice': 'NOTICE {} :{}',
    'ctcp': 'PRIVMSG {} :\x01{}\x01',
    'me': 'PRIVMSG {} :\x01ACTION {}\x01'
}
def test_irc_msg_funcs():
    for func, fmt in irc_msg_funcs.items():
        test = IRCQuoteWrapper.make_test(func)
        assert test('abc', ':def') == (fmt.format('abc', ':def'), None)
        assert (test('target', 'hello', 'world', tags={'abc': 'def'}) ==
            (fmt.format('target', 'hello world'), {'abc': 'def'}))

class FakeExecutor:
    submissions = 0
    def submit(self, *args):
        assert args == self.expected_args
        self.submissions += 1

def test_executor(monkeypatch):
    if not MINIIRC_V2:
        monkeypatch.setattr(miniirc, '_colon_warning', False)
    executor = FakeExecutor()
    irc = DummyIRC(executor=executor)
    def fake_handler():
        pass
    executor.expected_args = (fake_handler, irc, ('a', 'b', 'c'), ['d'])
    irc.Handler('test')(fake_handler)
    if MINIIRC_V2:
        irc.handle_msg(IRCMessage('TEST', ('a', 'b', 'c'), {}, ['d']))
    else:
        irc._handle('test', ('a', 'b', 'c'), {}, ['d'])
    assert executor.submissions == 1

def test_change_parser():
    irc = DummyIRC()
    assert irc._parse == miniirc.ircv3_message_parser
    def f(msg):
        ...
    irc.change_parser(f)
    assert irc._parse == f

def test_get_ca_certs():
    try:
        import certifi
    except ImportError:
        assert miniirc.get_ca_certs() is None
    else:
        assert miniirc.get_ca_certs() == certifi.where()

def test_start_main_loop(monkeypatch):
    irc = DummyIRC()
    thread = None
    event = threading.Event()

    def main(self):
        nonlocal thread
        assert self is irc
        thread = threading.current_thread()
        event.set()

    monkeypatch.setattr(DummyIRC, '_main', main)

    assert irc._main_thread is None
    irc._start_main_loop()
    main_thread = irc._main_thread
    assert event.wait(1)
    assert main_thread is irc._main_thread is thread
    assert not hasattr(irc, '_main_lock')

def test_connection(monkeypatch):
    irc = err = None

    # Prevent miniirc catching fakesocket errors
    def catch_errors(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            nonlocal err
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                err = err or e
                if MINIIRC_V2:
                    self._sock.close()
                else:
                    self.sock.close()
        return wrapper

    fixed_responses = {
        'CAP LS 302': 'CAP * LS :abc sasl account-tag',
        'CAP REQ :account-tag sasl': 'CAP miniirc-test ACK :sasl account-tag',
        'CAP REQ :sasl account-tag': 'CAP miniirc-test ACK :account-tag sasl',
        'AUTHENTICATE PLAIN': 'AUTHENTICATE +',
        'AUTHENTICATE dGVzdAB0ZXN0AGh1bnRlcjI=': '903',
        'CAP END': (
            '001 parameter test :with colon\n'
            '005 * CAP=END :isupport description\n'
        ),
        'USER miniirc-test 0 * :miniirc-test':
            ':a PRIVMSG miniirc-test :\x01VERSION\x01',
        'NICK miniirc-test': '432',
        'NICK miniirc-test_': '',
        'NOTICE a :\x01VERSION ' + miniirc.version + '\x01':
            '005 miniirc-test CTCP=VERSION :are supported by this server',
        'QUIT :I grew sick and died.': '',
    }

    class fakesocket(socket.socket):
        @catch_errors
        def __init__(self, __family, __type, *args):
            assert __family in (socket.AF_INET, socket.AF_INET6)
            assert __type == socket.SOCK_STREAM

        @catch_errors
        def connect(self, __addr):
            assert __addr[1] == 6667
            self._recvq = queue.Queue()

        @catch_errors
        def send(self, data):
            raise ValueError('socket.send() used in place of socket.sendall()')

        @catch_errors
        def sendall(self, data):
            msg = data.decode('utf-8')
            assert msg.endswith('\r\n')
            msg = msg[:-2]
            assert msg in fixed_responses
            if self._recvq is None:
                return
            for line in fixed_responses[msg].split('\n'):
                self._recvq.put(line.encode('utf-8') +
                    random.choice((b'\r', b'\n', b'\r\n', b'\n\r')))

        @catch_errors
        def recv(self, chunk_size):
            assert chunk_size == 8192
            if err is not None or self._recvq is None:
                return b''
            else:
                return self._recvq.get()

        def close(self):
            nonlocal err
            err = err or BrokenPipeError('Socket closed')
            event.set()
            if self._recvq:
                self._recvq.put(b'')
                self._recvq = None

        def settimeout(self, t):
            assert t == 60

    monkeypatch.setattr(socket, 'socket', fakesocket)

    try:
        event = threading.Event()
        irc = miniirc.IRC('example.com', 6667, 'miniirc-test',
            auto_connect=False, ns_identity=('test', 'hunter2'), persist=False,
            debug=True)
        assert irc.connected is None
        @irc.Handler('001', colon=False)
        @catch_errors
        def _handle_001(irc, hostmask, args):
            for i in range(100):
                if 'CAP' in irc.isupport and 'CTCP' in irc.isupport:
                    break
                time.sleep(0.001)
            assert args == ['parameter', 'test', 'with colon']
            assert irc.isupport == {'CTCP': 'VERSION', 'CAP': 'END'}
            event.set()

        irc.connect()
        assert event.wait(3) or err is not None
        if err is not None:
            raise err
        assert irc.connected
        if MINIIRC_V2:
            assert irc.nick == 'miniirc-test'
            assert irc.current_nick == 'miniirc-test_'
        else:
            assert irc.nick == irc.current_nick == 'miniirc-test_'
    finally:
        irc.disconnect()
