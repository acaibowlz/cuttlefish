"""Unit tests for `render.py`: subpath link rewriting and error messages."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from cuttlefish.render import _jinja_detail, _prefix_links


def test_prefix_links():
    html = '<a href="/blog/">x</a> <link href="/css/m.css"> <img src="/i.png">'
    out = _prefix_links(html, "/repo")
    assert 'href="/repo/blog/"' in out
    assert 'href="/repo/css/m.css"' in out
    assert 'src="/repo/i.png"' in out

    # External, protocol-relative, and anchor links are left alone.
    keep = '<a href="https://x.com/">e</a> <a href="//cdn/x">p</a> <a href="#top">a</a>'
    assert _prefix_links(keep, "/repo") == keep


def _error_detail(tmp_path, templates: dict[str, str], **ctx) -> str:
    root = tmp_path / "templates"
    root.mkdir(parents=True)
    for name, source in templates.items():
        (root / name).write_text(source, encoding="utf-8")
    env = Environment(loader=FileSystemLoader(str(root)), undefined=StrictUndefined)
    with pytest.raises(Exception) as exc:
        env.get_template("page.html").render(**ctx)
    return _jinja_detail(exc.value)


def test_undefined_attribute_names_expression_and_template_line(tmp_path):
    # Jinja names the Python type ("'types.SimpleNamespace object' has no
    # attribute ..."); the user needs their own expression and where it is —
    # the template that failed, not the page that extends it.
    detail = _error_detail(
        tmp_path,
        {
            "base.html": "<title>\n{{ site.titel }}</title>",
            "page.html": '{% extends "base.html" %}',
        },
        site=SimpleNamespace(title="T"),
    )
    assert detail == "templates/base.html:2: 'site' has no attribute 'titel'"


def test_undefined_attribute_on_subscript_and_bare_variable(tmp_path):
    detail = _error_detail(
        tmp_path / "a",
        {"page.html": "{{ page.items[0].nope }}"},
        page=SimpleNamespace(items=[SimpleNamespace()]),
    )
    assert detail == "templates/page.html:1: 'page.items[0]' has no attribute 'nope'"

    detail = _error_detail(tmp_path / "b", {"page.html": "{{ missing }}"})
    assert detail == "templates/page.html:1: 'missing' is undefined"


def test_syntax_error_shows_template_relative_path(tmp_path):
    detail = _error_detail(tmp_path, {"page.html": "ok\n{% if %}"})
    assert detail == "templates/page.html:2: Expected an expression, got 'end of statement block'"


def test_missing_template_names_it_without_search_path(tmp_path):
    # TemplateNotFound's own text is the absolute search path.
    detail = _error_detail(tmp_path, {"page.html": '{% include "nope.html" %}'})
    assert detail == "templates/page.html:1: template 'nope.html' not found in templates/"


def test_python_error_in_template_shows_the_source_line(tmp_path):
    detail = _error_detail(
        tmp_path, {"page.html": "{{ site.title() }}"}, site=SimpleNamespace(title="T")
    )
    assert detail == "templates/page.html:1: 'str' object is not callable, in: {{ site.title() }}"
