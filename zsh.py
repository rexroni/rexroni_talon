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

from . import files
from . import display
from . import singletons

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
}

# make a directory for completions from every zsh pid.
COMPLETIONS_DIR = os.path.join(os.path.dirname(__file__), "updates", "zsh_completions")
os.makedirs(COMPLETIONS_DIR, exist_ok=True)

def on_completion_update(relpath, path, exists):
    basename = os.path.basename(relpath)
    # get the window id that was updated from the filename
    matches = re.match("([0-9]+).csv", basename)
    if matches is None:
        return
    window = int(matches[1])
    # ignore non-active windows
    if window != display.get_active_window().id:
        return
    if not exists:
        ctx.lists["user.zsh_completion"] = {}
    with open(path) as f:
        update = files.csv_to_dict(f)
        print(update)
        ctx.lists["user.zsh_completion"] = update

files.add_updates_callback("zsh_completions/", on_completion_update)

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
        if key == 'enter' or '-' in key:
            # Don't trigger extra key presses on special keys.
            _typed_special = True
        _typed_anything = True

        # print('key:', key)

        # actions.next() is how you reference the action you are overriding.
        actions.next(key)


class ZshConnection:
    def __init__(self, conn):
        self.conn = conn
        # store up all the packets received and return them when the connection
        # is closed (one command per connection)
        self.packets = []

    # returns a command body when the connection is closed
    def recv(self):
        data = self.conn.recv(4096)
        if not data:
            # connection is broken, cmd is ended
            self.conn.close()
            return b''.join(self.packets)
        self.packets.append(data)
        return None


class ZshServer:
    def __init__(self, port=8468):
        self.port = port
        self.sock = None
        self.thread = None
        self.quitting = False

    def start(self):
        self.thread = threading.Thread(target=self._run)
        self.thread.start()
        return self

    def _handle_listener(self):
        conn, _ = self.listener.accept()
        conn.setblocking(False)
        c = ZshConnection(conn)
        self.selector.register(conn, selectors.EVENT_READ, c)

    def _handle_data(self, c):
        msg = c.recv()
        if msg:
            print(f"msg received: {msg}")
            # done with connection
            self.selector.unregister(c.conn)

            if msg.startswith(b'quit'):
                self.quitting = True
                return

    def _run(self):
        # Create the listener.
        with socket.socket() as self.listener:
            self.listener.bind(("localhost", self.port))
            self.listener.listen(5)
            self.listener.setblocking(False)

            with selectors.DefaultSelector() as self.selector:
                self.selector.register(self.listener, selectors.EVENT_READ)

                try:
                    # main event loop
                    while not self.quitting:
                        for key, mask in self.selector.select():
                            if key.fileobj == self.listener:
                                # handle a new connection
                                self._handle_listener()
                                continue
                            else:
                                c = key.data
                                self._handle_data(c)
                                if self.quitting:
                                    break
                finally:
                    self.selector.unregister(self.listener)
                    self.listener.close()
                    # unregister and close all connections
                    # (make a copy of the dictionary so we can modify the
                    # original as we iterate through the copy)
                    for fileobj, key in dict(self.selector.get_map()).items():
                        self.selector.unregister(fileobj)
                        c = key.data
                        c.conn.close()
        print("quit loop")

    def close(self):
        print('closing')
        if self.thread:
            # send a "quit" message through the socket
            try:
                with socket.socket() as s:
                    s.connect(('localhost', self.port))
                    s.send(b'quit\n')
            except Exception as e:
                print(e)
                pass
            self.thread.join()
        if self.sock:
            self.sock.close()


# on reload, kill the old server
if singletons.zsh_server is not None:
    singletons.zsh_server.close()
# start the new server
singletons.zsh_server = ZshServer().start()


class ZshTriggerWatch:
    """
    Whenever a new zsh window is selected, reach out to the zsh completion
    server and have it tell us what its completion list is.
    """
    def trigger_zsh(pid):
        try:
            with socket.socket(family=socket.AF_UNIX) as s:
                s.connect(f'/run/zsh-completion-server/{pid}.sock')
                s.send(b'trigger\n')
        except Exception as e:
            traceback.print_exc(e)
            pass

    def win_focus(window):
        if window.title.startswith("zsh:"):
            zsh_pid = int(window.title.split(':')[1])
            ZshTriggerWatch.trigger_zsh(zsh_pid)

    def win_title(window):
        if window == ui.active_window():
            if window.title.startswith("zsh:"):
                zsh_pid = int(window.title.split(':')[1])
                ZshTriggerWatch.trigger_zsh(zsh_pid)

    ui.register('win_focus', win_focus)
    ui.register('win_title', win_title)
