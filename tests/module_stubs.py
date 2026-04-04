# -*- coding: utf-8 -*-
"""Helpers for temporarily stubbing modules during test imports."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Iterator, Mapping


_MISSING = object()


@contextmanager
def temporary_sys_modules(stubs: Mapping[str, object]) -> Iterator[None]:
    """Temporarily install module stubs and restore the original modules on exit."""
    originals: dict[str, object] = {}
    try:
        for name, module in stubs.items():
            originals[name] = sys.modules.get(name, _MISSING)
            sys.modules[name] = module
        yield
    finally:
        for name, original in originals.items():
            if original is _MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
