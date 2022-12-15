# miniirc

[![Python 3.4+]](#python-version-support) [![Available on PyPI.]](https://pypi.org/project/miniirc/) [![License: MIT]](https://github.com/luk3yx/miniirc/blob/master/LICENSE.md)

A relatively simple thread-safe(-ish) IRC client framework.

To install miniirc, simply run `pip3 install miniirc`.

If you have previously used miniirc, you may want to read the
[deprecations list] (last updated 2020-04-28).

*This repository is available on both [GitHub](https://github.com/luk3yx/miniirc) and [GitLab](https://gitlab.com/luk3yx/miniirc).*

[Python 3.4+]: https://img.shields.io/badge/python-3.4+-blue.svg
[Available on PyPI.]: https://img.shields.io/pypi/v/miniirc.svg
[License: MIT]: https://img.shields.io/pypi/l/miniirc.svg
[deprecations list]: #deprecations

## Parameters

```py
irc = miniirc.IRC(ip, port, nick, channels=None, *, ssl=None, ident=None, realname=None, persist=True, debug=False, ns_identity=None, auto_connect=True, ircv3_caps=set(), quit_message='I grew sick and died.', ping_interval=60, ping_timeout=None, verify_ssl=True, executor=None)
```

*Note that everything before the \* is a positional argument.*

### Typical usage

You don't need to add every argument, and the `ip`, `port`, `nick`, and
`channels` arguments should be specified as positional arguments.

```py
irc = miniirc.IRC('irc.example.com', 6697, 'my-bot', ['#my-channel'], ns_identity=('my-bot', 'hunter2'), executor=concurrent.futures.ThreadPoolExecutor())
```

If you are not doing anything with the main thread after connecting to IRC,
please call `irc.wait_until_disconnected()` to prevent Python from trying to
shut down while miniirc is still connected, breaking thread pools (in
Python 3.9 and later).

```py
irc.wait_until_disconnected()
```

### Parameter descriptions

| Parameter     | Description                                                |
| ------------- | -------------------------------------------------------- |
| `ip`          | The IP/hostname of the IRC server to connect to.          |
| `port`        | The port to connect to.                                   |
| `nick`        | The nickname of the bot.                                  |
| `channels`    | The channels to join on connect. This can be an iterable containing strings (list, set, etc), or (since v1.5.0) a comma-delimited string. |
| `ssl`         | Enable TLS/SSL. If `None`, TLS is disabled unless the port is `6697`. |
| `ident`       | The ident to use, defaults to `nick`.                     |
| `realname`    | The realname to use, defaults to `nick` as well.          |
| `persist`     | Whether to automatically reconnect.                       |
| `debug`       | Enables debug mode, prints all IRC messages. This can also be a file-like object (with write mode enabled) if you want debug messages to be written into a file instead of being printed to stdout, or a function (for example `logging.debug`). |
| `ns_identity` | The NickServ account to use as a tuple/list of length 2 (`('<user>', '<password>')`). For compatibility, this can be a string (`'<user> <password>'`). |
| `auto_connect`| Runs `irc.connect()` straight away.                          |
| `ircv3_caps`  | A set() of additional IRCv3 capabilities to request. SASL is auto-added if `ns_identity` is specified. |
| `connect_modes` | A mode string (for example `'+B'`) of UMODEs to set when connected. |
| `quit_message`| Sets the default quit message. This can be modified per-quit with `irc.disconnect()`. |
| `ping_interval` | If no packets are sent or received for this amount of seconds, miniirc will send a `PING`, and if no reply is sent, after the ping timeout, miniirc will attempt to reconnect. Set to `None` to disable. |
| `ping_timeout` | The ping timeout used alongside the above `ping_interval` option, if unspecified will default to `ping_interval`. |
| `verify_ssl`  | Verifies TLS/SSL certificates. Disabling this is not recommended as it opens the IRC connection up to MiTM attacks. If you have trouble with certificate verification, try running `pip3 install certifi` first. |
| `executor`    | An instance of `concurrent.futures.ThreadPoolExecutor` to use when running handlers. |

*The only mandatory parameters are `ip`, `port`, and `nick`.*

## Functions

| Function      | Description                                               |
| ------------- | --------------------------------------------------------  |
| `change_parser(parser=...)` | *See the message parser section for documentation.* |
| `connect()`   | Connects to the IRC server if not already connected.      |
| `ctcp(target, *msg, reply=False, tags=None)` | Sends a `CTCP` request or reply to `target`. |
| `debug(...)`  | Debug, calls `print(...)` if debug mode is on.            |
| `disconnect(msg=..., *, auto_reconnect=False)`| Disconnects from the IRC server. `auto_reconnect` will be overridden by `self.persist` if set to `True`. |
| `Handler(...)` | An event handler, see [Handlers](#handlers) for more info. |
| `me(target, *msg, tags=None)`        | Sends a `/me` (`CTCP ACTION`) to `target`.  |
| `msg(target, *msg, tags=None)`       | Sends a `PRIVMSG` to `target`. `target` should not contain spaces or start with a colon. |
| `notice(target, *msg, tags=None)`    | Sends a `NOTICE` to `target`. `target` should not contain spaces or start with a colon. |
| `quote(*msg, force=False, tags=None)` | Sends a raw message to IRC, use `force=True` to send while disconnected. Do not send multiple commands in one `irc.quote()`, as the newlines will be stripped and it will be sent as one command. The `tags` parameter optionally allows you to add a `dict` with IRCv3 client tags (all starting in `+`), and will not be sent to IRC servers that do not support client tags. |
| `send(*msg, force=False, tags=None)` | Sends a command to the IRC server, treating every positional argument as a parameter. The usage of this is recommended over `irc.quote()` unless you know what you are doing. |
| `wait_until_disconnected()` | Waits until the IRC server is disconnected and automatic reconnecting is turned off. |

*Note that if `force=False` on `irc.quote` (or `irc.msg` etc is called) while
miniirc is not connected, messages will be temporarily stored and then sent
once miniirc is connected. Setting `force=True` will throw errors if miniirc is
completely disconnected (`irc.connected` is `None`).*

### irc.quote and irc.send

The two functions `irc.quote` and `irc.send` may sound similar, however are
fundamentally different: `irc.quote()` joins all provided arguments with spaces
and sends them as a raw message to IRC, while `irc.send()` treats each argument
as a parameter. If arguments passed to `irc.send()` contain spaces, they are
replaced with U+00A0 (a non-breaking space, visually similar to a regular
space however not interpreted as one).

#### Examples

 - `irc.quote('PRIVMSG', '#channel :Hello,', 'world!')` sends "Hello, world!"
    to #channel.
 - `irc.quote('PRIVMSG', '#channel', 'Hello, world!')` is invalid ("Hello," and
    "world!" are sent as separate parameters).
 - `irc.send('PRIVMSG', '#channel', 'Hello, world!')` will send "Hello, world!"
    to "#channel".
 - `irc.send('PRIVMSG', '#channel :Hello,', 'world!')` will send "world!" to
    `#channel\xa0:Hello,`, where `\xa0` is a non-breaking space.

*If you are unsure and do not need compatibility with miniirc <1.5.0, use
`irc.send()`. `PRIVMSG` is just used as an example, if you need to send
`PRIVMSG`s use `irc.msg()` instead.*

## Variables

*These variables should not be changed outside `miniirc.py`.*

| Variable      | Description                                               |
| ------------- | --------------------------------------------------------  |
| `active_caps` | A `set` of IRCv3 capabilities that have been successfully negotiated with the IRC server. This is empty while disconnected. |
| `connected`   | A boolean (or `None`), `True` when miniirc is connected, `False` when miniirc is connecting, and `None` when miniirc is not connected. |
| `current_nick` | The bot/client's current nickname. Do not modify this, and use this instead of `irc.nick` when getting the bot's current nickname. |
| `isupport`    | A `dict` with values (not necessarily strings) from `ISUPPORT` messages sent to the client. |
| `msglen`      | The maximum length (in bytes) of messages (including `\r\n`). This is automatically changed if the server supports the `oragono.io/maxline-2` capability. |
| `nick`        | The nickname to use when connecting to IRC. Until miniirc v2.0.0, you should only use or modify this while disconnected, as it is currently automatically updated with nickname changes. |

The following arguments passed to `miniirc.IRC` are also available: `ip`,
`port`, `channels`, `ssl`, `ident`, `realname`, `persist`, `connect_modes`,
`quit_message`, `ping_interval`, `verify_ssl`.

## Handlers

`miniirc.Handler` and `miniirc.CmdHandler` are function decorators that add
functions to an event handler list. Functions in this list are called in their
own thread when their respective IRC event(s) is/are received. Handlers may
work on every IRC object in existence (`miniirc.Handler`) or only on
specific IRC objects (`irc.Handler`).

The basic syntax for a handler is as followed, where `*events` is a list of events (`PRIVMSG`, `NOTICE`, etc) are called.

```py
import miniirc
@miniirc.Handler(*events, colon=False)
def handler(irc, hostmask, args):
    # irc:      An 'IRC' object.
    # hostmask: A 'hostmask' object.
    # args:     A list containing the arguments sent to the command. Everything
    #             following the first `:` in the command is put into one item
    #             (args[-1]). If "colon" is "False", the leading ":" (if any)
    #             is automatically removed. To prevent your code from horribly
    #             breaking, always set it to False unless you know what you are
    #             doing.
    pass
```

#### Recommendations when using handlers:

 - If you don't need support for miniirc <1.4.0 and are parsing the last
    parameter, setting `colon` to `False` is strongly recommended. If the
    `colon` parameter is omitted, it defaults to `True`, however this will
    change when miniirc v2.0.0 is released.
 - Although `Handler` and `CmdHandler` currently accept any object that can be
    converted to a string, every event is converted to a string internally.
 - Not specifying the [`ircv3`](#ircv3-tags) parameter when it is not required
    prevents a redundant `dict` from being created.
 - To add handlers to a specific `IRC` object and not every one in existence,
    use `irc.Handler` and `irc.CmdHandler` instead. If you want to create a
    `Bot` or `Client` class and automatically add handlers to `IRC` objects
    created inside it, see
    [making existing functions handlers](#making-existing-functions-handlers).

### Hostmask object

Hostmasks are tuples with the format `('user', 'ident', 'hostname')`. If `ident`
and `hostname` aren't sent from the server, they will be filled in with the
previous value. If a command is received without a hostmask, all the `hostmask`
elements will be set to the name of the command. This is deprecated, however,
and when miniirc v2.0.0 is released the `hostmask` elements will be set to
empty strings.

### Making existing functions handlers

You can make existing functions handlers (for example class instance methods)
with `irc.Handler(*events)(handler_function)`. You probably don't want to use
`miniirc.Handler` for class instance methods, as this will create a handler
that gets triggered for every `IRC` object.

You can also add multiple handlers of the same type easily:

```py
add_handler = irc.Handler('PRIVMSG', colon=False)
add_handler(handler_1)
add_handler(self.instance_handler)
```

This is useful if you want to create a `Bot` (or `Client`) class and add
class-specific handlers without creating global process-wide handlers or
creating a wrapper function for every class instance.

### IRCv3 support

#### IRCv3 tags

If you want your handler to support IRCv3 message tags, you need to add
`ircv3=True` to the `Handler` or `CmdHandler` decorator. You will need to add a
`tags` parameter to your function after `hostmask`. IRCv3 tags are sent to the
handlers as `dict`s, with values of either strings or `True`.

*miniirc will automatically un-escape IRCv3 tag values.*

```py
import miniirc
@miniirc.Handler(*events, colon=False, ircv3=True)
def handler(irc, hostmask, tags, args):
    pass
```

#### IRCv3 capabilities

You can handle IRCv3 capabilities before connecting using a handler.
You must use `force=True` on any `irc.quote()` called here, as when this is
called, miniirc may not yet be fully connected. Do not use the `colon` argument
for `Handler` when creating these handlers to avoid unexpected side-effects.

```py
import miniirc
@miniirc.Handler('IRCv3 my-cap-name')
def handler(irc, hostmask, args):
    # Process the capability here

    # IRCv3.2 capabilities:
    #   args = ['my-cap-name', 'IRCv3.2-parameters']

    # IRCv3.1 capabilities:
    #   args = ['my-cap-name']

    # Remove the capability from the processing list.
    irc.finish_negotiation(args[0]) # This can also be 'my-cap-name'.
```

### Custom message parsers (not recommended)

If the IRC server you are connecting to supports a non-standard message syntax, you can
create custom message parsers. These are called with the raw message (as a `str`) and
can either return `None` to ignore the message or a 4-tuple (`cmd, hostmask, tags, args`)
that will then be sent on to the handlers. The items in this 4-tuple should be the same
type as the items expected by handlers (and `cmd` should be a string).

#### Message parser example

This message parser makes the normal parser allow `~` as an IRCv3 tag prefix character.

```py
import miniirc

def my_message_parser(msg):
    if msg.startswith('~'):
        msg = '@' + msg[1:]
    return miniirc.ircv3_message_parser(msg)
```

#### Changing message parsers

To change message parsers, you can use `irc.change_parser(func=...)`. If `func` is not
specified, it will default to the built-in parser. You can only change message parsers
on-the-fly (for example in an IRCv3 CAP handler). If you need to change message parsers
before connecting, you can disable `auto_connect` and change it then.

```py
irc = miniirc.IRC(..., auto_connect=False)
irc.change_parser(my_message_parser)
irc.connect()
```

### Handling multiple events

If you want to handle multiple events and/or be able to get the name of the
event being triggered, you can use `irc.CmdHandler`. This will pass an extra
`command` argument to the handler function (between `irc` and `hostmask`),
containing a string with the command name (such as `PRIVMSG`).

#### Catch-all handlers

**Please do not use these unless there is no other alternative.**

If you want to handle *every* event, you can use catch-all handlers. To create
these, you can call `irc.CmdHandler()` *without* any parameters. Note that this
handler will be called many times while connecting (and once connected).

*You cannot call `irc.Handler()` without parameters.*

### Example

```py
import miniirc

# Not required, however this makes sure miniirc isn't outdated.
assert miniirc.ver >= (1,8,2)

@miniirc.Handler('PRIVMSG', 'NOTICE', colon=True)
def handler(irc, hostmask, args):
    print(hostmask[0], 'sent a message to', args[0], 'with content', args[1])
    # nickname sent a message to #channel with content :Hello, world!

@miniirc.CmdHandler('PRIVMSG', 'NOTICE', colon=False)
def cmdhandler(irc, command, hostmask, args):
    print(hostmask[0], 'sent a', command, 'to', args[0], 'with content',
        args[1])
    # nickname sent a PRIVMSG to #channel with content Hello, world!
```

This will print a line whenever the bot gets a `PRIVMSG` or `NOTICE`.

## Misc functions

miniirc provides the following helper functions:

| Name                          | Description                               |
| ----------------------------- | ----------------------------------------- |
| `miniirc.get_ca_certs()`      | Runs `certifi.where()` if `certifi` is installed, otherwise returns `None`. |
| `miniirc.ircv3_message_parser(msg)` | The default IRCv2/IRCv3 message parser, returns `cmd, hostmask, tags, args`. |
| `miniirc.ver`                 | A tuple containing version information.   |
| `miniirc.version`             | The `CTCP VERSION` reply, can be changed. |

The version numbering system should be similar to [SemVer](https://semver.org/),
however backwards compatibility is preserved where possible when major releases
change.

## Python version support

 - Python 3.3 and below are unsupported and do not work with miniirc.
 - Python 3.4, 3.5, and 3.6 are currently supported, but support will likely be
   dropped in miniirc v2.1.0. Major bugfixes may be backported to v2.0 for a
   few months after v2.1's release.
 - Python 3.7 and above should work with the latest stable version of miniirc.

If there is a bug/error in Python 3.4 or newer, please open an issue or pull
request on [GitHub](https://github.com/luk3yx/miniirc/issues) or
[GitLab](https://gitlab.com/luk3yx/miniirc/issues).

*If you are using Python 3.7 or an older version of Python, I strongly
recommend updating. Later versions of Python include features such as f-strings
that make software development easier.*

## miniirc_extras

If you want more advanced(-ish) features such as user tracking, you can use
[miniirc_extras](https://pypi.org/project/miniirc-extras/)
([GitHub](https://github.com/luk3yx/miniirc_extras),
[GitLab](https://gitlab.com/luk3yx/miniirc_extras)). Note that miniirc_extras
is still in beta and there will be breaking API changes in the future.

## Deprecations

If miniirc v2.0.0 is ever released, the following breaking changes will
(probably) be made:

 - Internal-only attributes `irc.handlers`, `irc.sock`, and `irc.sendq`
    (please do not use these) will be renamed. Again, please do not use these.
 - `irc.nick` will always be the nickname used when connecting to IRC rather
    than the current nickname, use `irc.current_nick` for the current nickname
    (since v1.4.3).
 - `irc.ns_identity` will be stored as a tuple instead of a string, for example
    `('username', 'password with spaces')` instead of
    `'username password with spaces'`. Both formats are currently accepted and
    will be accepted in the `ns_identity` keyword argument.
 - No exceptions will be raised in `irc.quote`/`irc.send` with `force=True`
    when the socket is closed. Instead of relying on these exceptions, use
    `irc.connected` which is set to `None` when completely disconnected.
 - As stated in the Python version support section, Python 3.4 support will be
    dropped in miniirc v2.1.0, however bugfixes will be backported for a few
    months.
 - The `colon` keyword argument to `Handler` and `CmdHandler` will default to
    `False` instead of `True`.
 - Unspecified hostmasks will be an empty string instead of the command. Don't
    rely on this "feature" if possible, simply ignore the hostmask if you do
    not need it.
 - The `extended-join` capability will be requested by default, use `args[0]`
    instead of `args[-1]` to get the channel from a `JOIN` event.
 - The `tags` keyword argument will be read-only.

## Working examples/implementations

Here is a list of some (open-source) bots using miniirc, in alphabetical order:

 - [irc-rss-feed-bot] - Posts RSS entry titles and shortened URLs to IRC
    channels. *Python 3.8+*
 - [irc-url-title-bot] - Gets webpage titles from URLs posted in IRC channels.
    *Python 3.8+*
 - [lurklite] - A generic configurable IRC bot.
    *[GitHub](https://github.com/luk3yx/lurklite) link.*
 - [stdinbot] - A very simple bot that dumps stdin to an IRC channel.
    *[GitHub](https://github.com/luk3yx/stdinbot) link.*

*Want to add your own bot/client to this list? Open an issue on
[GitHub](https://github.com/luk3yx/miniirc/issues) or
[GitLab](https://gitlab.com/luk3yx/miniirc/issues).*

[irc-rss-feed-bot]:  https://github.com/impredicative/irc-rss-feed-bot
[irc-url-title-bot]: https://github.com/impredicative/irc-url-title-bot
[lurklite]:          https://gitlab.com/luk3yx/lurklite
[stdinbot]:          https://gitlab.com/luk3yx/stdinbot
