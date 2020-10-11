#!/bin/false
import collections, miniirc

def test_ensure_v1():
    assert miniirc.ver <= (2, 0, 0)

if miniirc.ver >= (2, 0, 0):
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
        assert (p(hostmask_s + 'PRIVMSG #channel :Hello world!') ==
                ('PRIVMSG',  hostmask, {}, ['#channel', ':Hello world!']))

    hostmask = fill_in_hostmask('Hi', ())
    assert (p(r'@tag1=value\:\swith\s\\spaces\rand\nnewlines;tag2;tag3= Hi') ==
            ('Hi', hostmask, {'tag1': 'value; with \\spaces\rand\nnewlines',
            'tag2': True, 'tag3': True}, []))

def test_Handler():
    try:
        tmp, miniirc._global_handlers = miniirc._global_handlers, {}
        @miniirc.Handler('test', 1, ircv3=True, colon=False)
        def f(irc, hostmask, tags, args):
            ...
        assert not hasattr(f, 'miniirc_cmd_arg')
        assert not hasattr(f, 'miniirc_colon')
        assert hasattr(f, 'miniirc_ircv3')

        @miniirc.CmdHandler('test2', 2, colon=True)
        def f2(irc, command, hostmask, args):
            ...
        assert hasattr(f2, 'miniirc_colon')
        assert hasattr(f2, 'miniirc_cmd_arg')
        assert not hasattr(f2, 'miniirc_ircv3')

        @miniirc.CmdHandler()
        def f3(irc, command, hostmask, args):
            ...
        assert hasattr(f3, 'miniirc_cmd_arg')
        assert hasattr(f3, 'miniirc_colon')
        assert not hasattr(f3, 'miniirc_ircv3')

        assert miniirc._global_handlers == {
            'TEST': [f],
            '1': [f],
            'TEST2': [f2],
            '2': [f2],
            None: [f3]
        }
    finally:
        miniirc._global_handlers = tmp

def test_dict_to_tags():
    dict_to_tags = miniirc._dict_to_tags
    tags_dict = collections.OrderedDict((
        ('abc', True), ('def', False), ('ghi', ''), ('jkl', 'test\r\n; ')
    ))
    assert dict_to_tags(tags_dict) == rb'@abc;jkl=test\r\n\:\s '

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
    assert test('Hello world!') == ('Hello\xa0world!', None)
    assert (test('abc def\r\n', ':ghi', ':jkl', tags={'a': 'b'}) ==
            ('abc\xa0def\xa0\xa0 \u0703ghi ::jkl', {'a': 'b'}))

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
