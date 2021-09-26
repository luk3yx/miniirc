# Changelog

Format partially copied from [Keep a Changelog](https://keepachangelog.com).

Notes:
 - I strongly recommend you use the latest version of miniirc, there are major
    bugfixes that are not listed here.
 - This changelog may contain typographical errors, it is still a
    work-in-progress.

## 1.7.0 - 2021-09-26

### Added

 - The ability to make miniirc run handlers in thread pools using the
    "executor" keyword argument. I strongly recommend using this
    (`executor=concurrent.futures.ThreadPoolExecutor()`) if you plan to support
    Python 3.7 to 3.8 because of a memory leak
    (see [BPO 37788](https://bugs.python.org/issue37788) for more information).

### Changed

 - Fixed truncation of strings containing non-ASCII characters.
 - A couple of catch-all `execpt` statements now only handle more specific
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
