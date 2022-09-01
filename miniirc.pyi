# miniirc stub file
# This allows type checking without breaking compatibility or making the main
#   file slower to load.

from __future__ import annotations
import atexit, concurrent.futures, errno, io, threading, time, socket, sys
from collections.abc import Callable, Iterable
from typing import Any, Optional, Union, overload

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

# The version string and tuple
ver: tuple[int, int, int] = ...
version: str = ...

# __all__ and _default_caps
__all__: list[str] = ['CmdHandler', 'Handler', 'IRC']
_default_caps: set[str] = {'account-tag', 'cap-notify', 'chghost',
                           'draft/message-tags-0.2', 'invite-notify', 'message-tags',
                           'oragono.io/maxline-2', 'server-time', 'sts'}

# Get the certificate list.
get_ca_certs: Callable[[], Optional[str]]

# Create global handlers
_global_handlers: dict[str, Callable] = {}


def _add_handler(handlers, events, ircv3, cmd_arg, colon) \
    -> Callable[[Callable], Callable]: ...


_handler_func_1 = Callable[['IRC', tuple[str, str, str], list[str]], Any]
_handler_func_2 = Callable[['IRC', tuple[str, str, str],
                            dict[str, Union[str, bool]], list[str]], Any]


@overload
def Handler(*events: str, colon: bool, ircv3: Literal[False] = False) \
    -> Callable[[_handler_func_1], _handler_func_1]: ...


@overload
def Handler(*events: str, colon: bool, ircv3: Literal[True]) \
    -> Callable[[_handler_func_2], _handler_func_2]: ...


_handler_func_3 = Callable[['IRC', str, tuple[str, str, str], list[str]], Any]
_handler_func_4 = Callable[['IRC', str, tuple[str, str, str],
                            dict[str, Union[str, bool]], list[str]], Any]


@overload
def CmdHandler(*events: str, colon: bool, ircv3: Literal[False] = False) \
    -> Callable[[_handler_func_3], _handler_func_3]: ...


@overload
def CmdHandler(*events: str, colon: bool, ircv3: Literal[True]) \
    -> Callable[[_handler_func_4], _handler_func_4]: ...


# Parse IRCv3 tags
ircv3_tag_escapes: dict[str, str] = {':': ';', 's': ' ', 'r': '\r', 'n': '\n'}
def _tags_to_dict(tag_list: Union[str, list[str]],
                  separator: Optional[str] = ';') -> dict[str, Union[str, bool]]: ...

# Create the IRCv2/3 parser
def ircv3_message_parser(msg: str) -> tuple[str, tuple[str, str, str],
                                            dict[str, Union[str, bool]], list[str]]: ...

# Escape tags
def _escape_tag(tag: str) -> str: ...

# Convert a dict into an IRCv3 tags string
def _dict_to_tags(tags: dict[str, Union[str, bool]]) -> bytes: ...

# A wrapper for callable logfiles
class _Logfile:
    __slots__ = ('_buffer', '_func')

    def write(self, data: str) -> None: ...
    def __init__(self, func: Callable[[str], Any]) -> None: ...

# Create the IRC class
class IRC:
    connected: Optional[bool] = None
    debug_file: Optional[Union[io.TextIOWrapper, _Logfile]] = ...
    msglen: int = 512
    _main_lock: Optional[threading.Thread] = None
    _sasl: bool = False
    _unhandled_caps: Optional[set] = None

    @property
    def current_nick(self) -> str:
        ...

    ip: str
    port: int
    nick: str
    channels: set[str]
    ident: str
    realname: str
    ssl: Optional[bool]
    persist: bool
    ircv3_caps: set[str]
    active_caps: set[str]
    isupport: dict[str, Union[str, int]]
    connect_modes: Optional[str]
    quit_message: str
    ping_interval: int
    verify_ssl: bool

    ns_identity: Union[tuple[str, str], str]

    # Debug print()
    def debug(self, *args: Any, **kwargs) -> None: ...

    # Send raw messages
    def quote(self, *msg: str, force: Optional[bool] = None,
              tags: Optional[dict[str, Union[str, bool]]] = None) -> None: ...

    def send(self, *msg: str, force: Optional[bool] = None,
             tags: Optional[dict[str, Union[str, bool]]] = None) -> None: ...

    # User-friendly msg, notice, and ctcp functions.
    def msg(self, target: str, *msg: str,
            tags: Optional[dict[str, Union[str, bool]]] = None) -> None: ...

    def notice(self, target: str, *msg: str,
               tags: Optional[dict[str, Union[str, bool]]] = None) -> None: ...

    def ctcp(self, target: str, *msg: str, reply: bool = False,
             tags: Optional[dict[str, Union[str, bool]]] = None) -> None: ...

    def me(self, target: str, *msg: str,
           tags: Optional[dict[str, Union[str, bool]]] = None) -> None: ...

    # Allow per-connection handlers
    @overload
    def Handler(*events: str, colon: bool, ircv3: Literal[False] = False) \
        -> Callable[[_handler_func_1], _handler_func_1]: ...

    @overload
    def Handler(*events: str, colon: bool, ircv3: Literal[True]) \
        -> Callable[[_handler_func_2], _handler_func_2]: ...

    @overload
    def CmdHandler(*events: str, colon: bool, ircv3: Literal[False] = False) \
        -> Callable[[_handler_func_3], _handler_func_3]: ...

    @overload
    def CmdHandler(*events: str, colon: bool, ircv3: Literal[True]) \
        -> Callable[[_handler_func_4], _handler_func_4]: ...

    # The connect function
    def connect(self) -> None: ...

    # An easier way to disconnect
    def disconnect(self, msg: Optional[str] = None, *,
                   auto_reconnect: bool = False) -> None: ...

    # Finish capability negotiation
    def finish_negotiation(self, cap: str) -> None: ...

    # Change the message parser
    def change_parser(self, parser: Callable[
        [str],
        tuple[str, tuple[str, str, str], dict[str, Union[str, bool]],
              list[str]]
    ] = ircv3_message_parser) -> None: ...

    # Start a handler function
    def _start_handler(
        self, handlers: list[Callable], command: str,
        hostmask: tuple[str, str, str], tags: dict[str, Union[str, bool]],
        args: list[str]
    ) -> None: ...

    # Launch handlers
    def _handle(self, cmd: str, hostmask: tuple[str, str, str],
                tags: dict[str, Union[str, bool]], args: list[str]) -> bool: ...

    # Launch IRCv3 handlers
    def _handle_cap(self, cap: str) -> None: ...

    # The main loop
    def _main(self) -> None: ...

    # Waits until the client is disconnected and won't auto reconnect
    def wait_until_disconnected(self) -> None: ...

    # Initialize the class
    def __init__(
        self, ip: str, port: int, nick: str,
        channels: Union[Iterable[str], str] = None, *,
        ssl: Optional[bool] = None, ident: Optional[str] = None,
        realname: Optional[str] = None, persist: bool = True,
        debug: Union[bool, io.TextIOWrapper, _Logfile] = False,
        ns_identity: Optional[Union[tuple[str, str], str]] = None,
        auto_connect: bool = True, ircv3_caps: Optional[set[str]] = None,
        connect_modes: Optional[str] = None,
        quit_message: str = 'I grew sick and died.', ping_interval: int = 60,
        verify_ssl: bool = True,
        executor: Optional[concurrent.futures.ThreadPoolExecutor]
    ) -> None: ...
