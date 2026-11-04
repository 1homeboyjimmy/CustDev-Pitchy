# Market research with Scrapy

The research stage evaluates the Russian market. Reddit and X provide
international references and are excluded from Russian demand counts.
Existing saved runs remain readable and are not automatically recollected.

## Flow

1. The configured search provider discovers links for every research angle:
   DDGS, SearXNG, Exa, Google CSE or Brave. Query planning uses the Polza `search`
   model, with English queries for Reddit/X and Russian queries for other sites.
   Without a working LLM, discovery falls back to the product description.
2. A separate Scrapy process reads all discovered sources, including the
   existing Russian sites. It prevents reactor conflicts between Flask jobs.
3. Reddit public JSON supplies the post and nested replies. If unavailable,
   the collector tries the public HTML page. X uses Chromium through
   scrapy-playwright. Other sites use article selectors, visible comments and
   JSON-LD, with browser rendering for empty pages and dynamic discussions.
4. Results preserve text, excerpts, comment links, dates when available,
   collection status and egress. Only successfully fetched pages enter the
   evidence set. Search snippets and block pages do not count as demand.
5. The Polza `signals` model synthesizes Russian evidence and foreign experience
   separately. The same distinction is passed to the final verdict model.

Public access does not guarantee complete discussions. Login walls, removed
posts, rate limits, collapsed replies and the time limit
may prevent collection. `discussion_status=partial` explicitly marks a bounded
discussion; the collector does not sign in or purchase platform API access.
One page is counted as one source, even when it contains multiple replies.

## Setup

Use the repository's local activation script first. Install the research
dependencies into the existing backend environment:

```sh
source .codex-local/activate.sh
uv --no-config pip install --python backend/.venv/bin/python -r backend/requirements-research.txt
backend/.venv/bin/python -m playwright install chromium
```

Docker installs the same dependencies and Chromium with Linux dependencies.
They are layered over the existing simulation lock to avoid changing the
OASIS/Torch environment. No migration of the Neo4j database is needed.

## German egress

Main Pitchy's `search_agent.py` uses a scoped HTTP CONNECT proxy. Set
`SEARCH_HTTPS_PROXY` or `EXA_HTTPS_PROXY` to the same value in the server env.
Exa honors `EXA_HTTPS_PROXY`; other search providers use `SEARCH_HTTPS_PROXY`
(falling back to `EXA_HTTPS_PROXY`). Page loading uses `SIGNAL_HTTPS_PROXY`,
falling back to the search proxy. It first tries direct access, then retries
through the proxy on network errors, access blocks or missing content.
Chromium receives equivalent proxy settings at the browser-context level.
SSO, billing and LLM calls do not inherit this scoped setting.

The production deployment copies the search proxy from
`/opt/ai-startup/.env.runtime` when CustDev has no dedicated proxy setting.
Actual values are deployment secrets and are never written to tracked files
or printed by the collector. Staging can set the same env variables directly.

## Limits and diagnostics

| Variable | Default | Purpose |
| --- | --- | --- |
| `SIGNAL_RESEARCH_SECONDS` | 170 | Overall research wall-time budget, maximum 180 |
| `SIGNAL_CRAWL_SECONDS` | 75 | Maximum collection subprocess time |
| `SIGNAL_MAX_PAGES` | 48 | Maximum discovered pages attempted per job |
| `SIGNAL_MAX_COMMENTS` | 20 | Maximum visible comments/replies per page |
| `SIGNAL_BROWSER_ENABLED` | 1 | Enable public JavaScript page rendering |

At the deadline, completed pages are retained and Chromium is stopped.
`discovered_sources` includes unread pages with `crawl_status` such as
`blocked`, `timed_out`, `request_failed` or `not_attempted`. Verified sources
appear in `sources`; `unread_sources_count`, `comments_count` and the separate
Russian/international counts describe coverage. A missing proxy is not silently
treated as a successful retry.

Local live checks found links on Habr, Reddit and X; Habr article extraction
succeeded. Direct X access returned HTTP 403 and Reddit was not collected in
the allotted time. The local clone has no German proxy value, so a live
German-egress check is still required in the configured server environment.
