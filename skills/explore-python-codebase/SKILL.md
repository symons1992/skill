---
name: explore-python-codebase
description: Exhaustively analyze an unfamiliar Python repository and produce a self-contained, offline interactive HTML guide covering every inbound interface and its complete execution chain, plus architecture, packages, dependencies, domain concepts, data/error/async flows, persistence, integrations, configuration, tests, and risks. Use when onboarding to, explaining, auditing, documenting, or planning changes in a Python codebase, especially FastAPI, Django, Flask, Starlette, aiohttp, gRPC, GraphQL, Celery, CLI, serverless, data-service, and other access-layer repositories where route-by-route, task-by-task, command-by-command, or handler-by-handler traceability is required.
---

# Explore Python Codebase

Build an evidence-backed model of a Python repository. Treat complete externally invocable interface coverage as the primary deliverable for access-layer code; do not stop at representative flows.

## Workflow

### 1. Establish scope and output invariants

- Locate the repository root, Python project/workspace files, source roots, applications, workers, libraries, generated contracts, and existing architecture documents.
- Detect supported Python versions, packaging tools, dependency groups, framework versions, and runtime entry points from project metadata and lock files.
- Preserve existing files unless the user asks for repository documentation.
- Produce `<repo-root>/CODEBASE_GUIDE.html` by default. Make it a self-contained local file that opens through `file://` without a build step.
- Never publish, deploy, upload, or expose the report through a public URL. Do not use remote scripts, styles, fonts, images, analytics, or network requests. If local serving is strictly necessary for testing, bind only to `127.0.0.1` and do not treat it as delivery.
- Never copy secret values, credentials, tokens, private keys, cookies, sensitive settings, or production payloads into the report.

### 2. Build the structural inventory

Run the bundled scanner first:

```bash
python3 <skill-dir>/scripts/scan_python_repository.py <repo-root> --output /tmp/python-codebase-inventory.md
```

Read the inventory, then inspect `pyproject.toml`, setup/requirements/lock files, source roots, framework configuration, entry points, API/schema definitions, migrations, generated-code markers, and tests. Use `rg` for targeted discovery. Read [references/analysis-playbook.md](references/analysis-playbook.md) before tracing a large, layered, async, plugin-heavy, or framework-heavy repository.

Treat scanner output as discovery evidence, not an authoritative call graph. It uses syntax-tree and text heuristics; verify every important edge and final external identity in source and configuration.

### 3. Enumerate every inbound interface

Read [references/interface-tracing.md](references/interface-tracing.md) and create a coverage ledger before deep tracing.

- Enumerate every HTTP route, RPC method, GraphQL operation/resolver, WebSocket/SSE handler, webhook, message consumer, scheduled task, workflow/job, serverless handler, CLI command, management command, and intentionally public library entry that can initiate repository-owned behavior.
- Resolve decorators, router prefixes, mounted applications, Django URL includes, blueprints, generated registrations, configuration-selected apps, entry-point plugins, and environment-specific modules.
- Give every discovered interface a stable ID and record registration evidence, transport contract, handler, runtime selection, and trace status.
- Do not reduce the scope to a representative subset. Document shared middleware, dependencies, signals, or service segments once and reference them, but retain a distinct record for every interface.
- Reconcile implementation registrations with OpenAPI/protobuf/GraphQL/event schemas, packaging entry points, deployment manifests, and tests. Report orphaned or undocumented interfaces in both directions.

### 4. Trace each interface end to end

For every ledger row, trace the applicable stages in actual runtime order:

```text
trigger/registration
  -> application/router/middleware/dependencies
  -> decode/parse/normalize/validate
  -> authentication/authorization/tenant/request context
  -> view/handler/resolver/task/command
  -> application/domain services
  -> repositories, ORM/unit of work, caches, queues, and outbound clients
  -> transaction/side effects/async handoff
  -> exception translation and response/result serialization
```

Follow calls through imports, re-exports, factories, decorators, descriptors, dependency injection, framework settings, and production wiring. Record contracts, context propagation, branches, state changes, external effects, retries, timeouts, cancellation, idempotency, transaction scope, and tests. Cite the call expression, decorator, setting, URL composition, or wiring evidence for every step.

Stop only at a verified repository or process boundary. Mark dynamic imports, monkey patching, metaclass/descriptor behavior, generated code, framework magic, plugins, settings-dependent selection, or unresolved dispatch explicitly; never fill gaps with plausible guesses.

### 5. Model shared behavior and system context

- Document shared middleware, decorators, FastAPI dependencies, Django mixins/signals, exception handlers, serializers, ORM/session/unit-of-work boundaries, task wrappers, and client adapters once; link every affected interface to the exact shared chain.
- Explain import-time initialization, application startup/lifespan, readiness, shutdown, signal handling, event loops, tasks/futures, thread/process ownership, queues, locks, and background work.
- Map packages/modules, configuration layers, persistence, external systems, test seams, extension points, generated code, and namespace-package boundaries.
- Use architecture views only when they improve navigation. Treat the per-interface ordered chain and branch/error tables as authoritative for behavior.

### 6. Generate the offline interactive report

Read [references/html-output-guide.md](references/html-output-guide.md).

1. Copy `assets/codebase-guide.data.example.json` to a temporary working file and replace its example data with verified findings.
2. Include one `interfaces[]` record for every coverage-ledger row, including partial and unresolved interfaces.
3. Render the report:

```bash
python3 <skill-dir>/scripts/render_codebase_guide.py \
  --input /tmp/codebase-guide.data.json \
  --output <repo-root>/CODEBASE_GUIDE.html
```

4. Run the renderer with `--check`, open the final HTML locally, and verify search, filters, navigation, expand/collapse, narrow layout, and print layout.
5. Deliver the HTML file path and a concise coverage summary. Do not publish it.

### 7. Quality gate

- Reconcile `discovered = traced + partial + unresolved`; include every ledger row in the HTML.
- Give every traced interface registration, contract, ordered steps, important branches, exception/error mapping, side effects, tests, and source evidence.
- Cite a repository-relative source file, symbol, setting, schema, migration, or test for every major claim.
- Prove import aliases, re-exports, decorators, dependency providers, protocol/ABC calls, and runtime implementation choices or label them as candidates.
- Reference exact middleware/dependency/decorator steps from shared chains.
- Represent sync/async, event-loop/thread/process, transaction, retry, timeout, cancellation, queue, and process boundaries truthfully.
- Distinguish generated, vendored, migration, test, and owned runtime code.
- Keep the HTML free of external resources, network dependencies, and secret values.
- Keep unknowns visible with a concrete verification path.

## Resource routing

- Read `references/interface-tracing.md` for the exhaustive ledger, framework discovery rules, per-interface schema, and chain-resolution procedure.
- Read `references/analysis-playbook.md` for investigation order, packaging/framework heuristics, Python dispatch rules, evidence standards, and validation strategy.
- Read `references/diagram-guide.md` before adding architecture or sequence visuals.
- Read `references/html-output-guide.md` for the local-only report contract and QA procedure.
- Use `assets/codebase-guide.data.example.json` as the report-data skeleton.
- Use `scripts/render_codebase_guide.py` to validate report data and create the self-contained HTML.
- Run `scripts/scan_python_repository.py --help` for scanner options and JSON inventory output.
