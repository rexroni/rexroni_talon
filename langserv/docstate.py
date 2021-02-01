import dataclasses
import inspect
import json

import typing
from typing import Any, List, Optional, Union

UnionType = type(Union[int, str])


def _is_optional(anno):
    if not isinstance(anno, UnionType):
        return False
    if len(anno.__args__) != 2:
        return False
    return type(None) in anno.__args__


def _remove_optional(anno):
    if not isinstance(anno, UnionType):
        return anno
    if type(None) not in anno.__args__ or len(anno.__args__) != 2:
        return anno
    index = int(anno.__args__[0] is type(None))
    return anno.__args__[index]


class PODMeta(type):
    """
    PODMeta is a metaclass for plain-old-data types which defines useful
    primitives for handling data-like objects.

    PODMeta-based classes automatically support the following APIs:

      - initialization accepting keyword-only arguments corresponding to
        class type annotations
      - initialization by a single dictionary type, for automatic json-like
        parsing
      - initialization by a single object of matching type, with copy semantics


    For example:

        class Foo(metaclass=PODMeta):
            a: str
            b: typing.Optional[str] = None

        # Initialize with keyword-only args:
        f1 = Foo(a="asdf", b="zxcv")
        # Initialize with a dictionary:
        f2 = Foo({"a": "asdf", "b": "zxcv"})
        # Copy constructor
        f3 = Foo(f1)

        # Evaluates to True
        f1 == f2 == f3


    PODMeta depends on python3.8 or greater.
    """

    def __new__(cls, name, bases, dct):
        old_init = dct.get("__init__")

        # Create an automatic signature based on the class's __annotations__.
        params = []
        for attr, anno in dct.get("__annotations__", {}).items():
            kind = inspect.Parameter.KEYWORD_ONLY
            # Validate defaults.  Only support None for now.
            default = inspect.Parameter.empty
            if attr in dct:
                if dct[attr] is not None:
                    raise TypeError(
                        f"have non-None default in annotation for {name}.{attr}: {anno}"
                    )
                if not _is_optional(anno):
                    raise TypeError(
                        f"have default value for non-optional annotation for {name}.{attr}: {anno}"
                    )
                default = None
            # Further validation on supported annotations.
            anno = _remove_optional(anno)
            if isinstance(anno, UnionType):
                raise TypeError(
                    f"have Union type annotation for {name}.{attr}: {anno}, which is not supported"
                )
            params.append(
                inspect.Parameter(attr, kind, default=default, annotation=anno)
            )
        auto_sig = inspect.Signature(params)

        # Set all the attributes that are passed as arguments.
        def auto_init(self, **kwargs):
            bound = auto_sig.bind(**kwargs)
            for attr, value in bound.arguments.items():
                anno = self.__annotations__[attr]
                anno = _remove_optional(anno)
                if type(anno) is PODMeta:
                    # Invoke either the copy or parsing constructor.
                    setattr(self, attr, anno(value))
                else:
                    # Use the value directly.
                    setattr(self, attr, value)

        def auto_copy(self, other):
            for attr, value in vars(other).items():
                if type(type(value)) is PODMeta:
                    # Use copy constructor.
                    setattr(self, attr, type(value)(value))
                else:
                    # Use the value directly.
                    setattr(self, attr, value)

        # the _obj can be passed only as a positional argument, but it's
        # optional.  The remaining keyword arguments are bound to auto_sig.
        def new_init(self, _obj=None, /, **kwargs):
            if _obj is None:
                auto_init(self, **kwargs)
            elif isinstance(_obj, dict):
                auto_init(self, **_obj)
            elif isinstance(_obj, type(self)):
                auto_copy(self, _obj)
            else:
                raise TypeError(
                    f"{name}() called with parameter of type "
                    f"{type(_obj).__name__} which is neither a dictionary nor "
                    f"another {name}"
                )

            if old_init is not None:
                old_init(self)

        dct["__init__"] = new_init

        return super().__new__(cls, name, bases, dct)


class POD(metaclass=PODMeta):
    # This is mostly for mypy's benefit.
    def __init__(self, *_, **__) -> None:
        pass

    def __eq__(self, other):
        # Require exact type equality.
        if type(self) != type(other):
            return False
        for attr in getattr(self, "__annotations__", []):
            if not getattr(self, attr) == getattr(other, attr):
                return False
        return True

    def to_dict(self, explicit_nones=False) -> dict:
        out = {}
        if explicit_nones:
            attrs = iter(getattr(self, "__annotations__", []))
        else:
            attrs = iter(vars(self))
        for attr in attrs:
            val = getattr(self, attr)
            if type(type(val)) is PODMeta:
                val = val.to_dict(explicit_nones)
            out[attr] = val
        return out

    def __repr__(self) -> str:
        cls = type(self).__name__
        args = [f"{attr}={value.__repr__()}" for attr, value in vars(self).items()]
        return f"{cls}({', '.join(args)})"

    __str__ = __repr__


class Position(POD):
    line: int
    character: int

    def index(self, text):
        i = 0
        for l in range(self.line):
            i = text.find("\n", i) + 1
            if i == 0:
                count = text.count("\n")
                raise ValueError(
                    f"unable to find {self} in text with {count} lines:\n"
                    f"{text}\n----------------------"
                )
        return i + self.character


class Range(POD):
    start: Position
    end: Position


class ContentChange(POD):
    text: str
    range: Optional[Range] = None
    # deprecated and unused
    rangeLength: Optional[int] = None

    def apply(self, text: str) -> str:
        if self.range is None:
            if self.rangeLength is not None:
                raise ValueError("unsure how to handle deprecated rangeLength")
            # Full doc rewrite.
            return self.text
        try:
            start = self.range.start.index(text)
            end = self.range.end.index(text)
        except ValueError as e:
            raise ValueError(f"error applying {self}") from e
        return text[:start] + self.text + text[end :]


class TextEditOrInsertReplaceEdit(POD):
    # TextEdit is newText + range
    # InsertReplaceEdit is newText + insert + replace
    newText: str
    range: Optional[Range] = None
    insert: Optional[Range] = None
    replace: Optional[Range] = None

    def __init__(self, *arg, **kwarg):
        if self.range is not None:
            if self.insert is not None or self.replace is not None:
                raise TypeError("Invalid TextEdit()")
        else:
            if self.insert is None or self.replace is None:
                raise TypeError("Invalid InsertReplaceEdit()")


class CompletionItem(POD):
    # The label of this completion item. By default
    # also the text that is inserted when selecting
    # this completion.
    label: str

    # A string that should be inserted into a document when selecting
    # this completion. When `falsy` the label is used.
    insertText: Optional[str] = None

    # An edit which is applied to a document when selecting this completion.
    # When an edit is provided the value of `insertText` is ignored.
    textEdit: Optional[TextEditOrInsertReplaceEdit] = None

    # fields we don't care about
    kind: Optional[int] = None
    detail: Optional[str] = None
    deprecated: Optional[bool] = None
    preselct: Optional[bool] = None
    sortText: Optional[str] = None
    filterText: Optional[str] = None

    # fields we don't even parse correctly
    documentation: Optional[Any] = None
    tags: Optional[Any] = None
    insertTextFormat: Optional[Any] = None
    insertTextMode: Optional[Any] = None
    additionalTextEdits: Optional[Any] = None
    commitCharacters: Optional[Any] = None
    command: Optional[Any] = None
    data: Optional[Any] = None


class Document:
    def __init__(self, text: str) -> None:
        self.text = text

    def did_change(self, change: ContentChange) -> None:
        self.text = change.apply(self.text)


# Test driver.
if __name__ == "__main__":
    def test_pod():
        class Foo(POD):
            a: str
            b: Optional[str] = None

        class Bar(POD):
            foo: Foo
            opt: Optional[Foo] = None

        # Various constructors.
        f1 = Foo(a="asdf", b="zxcv")
        f2 = Foo({"a": "asdf", "b": "zxcv"})
        f3 = Foo(f1)
        assert f1 == f2 == f3
        b1 = Bar(foo=Foo(a="asdf"), opt=Foo(a="fdsa"))
        b2 = Bar({"foo": Foo(a="asdf"), "opt": {"a": "fdsa"}})
        b3 = Bar({"foo": {"a": "asdf"}, "opt": {"a": "fdsa"}})
        b4 = Bar(b1)
        assert b1 == b2 == b3 == b4

        # Copy semantics.
        f4 = Foo(a="asdf")
        f5 = Foo(f4)
        f4.b = "zxcv"
        assert f4 != f5

        b5 = Bar(foo=Foo(a="asdf"))
        b6 = Bar(b5)
        b5.foo.a = "zxcv"
        assert b5 != b6

    def test_document():
        doc = Document(text="\n")
        assert doc.text == "\n"

        change = ContentChange({
          "range": {
            "end": {
              "character": 0,
              "line": 1
            },
            "start": {
              "character": 0,
              "line": 0
            }
          },
          "text": "this is a test\n",
          "rangeLength": 0
        })

        doc.did_change(change)
        assert doc.text == "this is a test\n"

        change = ContentChange({
          "range": {
            "end": {
              "character": 0,
              "line": 1
            },
            "start": {
              "character": 7,
              "line": 0
            }
          },
          "text": "\nyet another\ntest!\n",
          "rangeLength": 7
        })

        doc.did_change(change)
        assert doc.text == "this is\nyet another\ntest!\n"

        doc = Document(text="test_string = \"asdf\"\nthis is a test\n")

        change = ContentChange({
          "range": {
            "end": {
              "character": 0,
              "line": 1
            },
            "start": {
              "character": 0,
              "line": 1
            }
          },
          "text": "ano\n",
          "rangeLength": 0
        })
        doc.did_change(change)
        assert doc.text == "test_string = \"asdf\"\nano\nthis is a test\n"

    test_pod()
    test_document()
