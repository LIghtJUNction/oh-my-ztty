# Documentation website

The website is rendered from the Markdown files in `site/content/`. `site/nav.json` defines the page order, URLs, sidebar groups and short descriptions. The build uses CommonMark with tables and strikethrough; raw HTML is disabled.

## Build locally

Python 3.10 or newer is required for the documentation build:

```sh
python3 -m venv .cache/docs-venv
.cache/docs-venv/bin/python -m pip install --disable-pip-version-check --require-hashes -r site/requirements.txt
.cache/docs-venv/bin/python scripts/build_site.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory _site
```

The renderer and its single dependency are pinned by version and artifact hash. These packages are used only while building the website. The deployed site is ordinary HTML, CSS and small browser scripts; it has no client-side Markdown renderer, external fonts or CDN assets.

The builder checks local links, heading anchors, duplicate IDs and local runtime assets before replacing `_site`. A failed build leaves an existing generated site intact. It refuses to replace an output directory that does not carry its own build marker.

## Write a page

Add one entry to `site/nav.json`, then write its source below `site/content/`. Use one H1 per page, followed by H2/H3 sections. Relative Markdown links such as `installation.md#install-a-release` are converted to static page URLs. Heading IDs use lowercase words joined by hyphens; punctuation is removed and repeated headings receive a numbered suffix.

Code fences become labelled blocks with a copy button when JavaScript is available. Tables remain readable in a horizontally scrollable region. Navigation and document content work without JavaScript.

`site/template.html` owns the document shell. `site/style.css`, `site/app.js` and `site/favicon.svg` are copied to the output root. Local search reads the generated `search-index.json` only when requested; it uses no remote search service. The JSON is an array of `{title, url, description, headings: [{text, id}], text}` records. URLs are relative to the site root.

## Publish

The Pages workflow builds and validates the site on relevant `main` changes, uploads `_site`, and deploys it after the artifact is visible to the Pages API. Website changes do not produce a new software release. The published base URL is `https://lightjunction.github.io/oh-my-ztty/`; `--base-url` supports another HTTPS root for a fork.
