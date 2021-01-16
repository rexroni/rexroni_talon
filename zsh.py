from talon import Module, Context, ui, actions, linux, actions, ui
from talon.scripting import core

import os
import typing
import re
import json
import socket
import contextlib
import selectors
import threading
import traceback
import logging

from . import singletons

HERE = os.path.dirname(__file__)

ctx = Context()
mod = Module()

mod.apps.zsh = "title: /^zsh:/"
ctx.matches = r"""
app: zsh
"""

mod.list("zsh_completion", desc="zsh completions")
ctx.lists["user.zsh_completion"] = {}

mod.list("shell_command", desc="user shell commands")
ctx.lists["user.shell_command"] = {
    "less": "less",
    "ls": "ls",
    "cd": "cd",
    "vim": "vim",
    "git": "git",
    "make": "make",
    "ninja": "ninja",
    "sed": "sed",
    "g": "g",
    "grep": "grep",
    "excel": "xsel",
    "rm": "rm",
    "make dir": "mkdir",
    "rmdir": "rmdir",
}

@mod.capture(rule="{user.shell_command}")
def shell_command(m) -> str:
    """Returns a shell command"""
    return m.shell_command

@mod.capture(rule="{user.zsh_completion}")
def zsh_completion(m) -> str:
    """Returns a zsh_completion"""
    return m.zsh_completion


_typed_special = False
_typed_anything = False

@contextlib.contextmanager
def maybe_trigger_completions():
    """
    After running any command, retrigger the completion calculation,
    unless you typed enter at any point.
    """
    global _typed_special
    global _typed_anything
    # print('triggering?')
    _typed_special = False
    _typed_anything = False
    yield
    should_trigger = _typed_anything and not _typed_special
    if should_trigger:
        actions.key('ctrl-t')
    # print('triggered!' if should_triger else 'not triggered!')


@ctx.action_class("core")
class core_action:
    def run_phrase(phrase: core.Capture):
        with maybe_trigger_completions():
            core.CoreActions.run_phrase(phrase)


@ctx.action_class("main")
class main_action:
    def key(key: str):
        global _typed_special
        global _typed_anything
        if key == 'enter' or ('-' in key and key != '-'):
            # Don't trigger extra key presses on special keys.
            _typed_special = True
        _typed_anything = True

        # print('key:', key)

        # actions.next() is how you reference the action you are overriding.
        actions.next(key)

def extensions(x):
    x = re.sub("\\.py$", " dot pie", x)
    x = re.sub("\\.c$", " dot see", x)
    x = re.sub("\\.h$", " dot h", x)
    x = re.sub("\\.sh$", " dot s h", x)
    x = re.sub("\\.zsh$", " dot z s h", x)
    x = re.sub("\\.go$", " dot go", x)
    return x

def speakify(x, specials):
    specials = specials or ""
    x = re.sub("\\.", " dot " if '.' in specials else ' ', x)
    x = re.sub("_", " under " if '_' in specials else ' ', x)
    x = re.sub("-", " dash " if '-' in specials else ' ', x)
    x = re.sub("/", " slash " if '/' in specials else ' ', x)
    # talon pukes on multiple spaces
    x = re.sub(" +", " ", x)
    # talon also pukes on leading spaces
    return x.strip()

def shorthand(x):
    s = re.sub('[._-/].*', '', x.lstrip('._-/'))
    if s == x:
        return None
    return x

def get_pronunciations(symbol, prefix=""):
    out = {}

    # We'll never re-type the prefix, ever.
    typable = symbol[len(prefix):]

    # If there is a symbol in the prefix, we never allow pronouncing before it.
    # Think of pronouncing "--amend" when "--" is the prefix or "a/b" when "a/"
    # is the prefix.  You wouldn't.
    symboled_prefix = re.match('(.*[._/-])[^._/-]*$', prefix)
    if symboled_prefix:
        symboled_prefix = symboled_prefix[1]
        symbol = symbol[len(symboled_prefix):]
        prefix = prefix[len(symboled_prefix):]

    # Now, if you have half-typed a word to narrow down the completion options,
    # support either the full (remaining) symbol, or just the part that is
    # remaining.
    variations = [(symbol, typable)]
    if prefix:
        variations.append((symbol[len(prefix):], typable))

    # Now, in case you want to pronounce just until the next symbol, we'll
    # support typing that out and we'll type a tab afterwards to trigger the
    # shell's tab completion (which allows us to not manually track prefixes)
    shorthand = re.match('^([^._/-]*)[._/-].*$', symbol)
    if shorthand:
        shorthand = shorthand[1]
        shortened_by = len(symbol) - len(shorthand)
        typable = typable[:-shortened_by] + '\t'

        variations.append((shorthand, typable))
        if prefix:
            shorthand = re.match('^([^._/-]*)[._/-].*$', symbol[len(prefix):])
            if shorthand:
                shorthand = shorthand[1]
                variations.append((shorthand, typable))

    for base, result in variations:
        if not base:
            continue

        # always start with pronouncing extensions
        base = extensions(base)

        # then try to support the plainest form
        out[speakify(base, None)] = result

        # support the most explicit form
        out[speakify(base, '._-/')] = result

        # support the one-of-each forms
        out[speakify(base, '.')] = result
        out[speakify(base, '_')] = result
        out[speakify(base, '-')] = result
        out[speakify(base, '/')] = result

    return out


class Zsh:
    def __init__(self, pid, selector):
        self.pid = pid
        self.selector = selector
        self.sock = socket.socket(family=socket.AF_UNIX)
        self.recvd = []
        self.recvd_buf = b''
        self.send_buf = b''
        self.completions = {}

        # print(f'new Zsh({pid})!')

        # There is a race condition where this hangs, unfortunately.
        # If the zsh line editor is not active, the zsh completion server
        # cannot accept connections and incoming connections can hang.
        # The good news is that it seems the first two connections do not hang
        # and we should only ever make one connection to each zsh server.
        try:
            self.sock.connect(f"{HERE}/zsh-completion-server/sock/{pid}.sock")
        except Exception as e:
            self.sock.close()
            logging.warning('connection failed:', e)
            raise

        self.sock.setblocking(False)
        self.selector.register(self.sock, self._event_mask(), self)

    def _event_mask(self):
        if self.send_buf:
            return selectors.EVENT_READ | selectors.EVENT_WRITE
        return selectors.EVENT_READ

    def queue_send(self, msg):
        # Only safe to call inside the event loop.
        self.send_buf += msg
        self.selector.modify(self.sock, self._event_mask(), self)

    def event(self, readable, writable):
        if readable:
            msg = self.sock.recv(4096)
            if not msg:
                # Broken connection.
                self.close()
                return
            self.recvd_buf += msg
            last_newline = self.recvd_buf.rfind(b'\n')
            if last_newline != -1:
                # commit complete lines to recvd
                self.recvd.extend(self.recvd_buf[:last_newline].split(b'\n'))
                self.recvd_buf = self.recvd_buf[last_newline + 1:]
                self.check_cmd()

        if writable:
            written = self.sock.send(self.send_buf)
            if written == 0:
                # Broken connection.
                self.close()
                return
            self.send_buf = self.send_buf[written:]
            self.selector.modify(self.sock, self._event_mask(), self)

    def check_cmd(self):
        if not self.recvd:
            return
        # cmd will be like 'CMD:ARG:ARG'
        cmd = self.recvd[0].split(b':')
        # Right now we only allow one command.
        assert cmd[0] == b'completions', f'command {cmd} not valid'
        try:
            end = self.recvd.index(b"::done::")
        except ValueError:
            return
        assert len(self.recvd) >= 4, "not enough lines in response"
        context = self.recvd[1]
        prefix = self.recvd[2]
        raw_completions = self.recvd[3:end]
        self.recvd = self.recvd[end+1:]
        self.handle_completions(context, prefix, raw_completions)

    def handle_completions(self, context, prefix, raw_completions):
        # For blank commands, we use a custom command list for completion and
        # ignore the huge list from zsh.

        if prefix == b'' and context in [
            b":complete:-command-:",
            b":complete:-sudo-:",
            b":complete:-env-:",
        ]:
            raw_completions = []

        completions = {}
        for symbol in raw_completions:
            completions.update(
                get_pronunciations(symbol.decode("utf8"), prefix.decode("utf8"))
            )

        # cache these completions for later
        self.completions = completions
        # if we are active, update the list of zsh_completions
        if self.is_active_window():
            logging.debug(completions)
            ctx.lists["user.zsh_completion"] = self.completions

    def is_active_window(self):
        window = ui.active_window()
        if not window.title.startswith("zsh:"):
            return False
        active_pid = int(window.title.split(':')[1])
        return active_pid == self.pid

    def close(self):
        self.selector.unregister(self.sock)
        self.sock.close()


class ZshPool:
    def __init__(self):
        # Open a control channel.  ctrl_r will be part of the event loop,
        # ctrl_w is for outside of the event loop.
        self.ctrl_r, self.ctrl_w = socket.socketpair()
        self.ctrl_r.setblocking(False)

        self.selector = selectors.DefaultSelector()
        self.selector.register(self.ctrl_r, selectors.EVENT_READ)

        # shells maps pids to Zsh objects.
        self.shells = {}
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run)
        self.thread.start()
        return self

    def _trigger_pid(self, pid):
        if pid not in self.shells:
            # detected new shell
            try:
                zsh = Zsh(pid, self.selector)
            except:
                return
            self.shells[pid] = zsh
        zsh = self.shells[pid]
        zsh.queue_send(b'trigger\n')

    def _handle_ctrl(self):
        msg = self.ctrl_r.recv(4096)
        for line in msg.splitlines():
            cmd = line.split(b":")
            if cmd[0] == b"quit":
                return True
            if cmd[0] == b"trigger":
                self._trigger_pid(int(cmd[1]))
                continue
            raise ValueError(f"unknown control message: {cmd}")
        return False

    def _run(self):
        while True:
            for key, mask in self.selector.select():
                if key.fileobj == self.ctrl_r:
                    quit = self._handle_ctrl()
                    if quit:
                        return
                else:
                    readable = mask & selectors.EVENT_READ
                    writable = mask & selectors.EVENT_WRITE
                    zsh = key.data
                    zsh.event(readable, writable)

    def trigger(self, pid):
        # print(f'trigger {pid}')
        self.ctrl_w.send(b'trigger:%d\n'%pid)

    def close(self):
        if self.thread:
            self.ctrl_w.send(b'quit\n')
            self.thread.join()
        self.selector.unregister(self.ctrl_r)
        self.ctrl_r.close()
        self.ctrl_w.close()

        # unregister and close all Zsh objects
        # (make a copy of the dictionary so we can modify the
        # original as we iterate through the copy)
        for _, key in dict(self.selector.get_map()).items():
            zsh = key.data
            zsh.close()

        self.selector.close()


# on reload, close the old pool
if singletons.zsh_pool is not None:
    singletons.zsh_pool.close()
    singletons.zsh_pool = None
# start the new pool
singletons.zsh_pool = ZshPool().start()


class ZshTriggerWatch:
    """
    Whenever a new zsh window is selected, reach out to the zsh completion
    server and have it tell us what its completion list is.
    """
    def win_focus(window):
        if window.title.startswith("zsh:"):
            pid = int(window.title.split(':')[1])
            singletons.zsh_pool.trigger(pid)

    def win_title(window):
        if window == ui.active_window():
            if window.title.startswith("zsh:"):
                pid = int(window.title.split(':')[1])
                singletons.zsh_pool.trigger(pid)

    ui.register('win_focus', win_focus)
    ui.register('win_title', win_title)
