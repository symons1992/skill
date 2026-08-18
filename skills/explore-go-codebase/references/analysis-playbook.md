# Go codebase analysis playbook

## Contents

- Investigation order
- Evidence and confidence
- Repository shapes
- Entry-point discovery
- Call-chain resolution
- Runtime and data behavior
- Validation strategy

## Investigation order

Start broad, then narrow:

1. Read `go.work`, `go.mod`, top-level directories, build files, deployment manifests, and existing docs.
2. Find binaries under `cmd/` and all `package main` files.
3. Find inbound adapters: HTTP routes, RPC registrations, CLI commands, message consumers, schedulers, and exported library APIs.
4. Find composition roots: constructors, dependency injection, server setup, and lifecycle hooks.
5. Build a complete inbound-interface coverage ledger before deep tracing.
6. Trace every inbound interface into domain/service code, repositories, clients, and emitted events. Prioritize high-risk interfaces first, but do not stop after a representative subset.
7. Read tests alongside implementation. Tests often reveal contracts, intended failures, and fake-to-interface mappings.
8. Inspect schemas, migrations, protobuf/OpenAPI files, and configuration for behavior not obvious from Go code.

Avoid reading files sequentially. Use symbols and call sites to form hypotheses, then verify them.

## Evidence and confidence

Classify findings internally:

- **Confirmed**: a direct source edge, registration, constructor wiring, schema, or executable test proves it.
- **Corroborated**: multiple independent clues agree, but runtime selection remains possible.
- **Inferred**: naming or structure suggests it; state the assumption and how to verify it.
- **Unknown**: dynamic behavior, missing dependency source, build tags, or environment prevents resolution.

Final prose should cite confirmed evidence and plainly label the other categories. A diagram may use solid arrows for confirmed calls/messages and dashed arrows for inferred or environment-dependent edges; include a legend if both appear.

Use repository-relative paths in the document so it remains portable. Cite the smallest useful range and include the symbol name in prose. Refresh line numbers after edits.

## Repository shapes

Recognize common layouts without assuming their semantics:

- `cmd/<name>` commonly contains a binary composition root.
- `internal/` enforces module-private imports; its subdirectories may still mix layers.
- `pkg/` is a convention, not proof of a public API.
- `api/`, `proto/`, `openapi/`, or `graphql/` often define transport contracts.
- `migrations/`, `queries/`, and generated ORM code reveal persistence behavior.
- `deploy/`, `charts/`, `terraform/`, and container files reveal runtime topology.

For multi-module workspaces, map module boundaries before package boundaries. Note `replace` directives because they can redirect important dependencies to local code.

## Entry-point discovery

Search for concrete registration rather than framework names alone:

```text
package main
http.HandleFunc|Handle|Methods|ServeHTTP
grpc.Register|Register.*Server
cobra.Command|AddCommand|RunE
Consume|Subscribe|Handler|Worker|Cron|Schedule
fx.Provide|fx.Invoke|wire.Build|dig.In
TestMain|httptest|bufconn
```

Also inspect generated registrations and build-tag variants. Record how startup, readiness, shutdown, signals, and background goroutines are coordinated.

For access-layer repositories, discover interfaces from both registration code and declared contracts. Resolve router groups and prefixes into the final external identity. Reconcile both lists so contract-only and implementation-only endpoints remain visible.

## Call-chain resolution

Trace each inbound interface using this record:

```text
trigger -> adapter -> use case/service -> domain operation -> repository/client -> effect
```

Expand the record to include shared and route-specific middleware, request binding, validation, identity/policy checks, response mapping, and serialization. Preserve actual runtime order.

For every edge, locate the call expression and the receiver/value construction. For interface calls:

1. Find the interface declaration.
2. Find implementations by method set and compile-time assertions.
3. Find constructor or dependency-injection wiring at the composition root.
4. If multiple implementations remain possible, list the selection condition or mark candidates.

Treat these carefully:

- Embedded methods may promote behavior from another type.
- Function fields and callbacks move the next edge into construction code.
- Generic functions require tracing type arguments and passed constraints.
- Reflection and plugin lookup may make static resolution impossible.
- Generated mocks prove an interface shape, not the production implementation.
- Build tags and platform suffixes can change the active graph.
- A `go` statement creates an asynchronous boundary; trace ownership, cancellation, and error reporting separately.
- Channels imply send/receive relationships, not ordinary function calls.

Use `gopls` references/call hierarchy or a static-analysis tool when available, but confirm high-value results in source and note tool limitations. Do not install tools merely to decorate the report.

## Runtime and data behavior

For each critical flow, answer:

- What validates and normalizes input?
- What identity, authorization, tenant, locale, deadline, or trace data travels in `context.Context`?
- What state is read or mutated, within which transaction?
- Which operations are idempotent, retried, cached, batched, or eventually consistent?
- What leaves the process: SQL, RPC, HTTP, queues, files, metrics, logs, or events?
- How are errors wrapped, classified, translated, logged, and exposed?
- Who owns goroutines, channels, locks, timers, and shutdown?

Never infer database table relationships only from struct names. Confirm with queries, ORM mappings, migrations, or schemas. Never copy secret values from environment files or configuration.

## Validation strategy

Use the cheapest meaningful checks:

- `go list ./...` validates package discovery.
- `go test ./...` validates behavior when practical.
- Focused tests validate the selected flow faster than an entire slow suite.
- `go vet ./...` can expose suspicious constructs but is not required for understanding.
- Build/test failures are findings: record whether they result from missing services, build tags, generated files, private modules, or actual code errors.

Cross-check every interface against registration and implementation evidence, then against at least one of tests, schema/configuration, or runtime documentation when available. If sources disagree, report the disagreement instead of silently choosing one.

Finish with an explicit count reconciliation: `discovered = traced + partial + unresolved`. A partial or unresolved interface is a reportable finding, not a reason to omit the row.
