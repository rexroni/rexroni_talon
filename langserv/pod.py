"""
The pod module defines the POD baseclass for plain-old data, which is easily
json-serializable.

A couple of talon modules in this repository POD for marshaling and
unmarshaling json-encoded structs.

Probably this is infrastructure overkill for the scope of this repository, but
hey, it's a for-fun project.
"""

import inspect
from typing import Dict, Optional, Union

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


class POD:
    """
    POD is a baseclass for plain-old-data types which defines useful primitives
    for handling data-like objects.

    POD's __init__ automatically supports the following usages:

      - initialization accepting keyword-only arguments corresponding to
        class type annotations
      - initialization by a single dictionary type, for automatic json-like
        parsing
      - initialization by a single object of matching type, with copy
        semantics

    POD also implements the following useful APIs:

      - recursive value-based __eq__ test
      - useful __repr__ output
      - a to_dict() method which can be fed to json.dumps()

    For example:

        class Foo(POD):
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

    If you need to write an __init__, always accept (*arg, **kwarg) and start
    by calling super().__init__(*arg, **kwarg).
    """
    def __init__(self, *args, **kwargs):
        # Create an automatic signature based on the class's __annotations__.
        params = []
        dct = vars(type(self))
        for attr, anno in self.__annotations__.items():
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

        # Create a more generic __init__ signature with a single
        # positional-only argument like this:
        #
        #   def __init__(_obj=None, /, **kwarg)
        #
        # Syntatically this can only be created with python 3.8 or greater, but
        # it's possible to do with the inspect module as of python 3.3.
        #
        # If _obj is none we will bind **kwarg to auto_sig.
        init_sig = inspect.Signature(
            [
                inspect.Parameter(
                    "_obj",
                    inspect.Parameter.POSITIONAL_ONLY,
                    default=None,
                ),
                inspect.Parameter(
                    "kwargs",
                    inspect.Parameter.VAR_KEYWORD,
                ),
            ]
        )

        # Bind the given arguments to the dynamically-created signature.
        bound = init_sig.bind(*args, **kwargs)
        _obj = bound.arguments.get("_obj")
        kwargs = bound.arguments.get("kwargs", {})
        if "_obj" in bound.arguments and kwargs:
            raise TypeError(
                "you must provide either a single positional argument (for "
                "the dict or copy constructor) or only keyword arguments (for "
                "the normal constructor)"
            )

        def auto_init(kwargs):
            bound = auto_sig.bind(**kwargs)
            # Call setattr for all kwargs.
            for attr, value in bound.arguments.items():
                if attr == "_obj":
                    continue
                anno = self.__annotations__[attr]
                anno = _remove_optional(anno)
                if isinstance(anno, type) and issubclass(anno, POD):
                    # Invoke either the copy or parsing constructor.
                    setattr(self, attr, anno(value))
                else:
                    # Use the value directly.
                    setattr(self, attr, value)

        def auto_copy(other):
            # Call setattr for all the attrs present on other.
            for attr, value in vars(other).items():
                if attr == "_obj":
                    continue
                if isinstance(value, POD):
                    # Use copy constructor.
                    setattr(self, attr, type(value)(value))
                else:
                    # Use the value directly.
                    setattr(self, attr, value)

        if _obj is None:
            auto_init(kwargs)
        elif isinstance(_obj, dict):
            auto_init(_obj)
        elif type(self) is type(_obj):
            auto_copy(_obj)
        else:
            raise TypeError(
                f"{type(self).__name__}() called with parameter of type "
                f"{type(_obj).__name__} which is neither a dictionary nor "
                f"another {type(self).__name__}"
            )

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

if __name__ == "__main__":
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

    # More complex annotations.
    class Meh(POD):
        a: Dict
        b: Dict[str, int]

    _ = Meh(a={}, b={"1": 1})
