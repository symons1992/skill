# Offline interactive HTML output

## Contents

- Delivery contract
- Report structure
- Data preparation
- Rendering
- Interaction and visual QA
- Security checks

## Delivery contract

Deliver one self-contained `CODEBASE_GUIDE.html` file that works when opened directly from disk. The report must not require npm, a build step, an internet connection, or a running service.

Never:

- publish or deploy the report;
- upload it to a gist, paste service, artifact host, cloud drive, or public repository;
- load CDN assets, remote fonts, remote images, analytics, iframes, or remote source maps;
- call `fetch`, `XMLHttpRequest`, WebSocket, EventSource, or service workers;
- embed credentials, secret configuration values, private keys, tokens, cookies, or production payloads.

The bundled renderer escapes repository-derived content and uses DOM text nodes for display. Keep that safety property when modifying the template.

## Report structure

The HTML must make both breadth and depth easy to inspect:

1. Summary, scope, revision, confidence, and coverage counts
2. Run/test/entry-point notes
3. Architecture and package responsibilities
4. Searchable interface index with protocol and status filters
5. One expandable detail card per discovered interface
6. Shared middleware/interceptor chains
7. Configuration, persistence, external integrations, concurrency, and lifecycle
8. Tests, risks, unknowns, and suggested reading order

Each interface card must show:

- external identity and trace status;
- request and response contract;
- ordered request chain with concrete behavior and evidence;
- branches and error translation;
- state changes, external calls, and async effects;
- context/transaction/retry/timeout/cancellation behavior;
- relevant tests and unresolved gaps.

## Data preparation

Start from `assets/codebase-guide.data.example.json`. Keep repository-relative evidence paths so the report remains portable.

Use concise strings and arrays rather than HTML fragments. Do not place markup in the data. Use one `interfaces[]` entry for each coverage-ledger row, including partial and unresolved rows.

Required interface fields are:

```text
id, protocol, external, title, status, registration, handler,
request, response, steps, branches, errors, effects, tests, unresolved
```

For a `traced` interface, `steps` must be non-empty and every step must contain evidence. For `partial` and `unresolved`, explain the gap in `unresolved`.

## Rendering

Render and validate:

```bash
python3 <skill-dir>/scripts/render_codebase_guide.py \
  --input /tmp/codebase-guide.data.json \
  --output <repo-root>/CODEBASE_GUIDE.html

python3 <skill-dir>/scripts/render_codebase_guide.py \
  --input /tmp/codebase-guide.data.json \
  --check
```

The renderer validates IDs, statuses, required fields, traced-step evidence, shared-chain references, and the absence of remote URLs in data. It derives coverage counts rather than trusting manually entered totals.

## Interaction and visual QA

Open the final file locally and verify:

- free-text search matches external identities, handlers, behavior, and evidence;
- protocol and trace-status filters work together;
- sidebar links navigate to the correct interface;
- expand/collapse controls preserve readable focus and hash navigation;
- long symbols and paths wrap instead of overflowing;
- narrow viewport layout remains usable;
- print/PDF mode expands content and hides controls;
- the report remains understandable when JavaScript is disabled enough to show a clear requirement notice.

If browser automation is unavailable, inspect the file and run at least the renderer checks. Never use a public preview service for QA.

## Security checks

Before delivery:

1. Search the HTML for `http://`, `https://`, protocol-relative URLs, remote imports, and network APIs.
2. Search for known credential variable names and redact values.
3. Confirm all source evidence is repository-relative.
4. Confirm the HTML opens with network disabled.
5. State that the report was created locally and was not published.
