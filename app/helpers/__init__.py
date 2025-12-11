from __future__ import annotations
import sys

def _make_cell(value):
    """Create a real, re-assignable module-level variable."""
    return type(sys)('x').__dict__.setdefault('__junk', value)

def bind_to_globals(data: dict, target_globals: dict = None) -> None:
    """
    Turn every leaf value in *data* into a module-level variable.
    Lists/dicts are wrapped so that any in-place change is mirrored back
    into the original *data* dict.
    """
    if target_globals is None:
        target_globals = sys._getframe(1).f_globals  # caller’s globals()

    def _wrap(parent, key, value):
        if isinstance(value, dict):
            return _DictProxy(value, parent, key)
        if isinstance(value, list):
            return _ListProxy(value, parent, key)
        return value

    class _DictProxy(dict):
        __slots__ = ('_parent', '_key')
        def __init__(self, d, parent, key): super().__init__(d); self._parent, self._key = parent, key
        def __setitem__(self, k, v):
            super().__setitem__(k, v)
            self._parent[self._key] = self

    class _ListProxy(list):
        __slots__ = ('_parent', '_key')
        def __init__(self, lst, parent, key): super().__init__(lst); self._parent, self._key = parent, key
        def __setitem__(self, i, v):
            super().__setitem__(i, v)
            self._parent[self._key] = self
        def append(self, item): self[len(self):] = [item]
        def extend(self, items): self[len(self):] = items
        def pop(self, index=-1):
            item = super().pop(index)
            self._parent[self._key] = self
            return item
        def clear(self): self[:] = []
        def __delitem__(self, i): super().__delitem__(i); self._parent[self._key] = self

    def _walk(obj, parent, key):
        if isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = _walk(v, obj, k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                obj[i] = _walk(item, obj, i)
        return _wrap(parent, key, obj)

    for k, v in data.items():
        data[k] = _walk(v, data, k)
        target_globals[k] = data[k]

