"""cuttlefish — agentic static site generator."""

from importlib.metadata import version

# Read from the installed package so pyproject.toml stays the single source.
__version__ = version("cuttlefish-ssg")
