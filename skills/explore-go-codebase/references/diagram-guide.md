# Offline report visualization guide

## Contents

- General rules
- Architecture view
- Per-interface request chain
- Runtime sequence
- Decisions and data flow
- Accuracy and offline checks

## General rules

- Choose one question per visual and state it in the title.
- Prefer native HTML and CSS already provided by the report template.
- Use inline SVG only when a relationship cannot be understood as clearly from the step chain or a table.
- Never use Mermaid, a CDN, remote fonts, remote icons, remote images, canvas libraries, or runtime network requests in the delivered HTML.
- Keep source paths out of visual labels; place evidence next to the relevant step.
- Back every node and edge with inspected source.

## Architecture view

Use a small component table or inline SVG for system boundaries and dependency direction. Keep it to the repository-owned components and immediate external systems needed to orient a reader.

Do not label a dependency diagram as a runtime request chain unless every edge is invoked in that order. The per-interface chain remains authoritative.

## Per-interface request chain

Use the report's ordered step rail for every interface. Each step needs:

- ordinal and stage;
- concrete symbol;
- behavior in plain language;
- input and output;
- state or external effect;
- source evidence and confidence.

Show shared-chain references at the exact point they execute. Expand route-specific overrides instead of hiding them in the shared description.

## Runtime sequence

Use an ordered sequence table when timing, transactions, or asynchronous handoffs matter. Include caller/component, operation, synchronous or asynchronous mode, result, and evidence.

Represent enqueue and later consumption as separate events. Do not imply the producer waits for consumer completion. Show transaction start/commit/rollback and retry loops only when code proves them.

## Decisions and data flow

Use branch and error tables for validation, policy decisions, retry, fallback, and transformations. Record the actual condition, resulting call or state change, external outcome, and evidence.

Do not collapse failure modes that map to different status codes, RPC codes, retry behavior, or operational signals.

## Accuracy and offline checks

- Does every edge have a source call, registration, message operation, or state update?
- Is sync versus async behavior explicit?
- Are transaction, process, timeout, retry, and cancellation boundaries visible?
- Are optional, build-specific, or dynamically selected edges marked?
- Can a reader find evidence for every step without inspecting a separate diagram legend?
- Does the final HTML render with networking disabled and contain no external resource URLs?
