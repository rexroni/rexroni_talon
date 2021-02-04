from typing import Any, Optional

from . import pod

class Position(pod.POD):
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


class Range(pod.POD):
    start: Position
    end: Position


class ContentChange(pod.POD):
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


class TextEditOrInsertReplaceEdit(pod.POD):
    # TextEdit is newText + range
    # InsertReplaceEdit is newText + insert + replace
    newText: str
    range: Optional[Range] = None
    insert: Optional[Range] = None
    replace: Optional[Range] = None

    def __init__(self, *arg, **kwarg):
        super().__init__(*arg, **kwarg)
        if self.range is not None:
            if self.insert is not None or self.replace is not None:
                raise TypeError("Invalid TextEdit()")
        else:
            if self.insert is None or self.replace is None:
                raise TypeError("Invalid InsertReplaceEdit()")


class CompletionItem(pod.POD):
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
