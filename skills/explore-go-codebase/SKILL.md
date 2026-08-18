---
name: explore-go-codebase
description: Rapidly analyze an unfamiliar Go repository and produce an evidence-backed codebase guide covering purpose, architecture, entry points, packages, dependencies, domain concepts, call chains, runtime sequences, business/data/error flows, concurrency, persistence, integrations, configuration, and risks. Use when onboarding to, explaining, auditing, documenting, or planning changes in a Golang codebase, especially when the result needs accurate Mermaid call graphs, sequence diagrams, or flowcharts linked to source files.
---

# Explore Go Codebase

Build a concise, navigable model of a Go repository. Treat source code and generated tool output as evidence; label inference and uncertainty instead of presenting guesses as facts.

## Workflow

### 1. Establish scope

- Locate the repository root, `go.mod`/`go.work`, user-facing binaries, services, workers, libraries, and existing architecture documents.
- Preserve existing files unless the user asks for documentation to be written into the repository.
- Decide the output location. Default to `CODEBASE_GUIDE.md` at the analyzed repository root when a durable guide is requested; otherwise answer in chat.
- Copy `assets/codebase-guide.template.md` when creating a durable guide, then remove sections that do not apply.

### 2. Build a structural inventory

Run the bundled scanner first:

```bash
python3 <skill-dir>/scripts/scan_go_repository.py <repo-root> --output /tmp/go-codebase-inventory.md
```

Read the inventory, then inspect `go.mod`, `go.work`, entry points, configuration, API/schema definitions, migrations, generated-code markers, and tests. Use `rg` for targeted discovery. Read [references/analysis-playbook.md](references/analysis-playbook.md) before tracing a large, layered, concurrent, or framework-heavy repository.

The scanner is a discovery aid, not a call-graph authority. Verify every important edge in source.

### 3. Identify the main capabilities

- Derive capabilities from externally visible behavior: commands, routes, RPC methods, consumers, scheduled jobs, exported library APIs, and tests.
- Map each capability to its entry point, orchestration layer, domain logic, state changes, and external effects.
- Prefer 3–7 high-value flows. Rank by user impact, centrality, and operational risk.
- Create a small glossary when names carry domain meaning.

### 4. Trace calls and state

For each selected flow:

1. Start at a concrete trigger.
2. Follow direct calls and dependency construction through interfaces to candidate implementations.
3. Track inputs, validation, state mutation, persistence, network calls, emitted events, error translation, retries, and cancellation.
4. Check tests to confirm intended behavior and edge cases.
5. Record evidence as `relative/path.go:Lx-Ly` while working; refresh line numbers before delivery.

Stop a trace where it reaches standard library/framework plumbing or leaves the repository. Name the boundary. Mark reflection, code generation, dependency injection, callbacks, interface dispatch, and goroutine handoffs when the target cannot be proven statically.

### 5. Draw only useful diagrams

Read [references/diagram-guide.md](references/diagram-guide.md). Use:

- A flowchart for system boundaries, decisions, state transitions, or data movement.
- A sequence diagram for time-ordered collaboration across components.
- A call graph for one bounded request/job path, not the whole repository.
- A state diagram only when the domain has explicit lifecycle states.

Keep diagrams readable and back every node and edge with inspected source. Accompany each diagram with entry conditions, outcome, important failure behavior, and evidence links.

### 6. Synthesize and quality-check

Deliver the guide in this order:

1. Executive summary and scope
2. How to run/test and primary entry points
3. Architecture and package responsibilities
4. Main capabilities
5. Critical call chains and sequence diagrams
6. Business, data, error, and concurrency flows
7. Configuration, persistence, and integrations
8. Testing strategy and extension points
9. Risks, uncertainties, and suggested next reading

Before delivery, verify:

- Every major claim cites a source file, symbol, configuration, schema, or test.
- Diagram arrows represent real calls, messages, or state transitions.
- Interface-to-implementation choices are proven or explicitly marked as candidates.
- Happy paths and important failure/cancellation paths are both covered.
- Generated/vendor code is distinguished from owned code.
- No secrets or credential values are copied into the guide.
- The overview is useful without reading every diagram.

## Resource routing

- Read `references/analysis-playbook.md` for investigation order, framework heuristics, evidence rules, and difficult Go constructs.
- Read `references/diagram-guide.md` before producing Mermaid diagrams.
- Use `assets/codebase-guide.template.md` as the report skeleton.
- Run `scripts/scan_go_repository.py --help` for scanner options and JSON output.
