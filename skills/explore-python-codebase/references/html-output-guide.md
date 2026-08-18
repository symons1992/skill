# Offline interactive HTML output

## Contents

- Delivery contract
- Report structure
- Data preparation
- Rendering
- Interaction and visual QA
- Security checks

## Delivery contract

Deliver one self-contained `CODEBASE_GUIDE.html` file that opens directly from disk. Require no npm, build step, internet connection, or running service.

Never publish or upload the report; load remote scripts, styles, fonts, images, analytics, frames, or maps; call network APIs; or embed credentials, secret settings, cookies, private keys, tokens, or production payloads.

The bundled renderer escapes repository-derived content and the template displays it through DOM text nodes. Preserve that property when modifying either resource.

## Report structure

Make breadth and depth easy to inspect:

1. Summary, scope, revision, confidence, and coverage counts
2. Run/test/entry-point notes
3. Architecture and package/module responsibilities
4. Searchable interface index with protocol and status filters
5. One expandable detail card per discovered interface
6. Shared middleware/dependency/decorator/task chains
7. Configuration, persistence, integrations, async/concurrency, and lifecycle
8. Tests, risks, unknowns, and suggested reading order

For each interface show its external identity, trace status, input/output contract, ordered chain, branches and exception mapping, state/external/async effects, context/transaction/retry/timeout/cancellation behavior, tests, evidence, and gaps.

## Data preparation

Start from `assets/codebase-guide.data.example.json`. Keep evidence paths repository-relative. Store concise plain strings and arrays, never HTML fragments. Add one `interfaces[]` entry per coverage-ledger row, including partial and unresolved entries.

Required interface fields:

```text
id, protocol, external, title, status, registration, handler,
request, response, steps, branches, errors, effects, tests, unresolved
```

Require non-empty `steps` and evidence for a `traced` interface. Explain every `partial` or `unresolved` gap with a verification action.

## Rendering

```bash
python3 <skill-dir>/scripts/render_codebase_guide.py \
  --input /tmp/codebase-guide.data.json \
  --output <repo-root>/CODEBASE_GUIDE.html

python3 <skill-dir>/scripts/render_codebase_guide.py \
  --input /tmp/codebase-guide.data.json \
  --check
```

The renderer validates IDs, statuses, required fields, traced-step evidence, shared-chain references, relative evidence, secret-like values, and remote URLs. It derives coverage counts rather than trusting totals in the data.

## Interaction and visual QA

Open the final file locally and verify search; combined protocol/status filters; sidebar navigation; expand/collapse and hash navigation; path wrapping; narrow viewports; print layout; and the disabled-JavaScript notice.

If browser automation is unavailable, inspect the rendered file and run at least the renderer checks. Never use a public preview service.

## Security checks

1. Search the HTML for remote/protocol-relative URLs, remote imports, and network APIs.
2. Search for credential-shaped values and known secret variable names; redact values while retaining useful key names.
3. Confirm all evidence paths are repository-relative.
4. Confirm the report opens with networking disabled.
5. State that the report was created locally and was not published.
