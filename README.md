# stdinbot

A stupidly simple IRC bot to interact with stdin.

# miniirc

A simple IRC client framework.

## Parameters

~~~py
irc = miniirc.IRC(ip, port, nick, channels = None, *, ssl = None, ident = None, realname = None, persist = False, debug = False, ns_identity = None, auto_connect = True)
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

## Functions

Functions are not yet documented, see the source code.
