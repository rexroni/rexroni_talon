import json
import enum

def make_content(parsed, headers=None):
    if headers:
        headers = "\r\n".join([f"{k}: {v}" for k, v in headers.items()])
        headers = headers + "\r\n"
    else:
        headers = ""
    body = json.dumps(parsed)
    msg = f"Content-Length: {len(body)}\r\n{headers}\r\n{body}"
    return msg.encode("utf8")

class IDGen:
    def __init__(self, name):
        self.name = name
        self.count = -1

    def __iter__(self):
        return self

    def __next__(self):
        self.count += 1
        return f"{self.name}:{self.count}"

class Parser:
    def __init__(self, cb):
        self.cb = cb
        self.reset(b'')

    def reset(self, leftover):
        self.buf = leftover
        self.header_length = None
        self.full_length = None

    def find_headers(self):
        """Return True if headers are found."""
        if self.full_length is not None:
            return True

        sep = None
        if b'\r\n\r\n' in self.buf:
            sep = b'\r\n'
        elif b'\n\n' in self.buf:
            sep = b'\n'
        if sep is None:
            return False

        self.header_length = self.buf.index(sep + sep) + 2*len(sep)
        self.headers = {}
        header = self.buf[:self.header_length]
        # make sure there is a Content-Length header
        content_length_found = True
        for line in header.rstrip(sep).split(sep):
            if b'Content-Length:' in line:
                content_length = int(line.split()[1])
                self.full_length = content_length + self.header_length
                content_length_found = True
            field, body = line.split(b":", 1)
            self.headers[field.decode('utf8')] = body.strip().decode('utf8')
        if not content_length_found:
            raise ValueError(f"message missing Content-Length: {self.buf}")

        return True

    def find_full_message(self):
        """Return True if a full message is found."""
        if len(self.buf) < self.full_length:
            return False

        full = self.buf[:self.full_length]
        body = full[self.header_length:]
        self.cb(full, body, self.headers)
        self.reset(self.buf[self.full_length:])
        return True

    def feed(self, msg):
        self.buf += msg

        # Parse multiple messages if necesary
        while True:
            # Parse headers (cacheable).
            if not self.find_headers():
                return
            # Collect the whole Content-Length + headers.
            if not self.find_full_message():
                return

class SymbolKind(enum.Enum):
    File = 1
    Module = 2
    Namespace = 3
    Package = 4
    Class = 5
    Method = 6
    Property = 7
    Field = 8
    Constructor = 9
    Enum = 10
    Interface = 11
    Function = 12
    Variable = 13
    Constant = 14
    String = 15
    Number = 16
    Boolean = 17
    Array = 18
    Object = 19
    Key = 20
    Null = 21
    EnumMember = 22
    Struct = 23
    Event = 24
    Operator = 25
    TypeParameter = 26
