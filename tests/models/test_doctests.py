"""Run doctests embedded in source modules."""

import doctest

import linguaalayam.models.entries as entries_module


def test_entries_doctests():
    results = doctest.testmod(entries_module, verbose=False)
    assert results.failed == 0, f"{results.failed} doctest(s) failed in models/entries.py"
