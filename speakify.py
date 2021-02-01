import re

def extensions(x):
    x = re.sub("\\.py$", " dot pie", x)
    x = re.sub("\\.c$", " dot see", x)
    x = re.sub("\\.h$", " dot h", x)
    x = re.sub("\\.sh$", " dot s h", x)
    x = re.sub("\\.zsh$", " dot z s h", x)
    x = re.sub("\\.go$", " dot go", x)
    return x

def numbers(x):
    x = x.replace("0", " zero ")
    x = x.replace("1", " one ")
    x = x.replace("2", " two ")
    x = x.replace("3", " three ")
    x = x.replace("4", " four ")
    x = x.replace("5", " five ")
    x = x.replace("6", " six ")
    x = x.replace("7", " seven ")
    x = x.replace("8", " eight ")
    x = x.replace("9", " nine ")
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

def get_pronunciations(symbol, prefix="", completer_char=None):
    r"""
    guess reasonable pronunciations for a symbol.

    arguments:
        symbol:
            the complete symbol to be pronounced.  If neither prefix nor
            edit are provided this will also be the text emitted by talon.
        prefix:
            the prefix which has already been typed.  This will effectively
            be removed from the symbol before emitting text.
        completer_char:
            a character to type after typing out a shortened version of a
            text, such as \t to invoke shell completion.  If not provided,
            no shortened symbols will be generated.
    """
    out = {}

    # We'll never re-type the prefix, ever.
    typable = symbol[len(prefix):]

    # If there is a symbol in the prefix, we never allow pronouncing before it.
    # Think of pronouncing "--amend" when "--" is the prefix or "a/b" when "a/"
    # is the prefix.  You wouldn't.
    symboled_prefix = re.match('(.*[0-9._/-])[^0-9._/-]*$', prefix)
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
    shorthand = re.match('^([^0-9._/-]*)[0-9._/-].*$', symbol)
    if shorthand and completer_char is not None:
        shorthand = shorthand[1]
        shortened_by = len(symbol) - len(shorthand)
        typable = typable[:-shortened_by] + completer_char

        variations.append((shorthand, typable))
        if prefix:
            shorthand = re.match(
                '^([^0-9._/-]*)[0-9._/-].*$', symbol[len(prefix):]
            )
            if shorthand:
                shorthand = shorthand[1]
                variations.append((shorthand, typable))

    for base, result in variations:
        if not base:
            continue

        # always start with pronouncing file extensions
        base = extensions(base)

        # always separate numbers into individual digits
        base = numbers(base)

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
