#!/usr/bin/env python3
"""Build the static documentation site from CommonMark sources."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
from string import Template
import sys
import tempfile
import unicodedata
from urllib.parse import unquote, urlsplit, urlunsplit
from xml.sax.saxutils import escape as xml_escape

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"
CONTENT = SITE / "content"
DEFAULT_BASE = "https://lightjunction.github.io/oh-my-ztty/"
SOURCE_REPO = "https://github.com/LIghtJUNction/oh-my-ztty"
MARKER = ".oh-my-ztty-docs-build"
ASSETS = ("style.css", "app.js", "favicon.svg")


class BuildError(Exception):
    """An actionable input or output error."""


@dataclass(frozen=True)
class Page:
    slug: str
    title: str
    source: str
    description: str
    group: str

    @property
    def route(self) -> str:
        return self.slug + "/" if self.slug else "./"

    @property
    def filename(self) -> PurePosixPath:
        return PurePosixPath(self.slug, "index.html") if self.slug else PurePosixPath("index.html")

    @property
    def root(self) -> str:
        return "../" if self.slug else "./"


def load_pages() -> list[Page]:
    navigation = json.loads((SITE / "nav.json").read_text(encoding="utf-8"))
    groups = navigation.get("groups")
    if not isinstance(groups, list) or not groups:
        raise BuildError("site/nav.json needs a non-empty groups list")
    pages: list[Page] = []
    slugs: set[str] = set()
    sources: set[str] = set()
    for group in groups:
        label, entries = group.get("label"), group.get("pages")
        if not isinstance(label, str) or not label or not isinstance(entries, list):
            raise BuildError("Each navigation group needs a label and pages list")
        for entry in entries:
            if not all(isinstance(entry.get(k), str) for k in ("slug", "title", "source", "description")):
                raise BuildError("Every page needs string slug, title, source and description fields")
            page = Page(group=label, **{k: entry[k] for k in ("slug", "title", "source", "description")})
            if page.slug and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", page.slug):
                raise BuildError(f"Invalid single-level page slug: {page.slug!r}")
            path = PurePosixPath(page.source)
            if path.is_absolute() or ".." in path.parts or path.suffix != ".md":
                raise BuildError(f"Invalid Markdown source: {page.source!r}")
            resolved = (CONTENT / path).resolve()
            if not resolved.is_relative_to(CONTENT.resolve()) or not resolved.is_file():
                raise BuildError(f"Missing Markdown source: site/content/{page.source}")
            if page.slug in slugs or page.source in sources:
                raise BuildError(f"Duplicate page slug or source: {page.source}")
            if not page.title.strip() or not page.description.strip():
                raise BuildError(f"Empty page title or description: {page.source}")
            slugs.add(page.slug)
            sources.add(page.source)
            pages.append(page)
    if not pages or pages[0].slug != "":
        raise BuildError("The first page must be the home page with an empty slug")
    return pages


def plain_inline(tokens: list) -> str:
    parts = []
    for token in tokens:
        if token.type in ("text", "code_inline"):
            parts.append(token.content)
        elif token.type in ("softbreak", "hardbreak"):
            parts.append(" ")
        elif token.children:
            parts.append(plain_inline(token.children))
    return "".join(parts)


def heading_slug(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).lower()
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"[\s-]+", "-", value).strip("-") or "section"


def href_for(page: Page, root: str) -> str:
    return root + page.slug + "/" if page.slug else root


def sidebar(pages: list[Page], current: Page | None, root: str) -> str:
    parts = ['<nav class="sidebar-nav" aria-label="Documentation">']
    previous_group = None
    for page in pages:
        if page.group != previous_group:
            if previous_group is not None:
                parts.append("</ul></div>")
            parts.append(f'<div class="nav-group"><p class="nav-label">{escape(page.group)}</p><ul>')
            previous_group = page.group
        active = ' aria-current="page"' if page == current else ""
        parts.append(
            f'<li><a class="nav-link" href="{escape(href_for(page, root), quote=True)}"{active}>'
            f"{escape(page.title)}</a></li>"
        )
    parts.append("</ul></div></nav>")
    return "\n".join(parts)


def pagination(pages: list[Page], index: int, root: str) -> str:
    parts = []
    for offset, direction, label in ((-1, "prev", "Previous"), (1, "next", "Next")):
        target = index + offset
        if not 0 <= target < len(pages):
            parts.append('<span class="pagination-spacer" aria-hidden="true"></span>')
            continue
        page = pages[target]
        parts.append(
            f'<a class="pagination-link {direction}" href="{escape(href_for(page, root), quote=True)}" '
            f'aria-label="{escape(label + " page: " + page.title, quote=True)}">'
            f'<span class="pagination-label">{label}</span>'
            f'<span class="pagination-title">{escape(page.title)}</span></a>'
        )
    return "\n".join(parts)


def rewrite_links(tokens: list, page: Page, by_source: dict[str, Page]) -> None:
    for token in tokens:
        if token.type == "link_open":
            href = token.attrGet("href")
            if href:
                url = urlsplit(href)
                if not url.scheme and not url.netloc and url.path.endswith(".md"):
                    source = posixpath.normpath(posixpath.join(posixpath.dirname(page.source), unquote(url.path)))
                    target = by_source.get(source)
                    if target is None:
                        raise BuildError(f"{page.source}: Markdown link has no page: {href}")
                    token.attrSet("href", urlunsplit(("", "", href_for(target, page.root), url.query, url.fragment)))
        if token.children:
            rewrite_links(token.children, page, by_source)


def make_markdown():
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:
        raise BuildError("Install site/requirements.txt in a virtual environment before building") from exc
    md = MarkdownIt("commonmark", {"html": False, "typographer": False})
    md.enable(["table", "strikethrough"])

    def fence(tokens, index, options, env):
        token = tokens[index]
        info = token.info.strip().split()
        language = info[0] if info else "text"
        env["code_number"] += 1
        code_id = f'code-{env["code_number"]}'
        while code_id in env["ids"]:
            env["code_number"] += 1
            code_id = f'code-{env["code_number"]}'
        env["ids"].add(code_id)
        language_class = re.sub(r"[^a-zA-Z0-9_-]", "", language)
        return (
            '<div class="code-block">\n<div class="code-toolbar">'
            f'<span class="code-language">{escape(language)}</span>'
            f'<button class="copy-button" type="button" data-copy="{code_id}" '
            f'aria-label="Copy {escape(language, quote=True)} code" hidden>Copy</button></div>\n'
            f'<pre id="{code_id}" tabindex="0"><code class="language-{language_class}">'
            f"{escape(token.content)}</code></pre>\n</div>\n"
        )

    md.renderer.rules["fence"] = fence
    original_open = md.renderer.rules.get("table_open")
    original_close = md.renderer.rules.get("table_close")

    def table_open(tokens, index, options, env):
        rendered = original_open(tokens, index, options, env) if original_open else md.renderer.renderToken(tokens, index, options, env)
        return '<div class="table-wrap" role="region" aria-label="Documentation table" tabindex="0">\n' + rendered

    def table_close(tokens, index, options, env):
        rendered = original_close(tokens, index, options, env) if original_close else md.renderer.renderToken(tokens, index, options, env)
        return rendered + "</div>\n"

    md.renderer.rules["table_open"] = table_open
    md.renderer.rules["table_close"] = table_close
    return md


def render_markdown(md, page: Page, by_source: dict[str, Page]):
    from markdown_it.token import Token

    text = (CONTENT / page.source).read_text(encoding="utf-8")
    env = {"ids": set(), "code_number": 0}
    tokens = md.parse(text, env)
    headings = []
    searchable = [
        plain_inline(token.children or []) if token.type == "inline" else token.content
        for token in tokens if token.type in ("inline", "fence", "code_block")
    ]
    h1_count = 0
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        level = int(token.tag[1:])
        h1_count += level == 1
        inline = tokens[index + 1]
        label = plain_inline(inline.children or [])
        base = heading_slug(label)
        anchor = base
        suffix = 1
        while anchor in env["ids"]:
            suffix += 1
            anchor = f"{base}-{suffix}"
        env["ids"].add(anchor)
        token.attrSet("id", anchor)
        if level in (2, 3):
            headings.append({"text": label, "id": anchor, "level": level})
            link = Token("link_open", "a", 1)
            link.attrSet("class", "heading-anchor")
            link.attrSet("href", "#" + anchor)
            link.attrSet("aria-label", "Link to " + label)
            symbol = Token("text", "", 0)
            symbol.content = "#"
            inline.children = (inline.children or []) + [link, symbol, Token("link_close", "a", -1)]
    if h1_count != 1:
        raise BuildError(f"{page.source}: expected one H1, found {h1_count}")
    rewrite_links(tokens, page, by_source)
    content = md.renderer.render(tokens, md.options, env)
    toc = '<ul class="toc-list">\n' + "\n".join(
        f'<li class="toc-level-{h["level"]}"><a href="#{escape(h["id"], quote=True)}">'
        f'{escape(h["text"])}</a></li>' for h in headings
    ) + "\n</ul>" if headings else ""
    return content, toc, headings, " ".join(" ".join(searchable).split())


class HTMLReferences(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.duplicates: set[str] = set()
        self.links: list[tuple[str, str, bool]] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            value = values["id"]
            if value in self.ids:
                self.duplicates.add(value)
            self.ids.add(value)
        for attribute in ("href", "src"):
            value = values.get(attribute)
            if value:
                asset = attribute == "src" or tag == "link" and values.get("rel") in ("stylesheet", "icon", "preload")
                self.links.append((tag, value, asset))


def validate_site(output: Path, base_url: str) -> int:
    base = urlsplit(base_url)
    base_path = base.path
    parsed: dict[Path, HTMLReferences] = {}
    for file in sorted(output.rglob("*.html")):
        doc = HTMLReferences()
        doc.feed(file.read_text(encoding="utf-8"))
        if doc.duplicates:
            raise BuildError(f"{file.relative_to(output)} has duplicate IDs: {sorted(doc.duplicates)}")
        parsed[file.resolve()] = doc
    checked = 0
    for file, doc in parsed.items():
        relative = file.relative_to(output)
        for tag, href, asset in doc.links:
            url = urlsplit(href)
            if url.scheme or url.netloc:
                local_absolute = url.scheme in ("http", "https") and url.netloc == base.netloc and url.path.startswith(base_path)
                if not local_absolute:
                    if asset:
                        raise BuildError(f"{relative}: external runtime asset is not allowed: {href}")
                    if url.scheme and url.scheme not in ("http", "https", "mailto"):
                        raise BuildError(f"{relative}: unsupported URL scheme: {href}")
                    continue
                path = unquote(url.path[len(base_path):])
                target = output / path
            elif url.path.startswith("/"):
                if not url.path.startswith(base_path):
                    raise BuildError(f"{relative}: absolute link leaves the site base path: {href}")
                target = output / unquote(url.path[len(base_path):])
            elif url.path:
                target = file.parent / unquote(url.path)
            else:
                target = file
            target = target.resolve()
            if not target.is_relative_to(output.resolve()):
                raise BuildError(f"{relative}: local link escapes the generated site: {href}")
            if target.is_dir() or url.path.endswith("/"):
                target /= "index.html"
            if not target.is_file():
                raise BuildError(f"{relative}: missing local target: {href}")
            if url.fragment and target.suffix == ".html":
                target_doc = parsed.get(target.resolve())
                if target_doc is None or unquote(url.fragment) not in target_doc.ids:
                    raise BuildError(f"{relative}: missing local heading: {href}")
            checked += 1
    return checked


def build(output: Path, base_url: str) -> dict:
    if output.is_symlink():
        raise BuildError("The output directory must not be a symlink")
    output = output.resolve()
    if output == REPO or output == SITE or SITE.is_relative_to(output):
        raise BuildError("The output directory must not contain source files")
    if output.exists() and (not output.is_dir() or not (output / MARKER).is_file()):
        raise BuildError(f"Refusing to replace unmarked output directory: {output}")
    split = urlsplit(base_url)
    if split.scheme != "https" or not split.netloc or split.query or split.fragment:
        raise BuildError("--base-url must be an absolute HTTPS URL without a query or fragment")
    base_url = base_url.rstrip("/") + "/"
    pages = load_pages()
    by_source = {page.source: page for page in pages}
    version = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    template = Template((SITE / "template.html").read_text(encoding="utf-8"))
    md = make_markdown()
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".docs-build-", dir=output.parent))
    old_output = None
    try:
        records = []
        for index, page in enumerate(pages):
            content, toc, headings, text = render_markdown(md, page, by_source)
            source_path = "site/content/" + page.source
            values = {
                "page_title": escape(page.title, quote=True),
                "description": escape(page.description, quote=True),
                "canonical_url": escape(base_url + (page.slug + "/" if page.slug else ""), quote=True),
                "root": page.root,
                "version": escape(version),
                "sidebar": sidebar(pages, page, page.root),
                "breadcrumb": escape(page.group),
                "content": content,
                "toc": toc,
                "pagination": pagination(pages, index, page.root),
                "edit_url": SOURCE_REPO + "/edit/main/" + source_path,
                "source_url": SOURCE_REPO + "/blob/main/" + source_path,
                "search_url": page.root + "search-index.json",
            }
            rendered = template.substitute(values)
            target = staging / page.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered, encoding="utf-8")
            records.append({
                "title": page.title,
                "url": page.route,
                "description": page.description,
                "headings": [{"text": h["text"], "id": h["id"]} for h in headings],
                "text": text,
            })
        root = urlsplit(base_url).path
        not_found = template.substitute(
            page_title="Page not found",
            description="This documentation page does not exist. Return to the oh-my-ztty documentation.",
            canonical_url=escape(base_url + "404.html", quote=True),
            root=escape(root, quote=True),
            version=escape(version),
            sidebar=sidebar(pages, None, root),
            breadcrumb="Documentation",
            content='<p class="page-kicker">404</p><h1 id="page-not-found">Page not found</h1>'
            '<p>The page may have moved, or the address may be incomplete.</p>'
            f'<p><a href="{escape(root, quote=True)}">Return to the documentation</a> or use search to find a topic.</p>',
            toc="",
            pagination="",
            edit_url=SOURCE_REPO + "/edit/main/scripts/build_site.py",
            source_url=SOURCE_REPO + "/blob/main/scripts/build_site.py",
            search_url=escape(root + "search-index.json", quote=True),
        )
        (staging / "404.html").write_text(not_found, encoding="utf-8")
        for asset in ASSETS:
            source = SITE / asset
            if not source.is_file():
                raise BuildError(f"Missing site asset: {source.relative_to(REPO)}")
            shutil.copyfile(source, staging / asset)
        (staging / "search-index.json").write_text(
            json.dumps(records, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
        )
        (staging / ".nojekyll").write_text("", encoding="utf-8")
        (staging / MARKER).write_text("oh-my-ztty static documentation\n", encoding="utf-8")
        sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for page in pages:
            sitemap += "<url><loc>" + xml_escape(base_url + (page.slug + "/" if page.slug else "")) + "</loc></url>\n"
        (staging / "sitemap.xml").write_text(sitemap + "</urlset>\n", encoding="utf-8")
        links_checked = validate_site(staging, base_url)
        generated_files = sum(1 for path in staging.rglob("*") if path.is_file())
        total_bytes = sum(path.stat().st_size for path in staging.rglob("*") if path.is_file())
        if output.exists():
            old_output = Path(tempfile.mkdtemp(prefix=".docs-previous-", dir=output.parent))
            old_output.rmdir()
            output.rename(old_output)
        try:
            staging.rename(output)
        except BaseException:
            if old_output is not None:
                old_output.rename(output)
                old_output = None
            raise
        if old_output is not None:
            shutil.rmtree(old_output)
        return {
            "pages": len(pages),
            "files": generated_files,
            "bytes": total_bytes,
            "local_links_checked": links_checked,
            "output": str(output),
        }
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPO / "_site", help="Generated site directory")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="Public HTTPS site root, including repository prefix")
    args = parser.parse_args()
    try:
        result = build(args.output, args.base_url)
    except (BuildError, ValueError, KeyError, OSError) as exc:
        print(f"Documentation build failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
