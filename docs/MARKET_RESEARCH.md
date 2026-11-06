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
   scrapy-playwright, or the official API when `X_API_BEARER_TOKEN` is set.
   Other sites use article selectors, visible comments and
   JSON-LD, with browser rendering for empty pages and dynamic discussions.
4. Results preserve text, excerpts, comment links, dates when available,
   collection status and egress. Only successfully fetched pages enter the
   evidence set. Search snippets and block pages do not count as demand.
5. The Polza `signals` model synthesizes Russian evidence and foreign experience
   separately. The same distinction is passed to the final verdict model.
   New demand counts derive from distinct cited Russian source indices, not
   the model's proposed totals. Invalid, duplicate and foreign citations are
   discarded. Legacy saved results retain compatibility.

Public access does not guarantee complete discussions. Login walls, removed
posts, rate limits, collapsed replies and the time limit
may prevent collection. `discussion_status=partial` explicitly marks a bounded
discussion; the collector does not sign in or purchase platform API access.
An explicitly configured X API token enables authorized read-only API requests.
One page is counted as one source, even when it contains multiple replies.
X timeline neighbors are excluded from replies unless public parent metadata
connects them to the selected post. Login screens are not Reddit evidence.
Browser retries merge collected replies and preserve the longer article.

## Setup

Use the repository's local activation script first. Install the research
dependencies into the existing backend environment:

```sh
source .codex-local/activate.sh
uv --no-config pip install --python backend/.venv/bin/python -r backend/requirements-research.txt
backend/.venv/bin/python -m playwright install chromium
```

Docker installs the same dependencies and the Chromium headless shell with
Linux dependencies in a layer preceding application source. Routine source
changes reuse this layer; only changes to its dependencies require a download.
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
When the main application runs on a different host, the repository secret
`SEARCH_HTTPS_PROXY` provides that same setting. It also reaches the browser
installer through a BuildKit secret, so slow regional CDN access does not
block deployment and proxy credentials do not enter image layers.
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
| `X_API_BEARER_TOKEN` | empty | Optional official X API credentials; secret, never log |
| `X_API_MAX_POSTS` | 3 | Paid discovered posts per collector job, maximum 10 |
| `X_API_MAX_REPLIES` | 10 | Replies retained per post, 0 disables reply requests |

With X API enabled, Scrapy batches discovered post IDs in one lookup and
reads at most one full-archive reply-search page per selected post. Each search
requests exactly 10 results (the API minimum), even if fewer replies are retained.
The search starts at the selected post's publication date so older discussions
are included. Posts whose API metrics report zero replies skip the reply call.
No pagination, user expansions or automatic paid retries run. The default
maximum is 3 parent posts plus 30 returned replies per collector job, not a
global account spending cap. Set the billing-cycle cap in the X console too.
The configured German proxy is used immediately for X API requests. Authorization
headers only go to fixed `api.x.com` endpoints; redirects are disabled.
Search providers remain responsible for discovery. Sources beyond the paid cap
are marked `budget_limited`; inaccessible or deleted API posts are not evidence.
Reply-access failure preserves a successfully read parent post and records
`discussion_http_status`. Threads are always marked partial, not complete.

Production takes `X_API_BEARER_TOKEN` from the same-named GitHub Actions secret
and writes it into the container runtime env; `.env` is excluded from the image.

At the deadline, completed pages are retained and Chromium is stopped.
`discovered_sources` includes unread pages with `crawl_status` such as
`blocked`, `timed_out`, `request_failed` or `not_attempted`. Verified sources
appear in `sources`; `unread_sources_count`, `comments_count` and the separate
Russian/international counts describe coverage. A missing proxy is not silently
treated as a successful retry.
`discovered_sources` contains compact diagnostics; full text and comments live
only in `sources`. `search_status` distinguishes an unavailable search provider
from a successful search with no matches. Research creation accepts an optional
owner-scoped `request_id`; retries with the same ID reuse the task. The browser
polls serially and discards responses belonging to a previous run or page.

The manual check script reports `verification_status=passed|partial|failed`.
Exit codes are 0/2/1 respectively. Habr alone cannot pass a Reddit/X check, and
full verification also requires an available synthesis result.

Local live checks found links on Habr, Reddit and X; Habr article extraction
succeeded. Direct X access returned HTTP 403 and Reddit was not collected in
the allotted time. The local clone has no German proxy value, so a live
German-egress check is still required in the configured server environment.
