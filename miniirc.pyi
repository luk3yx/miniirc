# miniirc stub file
# This allows type checking without breaking compatibility or making the main
#   file slower to load.

import atexit, concurrent.futures, errno, io, threading, time, socket, ssl, sys
from typing import (Any, Callable, Dict, Iterable, List, Mapping, Optional,
                    Set, Tuple, Union, overload)

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

# The version string and tuple
ver: Tuple[int, int, int] = ...
version: str = ...

# __all__ and _default_caps
__all__: List[str] = ['CmdHandler', 'Handler', 'IRC']
_default_caps: Set[str] = {'account-tag', 'cap-notify', 'chghost',
    'draft/message-tags-0.2', 'invite-notify', 'message-tags',
    'oragono.io/maxline-2', 'server-time', 'sts'}

# Get the certificate list.
get_ca_certs: Callable[[], Optional[str]]
try:
    from certifi import where as get_ca_certs
except ImportError:
    get_ca_certs = lambda : None

_handler_func_1 = Callable[['IRC', Tuple[str, str, str], List[str]], Any]
_handler_func_2 = Callable[['IRC', Tuple[str, str, str],
                            Mapping[str, Union[str, bool]], List[str]], Any]
@overload
def Handler(*events: str, colon: bool = False, ircv3: Literal[False] = False) \
    -> Callable[[_handler_func_1], _handler_func_1]: ...
@overload
def Handler(*events: str, colon: bool = False, ircv3: Literal[True]) \
    -> Callable[[_handler_func_2], _handler_func_2]: ...

_handler_func_3 = Callable[['IRC', str, Tuple[str, str, str], List[str]], Any]
_handler_func_4 = Callable[['IRC', str, Tuple[str, str, str],
                            Mapping[str, Union[str, bool]], List[str]], Any]
@overload
def CmdHandler(*events: str, colon: bool = False,
    ircv3: Literal[False] = False) -> Callable[[_handler_func_3], _handler_func_3]: ...
@overload
def CmdHandler(*events: str, colon: bool = False, ircv3: Literal[True]) \
    -> Callable[[_handler_func_4], _handler_func_4]: ...

# Parse IRCv3 tags
_ircv3_tag_escapes: Dict[str, str] = {':': ';', 's': ' ', 'r': '\r', 'n': '\n'}
def _tags_to_dict(tag_list: Union[str, List[str]],
        separator: Optional[str] = ';') -> Dict[str, Union[str, bool]]: ...

# Create the IRCv2/3 parser
def ircv3_message_parser(msg: str) -> Tuple[str, Tuple[str, str, str],
        Dict[str, Union[str, bool]], List[str]]: ...

# Escape tags
def _escape_tag(tag: str) -> str: ...

# Convert a dict into an IRCv3 tags string
def _dict_to_tags(tags: Mapping[str, Union[str, bool]]) -> bytes: ...

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

    ip: str
    port: int
    nick: str
    current_nick: str
    channels: Set[str]
    ident: str
    realname: str
    ssl: Optional[bool]
    persist: bool
    ircv3_caps: Set[str]
    active_caps: Set[str]
    isupport: Dict[str, Union[str, int]]
    connect_modes: Optional[str]
    quit_message: str
    ping_interval: int
    verify_ssl: bool

    ns_identity: Union[Tuple[str, str], str]

    # Debug print()
    def debug(self, *args: Any, **kwargs) -> None: ...

    # Send raw messages
    def quote(self, *msg: str, force: Optional[bool] = None,
        tags: Optional[Mapping[str, Union[str, bool]]] = None) -> None: ...

    def send(self, *msg: str, force: Optional[bool] = None,
        tags: Optional[Mapping[str, Union[str, bool]]] = None) -> None: ...

    # User-friendly msg, notice, and ctcp functions.
    def msg(self, target: str, *msg: str,
        tags: Optional[Mapping[str, Union[str, bool]]] = None) -> None: ...

    def notice(self, target: str, *msg: str,
        tags: Optional[Mapping[str, Union[str, bool]]] = None) -> None: ...

    def ctcp(self, target: str, *msg: str, reply: bool = False,
        tags: Optional[Mapping[str, Union[str, bool]]] = None) -> None: ...

    def me(self, target: str, *msg: str,
        tags: Optional[Mapping[str, Union[str, bool]]] = None) -> None: ...

    # Allow per-connection handlers
    @overload
    def Handler(*events: str, colon: bool = False,
        ircv3: Literal[False] = False) \
        -> Callable[[_handler_func_1], _handler_func_1]: ...
    @overload
    def Handler(*events: str, colon: bool = False, ircv3: Literal[True]) \
        -> Callable[[_handler_func_2], _handler_func_2]: ...

    @overload
    def CmdHandler(*events: str, colon: bool = False,
        ircv3: Literal[False] = False) \
        -> Callable[[_handler_func_3], _handler_func_3]: ...
    @overload
    def CmdHandler(*events: str, colon: bool = False, ircv3: Literal[True]) \
        -> Callable[[_handler_func_4], _handler_func_4]: ...

    # The connect function
    def connect(self) -> None: ...

    # An easier way to disconnect
    def disconnect(self, msg: Optional[str] = None, *,
        auto_reconnect: bool = False) -> None: ...

    # Finish capability negotiation
    def finish_negotiation(self, cap: str) -> None: ...

    # Change the message parser
    def change_parser(self, parser: Callable[[str],
        Tuple[str, Tuple[str, str, str], Dict[str, Union[str, bool]],
        List[str]]] = ircv3_message_parser) -> None: ...

    # Initialize the class
    def __init__(self, ip: str, port: int, nick: str,
        channels: Union[Iterable[str], str] = None, *,
        ssl: Optional[bool] = None, ident: Optional[str] = None,
        realname: Optional[str] = None, persist: bool = True,
        debug: Union[bool, io.TextIOWrapper, _Logfile] = False,
        ns_identity: Optional[Union[Tuple[str, str], str]] = None,
        auto_connect: bool = True, ircv3_caps: Optional[Set[str]] = None,
        connect_modes: Optional[str] = None,
        quit_message: str = 'I grew sick and died.', ping_interval: int = 60,
        verify_ssl: bool = True,
        executor: Optional[concurrent.futures.ThreadPoolExecutor]) -> None: ...
