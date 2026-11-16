import itertools

import pytest

_n = itertools.count()


@pytest.fixture
def bus_spec():
    """A fresh in-process virtual bus per test so tests don't hear each other."""
    return f"virtual:test{next(_n)}"
