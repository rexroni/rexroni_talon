# This files is modeled after knausj_talon's user_settings.py but simpler.

from talon import Module, fs, Context
import os
import re
import csv
from typing import Dict, List, Tuple, Iterable
import threading


UPDATES_DIR = os.path.join(os.path.dirname(__file__), "updates")
os.makedirs(UPDATES_DIR, exist_ok=True)

def extensions(x):
    x = re.sub("\\.py$", " dot pie", x)
    x = re.sub("\\.c$", " dot see", x)
    x = re.sub("\\.h$", " dot h", x)
    x = re.sub("\\.sh$", " dot s h", x)
    return x

def speakify(x, symbols):
    symbols = symbols or ""
    x = re.sub("\\.", " dot " if '.' in symbols else ' ', x)
    x = re.sub("_", " under " if '_' in symbols else ' ', x)
    x = re.sub("-", " dash " if '-' in symbols else ' ', x)
    # talon pukes on multiple spaces
    x = re.sub(" +", " ", x)
    # talon also pukes on leading spaces
    return x.strip()


def get_pronunciations(symbol, pronunciation=None):
    # Skip this for explicit pronunciations.
    if pronunciation is not None:
        return {pronunciation: symbol}

    out = {}

    # skip anything with a slash?
    # TODO: this breaks multi-stage completions.
    if '/' in symbol:
        return out

    # always start with pronouncing extensions
    x = extensions(symbol)

    # then try to support the plainest form
    out[speakify(x, None)] = symbol

    # support the most explicit form
    out[speakify(x, '._-')] = symbol

    # support the one-of-each forms
    out[speakify(x, '.')] = symbol
    out[speakify(x, '_')] = symbol
    out[speakify(x, '-')] = symbol

    return out


def csv_to_dict(f: Iterable) -> Dict[str, str]:
    """
    Load a csv of symbols[, pronunciations] and return a dict of
    pronunciations->symbols.

    f should be an iterable of lines, such as with `open(...) as f`.
    """
    def uncommented(f) -> Iterable:
        for row in f:
            # ignore comments
            if not row.startswith("#"):
                yield row

    # TODO: handle prefixes somehow.  Some prefixes need to be stripped out
    # like ../ or -- but other fixes should still be spoken, like if your
    # prefix was 'm' and you wanted to complete 'make'

    reader = csv.reader(uncommented(f))

    out = {}
    for row in reader:
        # ignore empty rows
        if len(row) == 0:
            continue
        assert len(row) < 3, f"malformed row: {row}"
        symbol = row[0]
        pronunciation = row[1] if len(row) == 2 else None
        out.update(get_pronunciations(symbol, pronunciation))

    return out


# callbacks should be of the form:
#   def fn(relpath, path, exists)
callbacks = {}

def on_file_update(path: str, flags):
    relpath = os.path.relpath(path, UPDATES_DIR)
    for match, fn in callbacks.items():
        if relpath.startswith(match):
            fn(relpath, path, flags.exists)

def add_updates_callback(match, fn):
    callbacks[match] = fn

fs.watch(UPDATES_DIR, on_file_update)
