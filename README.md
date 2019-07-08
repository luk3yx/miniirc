# miniirc

[![Python 3.4+]](#python-version-support) [![Available on PyPI.]](https://pypi.org/project/miniirc/) [![License: MIT]](https://github.com/luk3yx/miniirc/blob/master/LICENSE.md)

A simple IRC client framework.

To install miniirc, simply run `pip3 install miniirc` as root.

[Python 3.4+]: https://img.shields.io/badge/python-3.4/3.5+-blue.svg
[Available on PyPI.]: https://img.shields.io/pypi/v/miniirc.svg
[License: MIT]: https://img.shields.io/pypi/l/miniirc.svg

## Parameters

~~~py
irc = miniirc.IRC(ip, port, nick, channels=None, *, ssl=None, ident=None, realname=None, persist=True, debug=False, ns_identity=None, auto_connect=True, ircv3_caps=set(), quit_message='I grew sick and died.', ping_interval=60, verify_ssl=True)
~~~

*Note that everything before the \* is a positional argument.*

| Parameter     | Description                                                |
| ------------- | -------------------------------------------------------- |
| `ip`          | The IP/hostname of the IRC server to connect to.          |
| `port`        | The port to connect to.                                   |
| `nick`        | The nickname of the bot.                                  |
| `channels`    | The channels to join on connect. This can be an iterable containing strings (list, set, etc), or (since v1.4.0) a string. |
| `ssl`         | Enable TLS/SSL. If `None`, TLS/SSL is disabled unless the port is `6697`. |
| `ident`       | The ident to use, defaults to `nick`.                     |
| `realname`    | The realname to use, defaults to `nick` as well.          |
| `persist`     | Whether to automatically reconnect.                       |
| `debug`       | Enables debug mode, prints all IRC messages. This can also be a file-like object (with write mode enabled) if you want debug messages to be written into a file instead of being printed to stdout, or a function (for example `logging.debug`). |
| `ns_identity` | The NickServ account to use (`<user> <password>`). This can be a tuple or list since miniirc v1.2.0, however for backwards compatibility it should probably be a string. |
| `auto_connect`| Runs `.connect()` straight away.                          |
| `ircv3_caps`  | A set() of additional IRCv3 capabilities to request. SASL is auto-added if `ns_identity` is specified. |
| `connect_modes` | A mode string (for example `'+B'`) of UMODEs to set when connected. |
| `quit_message`| Sets the default quit message. This can be modified per-quit with `irc.disconnect()`. |
| `ping_interval` | If no packets are sent or received for this amount of seconds, miniirc will send a `PING`, and if no reply is sent, after the same timeout, miniirc will attempt to reconnect. Set to `None` to disable. |
| `verify_ssl`  | Verifies TLS/SSL certificates. Disabling this is not recommended. If you have trouble with certificate verification, try running `pip3 install certifi` first. |

## Functions

| Function      | Description                                               |
| ------------- | --------------------------------------------------------  |
| `change_parser(parser=...)` | *See the message parser section for documentation.* |
| `connect()`   | Connects to the IRC server if not already connected.      |
| `ctcp(target, *msg, reply=False, tags=None)` | Sends a `CTCP` request or reply to `target`. |
| `debug(...)`  | Debug, calls `print(...)` if debug mode is on.            |
| `disconnect(msg=..., *, auto_reconnect=False)`| Disconnects from the IRC server. `auto_reconnect` will be overriden by `self.persist` if set to `True`. |
| `Handler(...)` | An event handler, see [Handlers](#handlers) for more info.|
| `me(target, *msg, tags=None)`        | Sends a `/me` (`CTCP ACTION`) to `target`.  |
| `msg(target, *msg, tags=None)`       | Sends a `PRIVMSG` to `target`.              |
| `notice(target, *msg, tags=None)`    | Sends a `NOTICE` to `target`.               |
| `quote(*msg, force=False, tags=None)` | Sends a raw message to IRC, use `force=True` to send while disconnected. Do not send multiple commands in one `irc.quote()`, as the newlines will be stripped and it will be sent as one command. The `tags` parameter optionally allows you to add a `dict` with IRCv3 client tags (all starting in `+`), and will not be sent to IRC servers that do not support client tags. |

*Note that if `force=False` on `irc.quote` (or `irc.msg` etc is called) while
miniirc is not connected, messages will be temporarily stored and then sent
once miniirc is connected.*

## Variables

*These variables should not be changed outside `miniirc.py`.*

| Variable      | Description                                               |
| ------------- | --------------------------------------------------------  |
| `isupport`    | *New in 1.1.0.* A `dict` with values (not necessarily strings) from `ISUPPORT` messages sent to the client. |
| `msglen`      | *New in 1.1.0.* The maximum length (in bytes) of messages (including `\r\n`). This is automatically changed if the server supports the `oragono.io/maxline-2` capability. |
| `nick`        | The current nickname.                                     |

## Handlers

`miniirc.Handler` and `miniirc.CmdHandler` are function decorators that add
functions to an event handler list. Functions in this list are called in their
own thread when their respective IRC event(s) is/are received. Handlers may
work on every IRC object in existence (`@miniirc.handler`) or only on
specific IRC objects (`@miniirc.IRC().handler`).

The basic syntax for a handler is as followed, where `*events` is a list of events (`PRIVMSG`, `NOTICE`, etc) are called.

~~~py
import miniirc
@miniirc.Handler(*events, colon=True)
def handler(irc, hostmask, args):
    # irc:      An 'IRC' object.
    # hostmask: A 'hostmask' object.
    # args:     A list containing the arguments sent to the command. Everything
    #             following the first `:` in the command is put into one item
    #             (args[-1]). If "colon" is "False", the leading ":" (if any)
    #             is automatically removed. Setting this to False is probably
    #             a good idea to prevent unexpected side effects.
    pass
~~~

Recommendations when using handlers:
 - If you don't need support for miniirc <1.4.0 and are parsing the last
    parameter, setting `colon` to `False` is strongly recommended. If the
    `colon` parameter is omitted, it defaults to `True`, however this may change
    if/when miniirc v2.0.0 is released.
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

Hostmasks are tuples with the format `('user', 'ident', 'hostname')`. If `ident` and `hostname` aren't sent from the server, they will be filled in with the previous value. If a command is received without a hostmask, all the `hostmask` parameters will be set to the name of the command.

### Making existing functions handlers

You can make existing functions handlers (for example class instance methods)
with `irc.Handler(*events)(handler_function)`. You probably don't want to use
`miniirc.Handler` for class instance methods, as this will create a handler
that gets triggered for every `IRC` object.

You can also add multiple handlers of the same type easily:

```py
add_handler = irc.Handler('PRIVMSG')
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

~~~py
import miniirc
@miniirc.Handler(*events, colon=False, ircv3=True)
def handler(irc, hostmask, tags, args):
    pass
~~~

#### IRCv3 capabilities

You can handle IRCv3 capabilities before connecting using a handler.
You must use `force=True` on any `irc.quote()` called here, as when this is
called, miniirc may not yet be fully connected. Do not use the `colon` argument
for `Handler` when creating these handlers to avoid unexpected side-effects.

~~~py
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
~~~

### Custom message parsers

If the IRC server you are connecting to supports a non-standard message syntax, you can
create custom message parsers. These are called with the raw message (as a `str`) and
can either return `None` to ignore the message or a 4-tuple (`cmd, hostmask, tags, args`)
that will then be sent on to the handlers. The items in this 4-tuple should be the same
type as the items expected by handlers (and `cmd` should be a string).

#### Message parser example

This message parser makes the normal parser allow `~` as an IRCv3 tag prefix character.

~~~py
import miniirc

def my_message_parser(msg):
    if msg.startswith('~'):
        msg = '@' + msg[1:]
    return miniirc.ircv3_message_parser(msg)
~~~

#### Changing message parsers

To change message parsers, you can use `irc.change_parser(func=...)`. If `func` is not
specified, it will default to the built-in parser. You can only change message parsers
on-the-fly (for example in an IRCv3 CAP handler). If you need to change message parsers
before connecting, you can disable `auto_connect` and change it then.

~~~py
irc = miniirc.IRC(..., auto_connect=False)
irc.change_parser(my_message_parser)
irc.connect()
~~~

### Handling multiple events

*New in version 1.3.0.*

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

~~~py
import miniirc

# Not required, however this makes sure miniirc isn't insanely outdated.
assert miniirc.ver >= (1,4,0)

@miniirc.Handler('PRIVMSG', 'NOTICE', colon=True)
def handler(irc, hostmask, args):
    print(hostmask[0], 'sent a message to', args[0], 'with content', args[1])
    # nickname sent a message to #channel with content :Hello, world!

@miniirc.CmdHandler('PRIVMSG', 'NOTICE', colon=False)
def cmdhandler(irc, command, hostmask, args):
    print(hostmask[0], 'sent a', command, 'to', args[0], 'with content',
        args[1])
    # nickname sent a PRIVMSG to #channel with content Hello, world!
~~~

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
change. Patch version numbers can and will increase quickly, as miniirc is (at
the time of writing this) under active development.

## Python version support

 - Python 2 does not work and will (probably) never work with miniirc. If you MUST use Python 2, you can use the (probably outdated and bug-filled) python2 branch.
 - Python 3.3 and below probably won't work, and fixes will not be added unless
    they are very trivial.
 - Python 3.4 is not tested as thoroughly, however should work (and does with
    version 1.2.3).
 - Python 3.5 and above should work with the latest stable version of miniirc.

If there is a bug/error in Python 3.4 or newer (or a very trivial fix for
Python 3.3), please open an issue or pull request on
[GitHub](https://github.com/luk3yx/miniirc/issues) or
[GitLab](https://gitlab.com/luk3yx/miniirc/issues).

## Deprecations

miniirc v2.0.0 may never be released, however if it is the following breaking
changes will be made:

 - The `colon` keyword argument to `Handler` and `CmdHandler` will default to
    `False` instead of `True`.
 - Internal-only attributes `irc.sock` and `irc.sendq` (please do not use
    these) will be renamed. Again, please do not use these.
 - Unspecified hostmasks will be an empty string instead of the command. Don't
    rely on this "feature" if possible, simply ignore the hostmask if you do
    not need it.

## Working examples/implementations

Here is a list of some (open-source) bots using miniirc, in alphabetial order:

 - [irc-rss-feed-bot] - Posts RSS entry titles and shortened URLs to IRC
    channels. *Python 3.7+*
 - [irc-url-title-bot] - Gets webpage titles from URLs posted in IRC channels.
    *Python 3.7+*
 - [lurklite] - A generic configurable IRC bot.
    *[GitHub](https://github.com/luk3yx/lurklite) link.*
 - [stdinbot] - A very simple bot that dumps stdin to an IRC channel.
    *[GitHub](https://github.com/luk3yx/stdinbot) link.*

[irc-rss-feed-bot]:  https://github.com/impredicative/irc-rss-feed-bot
[irc-url-title-bot]: https://github.com/impredicative/irc-url-title-bot
[lurklite]:          https://gitlab.com/luk3yx/lurklite
[stdinbot]:          https://gitlab.com/luk3yx/stdinbot
