# miniirc

A simple IRC client framework.

To install miniirc, simply run `pip3 install miniirc` as root.

## Parameters

~~~py
irc = miniirc.IRC(ip, port, nick, channels = None, *, ssl = None, ident = None, realname = None, persist = True, debug = False, ns_identity = None, auto_connect = True, ircv3_caps = set(), quit_message  = 'I grew sick and died.', verify_ssl = True)
~~~

| Parameter     | Description                                                |
| ------------- | -------------------------------------------------------- |
| `ip`          | The IP/hostname of the IRC server to connect to.          |
| `port`        | The port to connect to.                                   |
| `nick`        | The nickname of the bot.                                  |
| `channels`    | The channels to join on connect.                          |
| `ssl`         | Enable SSL. If `None`, SSL is disabled unless the port is `6697`. |
| `ident`       | The ident to use, defaults to `nick`.                     |
| `realname`    | The realname to use, defaults to `nick` as well.          |
| `persist`     | Whether to automatically reconnect.                       |
| `debug`       | Enables debug mode, prints all IRC messages.              |
| `ns_identity` | The NickServ account to use (`<user> <password>`).        |
| `auto_connect`| Runs `.connect()` straight away.                          |
| `ircv3_caps`  | A set() of IRCv3 capabilities to request. SASL is auto-added if `ns_identity` is specified. |
| `quit_message`| Sets the default quit message. This can be modified per-quit with `irc.disconnect()`. |
| `verify_ssl`  | Verifies SSL certificates. Disabling this is not recommended. If you have trouble with SSL certificate verification, try running `pip3 install certifi` first. |

## Functions

| Function      | Description                                               |
| ------------- | --------------------------------------------------------  |
| `connect()`   | Connects to the IRC server if not already connected.      |
| `ctcp(target, *msg, reply=False)` | Sends a `CTCP` request or reply to `target`. |
| `debug(...)`  | Debug, calls `print(...)` if debug mode is on.            |
| `disconnect(msg = ..., *, auto_reconnect = False)`| Disconnects from the IRC server. `auto_reconnect` will be overriden by `self.persist` if set to `True`. |
| `Hander(...)` | An event handler, see [Handlers](#handlers) for more info.|
| `main()`      | Starts the main loop in a thread if not already running.  |
| `me(target, *msg)`          | Sends a `/me` (`CTCP ACTION`) to `target`.  |
| `msg(target, *msg)`         | Sends a `PRIVMSG` to `target`.              |
| `notice(target, *msg)`      | Sends a `NOTICE` to `target`.               |
| `quote(*msg, force=None)` | Sends a raw message to IRC, use `force=True` to send while disconnected. |

## Handlers

Handlers are `@-rules` called in their own thread when their respective IRC event(s) is/are received. Handlers may be global (`@miniirc.handler`) or local (`@miniirc.IRC().handler`) to a certain IRC connection. New handlers are not added to existing IRC connections automatically, either define handlers before you initialise the `miniirc.IRC` object or add them as local handlers.

The basic syntax for a handler is as followed, where `*events` is a list of events (`PRIVMSG`, `NOTICE`, etc) are called.

~~~py
import miniirc
@miniirc.Handler(*events)
def handler(irc, hostmask, args):
    # irc:      An 'IRC' object.
    # hostmask: A 'hostmask' object.
    # args:     A list containing the arguments sent to the command.
    #             Everything following the first `:` in the command
    #             is put into one item (args[-1]).
    pass
~~~

### Hostmask object

Hostmasks are tuples with the format `('user', 'ident', 'hostname')`. If `ident` and `hostname` aren't sent from the server, they will be filled in with the previous value. If a command is received without a hostmask, all the `hostmask` parameters will be set to the name of the command.

### Example

~~~py
import miniirc

@miniirc.Handler('PRIVMSG', 'NOTICE')
def handler(irc, hostmask, args):
    print(hostmask[0], 'sent a message to', args[0], 'with content', args[1])
~~~

This will print a line whenever the bot gets a `PRIVMSG` or `NOTICE`.

## Working examples/implementations

There is a working example and stdinbot (dumps stdin to an IRC channel) on
[luk3yx/stdinbot](https://gitlab.com/luk3yx/stdinbot).
