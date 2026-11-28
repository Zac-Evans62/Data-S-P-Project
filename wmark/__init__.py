"""Keyed text watermarking project: shared library.

Everything that must behave identically across the team (word rules,
scoring, settings, the passage manifest) lives in this package. Scripts in
``scripts/`` import from here so there is exactly one implementation.
"""
