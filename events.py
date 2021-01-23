"""
events.py contains a select-based event loop within the talon process
(but otherwise independent of talon) for supporting IPC for advanced talon
integrations.

When this file is reloaded, it will shut down any modules which depended on
this event loop; and they must also be reloaded.
"""

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

class EventConsumer:
    def close(self):
        """A consumer must shut down because the event loop is closing."""
        raise NotImplementedError()

    def event(self, key, mask):
        """A consumer got an event"""
        raise NotImplementedError()

# LoopContext is the interface to the event loop provided to a consumer.
class LoopContext:
    def __init__(self, loop, consumer):
        self.loop = loop
        self.consumer = consumer

    def register(self, fileobj, mask, data=None):
        self.loop.selector.register(fileobj, mask, data)
        self.loop.consumers[fileobj] = self.consumer

    def modify(self, fileobj, mask, data=None):
        self.loop.selector.modify(fileobj, mask, data)

    def unregister(self, fileobj):
        self.loop.selector.unregister(fileobj)
        del self.loop.consumers[fileobj]


class EventLoop(threading.Thread):
    def __init__(self):
        # This is the one selector that everyone will use.
        self.selector = selectors.DefaultSelector()

        # Open a control channel.  ctrl_r will be part of the event loop,
        # ctrl_w is for outside of the event loop.
        self.ctrl_r, self.ctrl_w = socket.socketpair()
        self.ctrl_r.setblocking(False)
        self.selector.register(self.ctrl_r, selectors.EVENT_READ)

        # fileobjs maps fileobjs in the select loop to consumers
        self.consumers = {}

        # all_consumers is a set of EventConsumer objects
        self.all_consumers = set()

        self.paused = False
        self.pauser = threading.Condition()

        super().__init__()

    def run(self):
        while True:
            for key, mask in self.selector.select():
                if key.fileobj == self.ctrl_r:
                    msg = self.ctrl_r.recv(4096)
                    for line in msg.splitlines():
                        if line == b"quit":
                            for consumer in self.all_consumers:
                                self.consumer.close()
                            return
                        elif line == b"pause":
                            with self.pauser:
                                self.paused = True
                                self.pauser.notify()
                                # now wait for the pause lock to end
                                while self.paused:
                                    self.pauser.wait()
                            continue
                        raise ValueError(f"unknown control message: {line}")

                # all other fileobjs are from consumers.
                else:
                    self.consumers[key.fileobj].event(key, mask)

    @contextlib.contextmanager
    def register_lock(self):
        """
        Attempt to hide the details of multi-threading during registration
        behind a contextmanager.

        Unless the reload system itself was inside the event loop, some form
        of threading protection is inevitable.
        """

        with self.pauser:
            self.ctrl_w.send(b"pause\n")
            while not self.paused:
                self.pauser.wait()
            self.paused = False

            def register(consumer):
                self.all_consumers.add(consumer)
                return LoopContext(self, consumer)

            try:
                yield register
            finally:
                # End the pause lock
                self.pauser.notify()

    def close(self):
        self.ctrl_w.send(b"quit\n")
        self.join()


@singletons.singleton
def event_loop():
    x = EventLoop()
    x.start()
    yield x
    x.close()
