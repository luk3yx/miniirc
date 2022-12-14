# Changelog

Format partially copied from [Keep a Changelog](https://keepachangelog.com).

Notes:
 - I strongly recommend you use the latest version of miniirc, there are major
    bugfixes that are not listed here.
 - This changelog may contain typographical errors, it is still a
    work-in-progress.

## 1.9.1 - 2022-12-14

### Changed

 - Fixed handling of socket timeouts when trying to recover nickname
 - The socket is now closed if there's a connection timeout while writing data
   since the socket may have partially written data.
 - Removed use of the deprecated `socket.error`

## 1.9.0 - 2022-12-13

### Added

 - miniirc will now attempt to regain the originally specified nickname if it
   cannot used when connecting. For compatibility, `irc.nick` will return the
   current nickname while connected, however changing it will change the
   desired nickname. This may change in the future.

### Changed

 - The current nickname is now obtained from the 001 response after connecting.

## 1.8.4 - 2022-08-22

### Changed

 - Fixed a socket-related oversight in v1.8.3.

## 1.8.3 - 2022-08-22

### Changed

 - Receiving from the SSL socket is now done with a lock to prevent sending and
   receiving at the same time (which can break with SSL). This should fix
   random disconnects with Ubuntu 22.04 / OpenSSL 3.
 - Because of the above change, `irc.sock` is now non-blocking and things that
   call `irc.sock.settimeout()` may break the connection or cause deadlocks.
    - `irc.sock` hasn't been in the API documentation and has been deprecated
      for a while.

## 1.8.2 - 2022-04-26

### Added

 - Support for [SNI](https://en.wikipedia.org/wiki/Server_Name_Indication).

### Changed

 - `socket.create_connection()` is now used internally. If a domain name has
   multiple IP addresses and the connection fails, socket.create_connection()
   will attempt to connect to the next IP address in the list. This is an
   improvement over miniirc's previous behaviour of only trying the first IP
   address.
 - `ping_timeout` is now used as a connection timeout during socket setup.
 - A warning is now emitted if `verify_ssl` is disabled.
 - `SSLContext.wrap_socket()` is used instead of `ssl.wrap_socket()`.
 - The miniirc PyPI package now requires Python 3.4 or later.

## 1.8.1 - 2022-04-08

### Changed

 - Don't try and abort SASL authentication when receiving 904 numerics if it
   has already been aborted. This prevents miniirc from constantly trying to
   cancel authentication on InspIRCd 3 servers if the supplied credentials are
   incorrect.

## 1.8.0 - 2022-01-11

### Added

 - The `irc.wait_until_disconnected()` function has been added so that it's
   possible to stop the main thread from exiting while miniirc is still
   connected.

### Changed

 - Calling `Handler` or `CmdHandler` without colon=False will create a
   deprecation warning (unless the handler only handles IRCv3 capabilities).
 - The `irc.main()` function has a deprecation warning as well.

## 1.7.0 - 2021-09-26

### Added

 - The ability to make miniirc run handlers in thread pools using the
    "executor" keyword argument. I strongly recommend using this
    (`executor=concurrent.futures.ThreadPoolExecutor()`) if you plan to support
    Python 3.7 to 3.8 because of a memory leak
    (see [BPO 37788](https://bugs.python.org/issue37788) for more information).

### Changed

 - Fixed truncation of strings containing non-ASCII characters.
 - A couple of catch-all `except` statements now only handle more specific
    exceptions.

## 1.6.3 - 2020-10-20

### Added

 - Unit tests.

### Changed

 - Fix 432 (ERR_NICKNAMENUSE) handling.

## 1.6.2 - 2020-05-08

### Changed

 - Minor bugfix.

## 1.6.1 - 2020-04-29

### Changed

 - Fix NameError.

## 1.6.0 - 2020-04-28

### Added

 - A `ping_timeout` option (defaults to `ping_interval` for compatibility).

### Changed

 - Removed more potential race conditions.

### Deprecated

 - Relying on `args[-1]` being the channel for `JOIN` events.
 - Modifying the dict passed to handlers in the `tags` keyword argument.

## 1.5.1 - 2020-01-15

### Changed

 - `miniirc.pyi` now treats `colon` as a required parameter to `Handler`
    and `CmdHandler`, type checkers should throw an error if this parameter
    is unspecified.
 - No longer throws an error caused by a race condition with the `sts`
    capability.
 - Treats empty message tag values (`tag=`) the same way as tags without values
    (`tag`).

### Deprecated

 - Relying on `irc.quote` or `irc.send` throwing errors when the `force`
    keyword argument is used.

## 1.5.0 - 2019-11-19

### Added

 - Allow a comma-delimited string in the `channels` argument.
 - `irc.send()`: `irc.send('PRIVMSG', '#channel with spaces', 'Test message')`
    → `irc.quote('PRIVMSG', '#channel\xa0with\xa0spaces', ':Test message')`

## 1.4.3 - 2019-09-29

### Added

- `irc.current_nick` to be used instead of `irc.nick` when wanting the current
    nickname instead of the one used to connect. Note that this is currently an
    alias for `irc.nick`.

### Changed

 - Prevent `irc.quote()` from throwing errors if the socket somehow breaks. (I
    will probably rewrite `irc.quote`'s internals in miniirc v2.0.0).
 - Request the `away-notify` IRCv3 capability by default.
 - Use `threading.Lock`s inside `connect()`.

## 1.4.2 - 2019-08-16

### Changed

 - Code style changes.
 - Rewrite the internal socket receiving loop.
 - Use `threading.Lock`s internally when sending messages. If you were using
    outgoing message locks for stability, you no longer need them.

### Deprecated

 - Python 3.4
 - In miniirc v2.0.0, `irc.ns_identity` may be stored as a tuple instead of a
    string, for example `('username', 'password with spaces')` instead of
    `'username password with spaces'`. Both formats are currently accepted and
    will be accepted in the `ns_identity` keyword argument.

## 1.4.1 - 2019-07-16

### Changed

 - Bugfixes and code style changes.

### Deprecated

 - Internal-only attributes `irc.handlers`, `irc.sock`, and `irc.sendq`
    (please do not use these) will be renamed.
 - In miniirc v2.0.0, unspecified hostmasks will be an empty string instead of
    the command. Don't rely on this "feature" if possible, simply ignore the
    hostmask if you do not need it.


## 1.4.0 - 2019-06-18

### Added

 - Allow "channels" to be passed as a string containing a single channel.
 - A `colon` keyword argument to `Handler` and `CmdHandler`. When this is
    `False`, the leading colon is removed from `args[-1]`.

### Changed

 - Minor bugfix.

### Deprecated

 - In miniirc v2.0.0, the `colon` argument will default to `False` instead of
    `True`.

## 1.3.3 - 2019-05-20

### Changed

 - Bugfixes and a minor performance improvement.


## 1.3.2 - 2019-04-29

### Changed

 - Fix `CmdHandlers` and IRCv3 handlers on methods.

## 1.3.1 - 2019-04-29

### Changed

 - Bugfix and a documentation change.

## 1.3.0 - 2019-04-28

### Added

 - `CmdHandlers` that allow getting the command when handling multiple events.
 - Catch-all handlers that can handle all events.

## 1.2.4 - 2019-04-06

### Changed

 - Bugfixes.

## 1.2.3 - 2019-04-06

*Although miniirc v1.2.0 to v1.2.2 existed, they were horribly broken and
pulled from PyPI. Changes from those releases will be mentioned here.*

### Added

 - miniirc now periodically pings servers, the interval at which this ping is
    sent can be modified with the `ping_interval` keyword argument.
 - The `ns_identity` keyword argument can now be a `tuple` or a `list` similar
    to `('username', 'password with spaces')`.
 - The `debug` keyword argument can be a function, this will be called for each
    line displayed with `irc.debug()`.

### Changed

 - Bugfixes.

## 1.1.4 - 2019-03-29

### Changed

 - Internally allow logging functions to be passed, for forwards-compatibility
    with v1.2.0.

## 1.1.3 - 2019-03-27

### Changed

 - Documentation updates.

## 1.1.2 - 2019-03-19

### Changed

 - Python 3.4 bugfixes.

## 1.1.1 - 2019-03-19

### Changed

 - Bugfix when parsing invalid ISUPPORTs.

## 1.1.0 - 2019-03-19

### Changed

 - Add (broken) support for `oragono.io/maxline-2`, this is not fixed until a
    future release.
 - Add ISUPPORT message parsing.

## 1.0.10 - 2019-03-19

### Changed

 - Process IRCv3 tags in a separate function.

## 1.0.9 - 2019-02-27

### Changed

 - Added `message-tags` as an alias for `draft/message-tags-0.2`.

## 1.0.8 - 2019-02-26

### Changed

 - Automatically enable TLS/SSL when the port specified is `'6697'`, instead of
    just `6697`.

## 1.0.7 - 2019-02-19

### Changed

 - Fixed typographical error in README.md.

## 1.0.6 - 2019-02-19

### Changed

 - Add a URL to setup.py and bump the version number.

## 1.0.5 - 2019-01-12

### Changed

 - Request more IRC capabilities by default.
 - Support `CAP DEL`.

## 1.0.4 - 2019-01-11

### Changed

 - Stopped including the `sts` capability in `CAP REQ`, it is still handled
    internally however.

## 1.0.3 - 2019-01-11

### Changed

 - Don't cut part of a tag name or value off when sending message tags.

## 1.0.2 - 2019-01-11

### Changed

 - Allow message tags that do not start in `+` to be sent.
 - Update documentation.

## 1.0.1 - 2019-01-10

### Changed

 - Bugfixes.

## 1.0.0 - 2019-01-10

### Added

 - Message tags can now be sent to IRC servers if the server supports it.
 - `irc.active_caps` now lists active capabilities.
 - Add sanity check to `irc.connect()`.
 - Bugfixes and documentation updates.
