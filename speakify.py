import re

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

def get_pronunciations(symbol, prefix="", completer_char=None):
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
    if shorthand and completer_char is not None:
        shorthand = shorthand[1]
        shortened_by = len(symbol) - len(shorthand)
        typable = typable[:-shortened_by] + completer_char

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
