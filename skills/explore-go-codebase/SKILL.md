---
name: explore-go-codebase
description: Exhaustively analyze an unfamiliar Go repository and produce a self-contained, offline interactive HTML guide covering every inbound interface and its complete request chain, plus architecture, packages, dependencies, domain concepts, data/error/concurrency flows, persistence, integrations, configuration, tests, and risks. Use when onboarding to, explaining, auditing, documenting, or planning changes in a Golang codebase, especially API gateways, BFFs, edge services, protocol adapters, and other access-layer repositories where route-by-route or RPC-by-RPC traceability is required.
---

# Explore Go Codebase

Build an evidence-backed model of a Go repository. For access-layer code, treat complete inbound-interface coverage as the primary deliverable rather than sampling a few representative flows.

## Workflow

### 1. Establish scope and output invariants

- Locate the repository root, `go.mod`/`go.work`, binaries, services, workers, libraries, generated contracts, and existing architecture documents.
- Preserve existing files unless the user asks for repository documentation.
- Produce `<repo-root>/CODEBASE_GUIDE.html` by default. The result must be a self-contained local file that opens through `file://` without a build step.
- Never publish, deploy, upload, or expose the report through a public URL. Do not use remote scripts, styles, fonts, images, analytics, or network requests. If a local server is strictly necessary for testing, bind only to `127.0.0.1` and do not treat it as delivery.
- Never copy secret values, credentials, tokens, private keys, or sensitive request examples into the report.

### 2. Build the structural inventory

Run the bundled scanner first:

```bash
python3 <skill-dir>/scripts/scan_go_repository.py <repo-root> --output /tmp/go-codebase-inventory.md
```

Read the inventory, then inspect `go.mod`, `go.work`, entry points, configuration, API/schema definitions, migrations, generated-code markers, and tests. Use `rg` for targeted discovery. Read [references/analysis-playbook.md](references/analysis-playbook.md) before tracing a large, layered, concurrent, or framework-heavy repository.

Treat scanner output as discovery evidence, not an authoritative call graph. Verify every important edge in source.

### 3. Enumerate every inbound interface

Read [references/interface-tracing.md](references/interface-tracing.md) and create a coverage ledger before deep tracing.

- Enumerate every HTTP route, RPC method, GraphQL operation/resolver, WebSocket entry, message consumer, scheduled trigger, CLI command, and exported library entry that can initiate application behavior.
- Resolve routes assembled through groups, prefixes, generated registration, embedded routers, build tags, and versioned modules.
- Give every discovered interface a stable ID and record its registration evidence, transport contract, handler, and trace status.
- Do not reduce the scope to a representative subset. Shared middleware or service segments may be documented once and referenced, but every interface must have its own contract, chain, outcomes, and evidence.
- Reconcile implementation registrations with OpenAPI/protobuf/GraphQL schemas and report orphaned or undocumented interfaces in both directions.

### 4. Trace each interface end to end

For every ledger row, trace:

```text
trigger/registration
  -> routing and middleware
  -> decode/bind/normalize/validate
  -> authentication/authorization/tenant/context
  -> handler/controller
  -> application/domain services
  -> repositories, caches, queues, and outbound clients
  -> transaction/side effects
  -> error translation and response serialization
```

Follow interface dispatch through constructors and dependency injection to the production implementation. Record request and response fields, context propagation, branches, state changes, external effects, retries, timeouts, cancellation, idempotency, and tests. Cite the call expression or wiring evidence for every step.

Stop only at a verified repository or process boundary. Mark dynamic, generated, reflection-based, build-specific, or unresolved edges explicitly; never fill gaps with plausible guesses.

### 5. Model shared behavior and system context

- Document shared middleware, interceptors, adapters, error mappers, transactions, and client wrappers once, then link each affected interface to the shared chain.
- Explain startup, readiness, shutdown, goroutine ownership, channels, locks, and background work.
- Map packages, configuration, persistence, external systems, test seams, and extension points.
- Use architecture views only when they improve navigation. For request behavior, the per-interface step chain and branch/error tables are authoritative.

### 6. Generate the offline interactive report

Read [references/html-output-guide.md](references/html-output-guide.md).

1. Copy `assets/codebase-guide.data.example.json` to a temporary working file and replace the example data with verified findings.
2. Include one `interfaces[]` record for every row in the coverage ledger; do not omit unresolved interfaces.
3. Render the report:

```bash
python3 <skill-dir>/scripts/render_codebase_guide.py \
  --input /tmp/codebase-guide.data.json \
  --output <repo-root>/CODEBASE_GUIDE.html
```

4. Run the renderer again with `--check` against the final data, open the HTML locally, and verify search, filters, navigation, expand/collapse, and print layout.
5. Deliver the HTML file path and a concise coverage summary. Do not publish it.

### 7. Quality gate

Before delivery, verify all of the following:

- Discovered interface count equals `traced + partial + unresolved`; every interface appears in the HTML.
- Every traced interface has registration, request/response contract, ordered steps, important branches, error mapping, side effects, tests, and source evidence.
- Every major claim cites a source file, symbol, configuration, schema, or test.
- Interface-to-implementation choices are proven or explicitly marked as candidates.
- Shared-chain references identify the exact middleware/interceptor steps they replace.
- Sync/async, transaction, retry, timeout, cancellation, and process boundaries are represented truthfully.
- Generated/vendor code is distinguished from owned code.
- The HTML has no external resource or network dependency and contains no secret values.
- Unknowns remain visible and include a concrete verification path.

## Resource routing

- Read `references/interface-tracing.md` for the exhaustive ledger, per-interface schema, and chain-resolution rules.
- Read `references/analysis-playbook.md` for investigation order, framework heuristics, evidence rules, and difficult Go constructs.
- Read `references/diagram-guide.md` before adding architecture or sequence visuals to the offline report.
- Read `references/html-output-guide.md` for the local-only HTML contract and QA procedure.
- Use `assets/codebase-guide.data.example.json` as the report-data skeleton.
- Use `scripts/render_codebase_guide.py` to validate data and create the self-contained HTML.
- Run `scripts/scan_go_repository.py --help` for scanner options and JSON inventory output.
