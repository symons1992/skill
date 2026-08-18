# Exhaustive inbound-interface tracing

## Contents

- Coverage contract
- Interface discovery
- Coverage ledger
- Per-interface record
- End-to-end trace procedure
- Shared chains
- Reconciliation and completion

## Coverage contract

Treat an inbound interface as any externally invocable trigger that can start repository-owned behavior. In access-layer repositories, completeness is more valuable than selecting only prominent flows.

Include:

- HTTP routes, including health/admin/debug routes when repository-owned
- gRPC, Connect, Twirp, Thrift, and other RPC methods
- GraphQL operations and resolvers
- WebSocket/SSE connection and message handlers
- queue/topic consumers and webhook receivers
- scheduled jobs and CLI commands
- exported library functions intentionally used as application entry points

Exclude framework internals and generated glue only after linking them to the owned registration or implementation. Keep generated contract evidence when it defines the external surface.

## Interface discovery

Search registrations and contracts from independent directions:

1. Start at server/router construction and registration calls.
2. Inspect OpenAPI, protobuf, GraphQL, IDL, gateway, and generated route files.
3. Search handler/controller/resolver method sets and framework annotations.
4. Inspect tests that invoke routes, methods, commands, or consumers.
5. Resolve group prefixes, mounted subrouters, versioning, build tags, and environment-specific registrations.
6. Compare all lists. Report implementation-only and contract-only entries.

Framework registrations can be indirect. Trace values passed into route groups, generated `Register*Server` functions, method expressions, callback fields, and dependency-injection providers.

## Coverage ledger

Create the ledger before detailed tracing and update it continuously:

| ID | Protocol | External identity | Registration | Handler | Contract | Status | Gap |
|---|---|---|---|---|---|---|---|
| `http-post-orders` | HTTP | `POST /v1/orders` | `router.go:L42` | `OrderHandler.Create` | `openapi.yaml` | traced | - |

Use these statuses:

- `traced`: production implementation and all meaningful steps are proven.
- `partial`: entry is known, but one or more internal or boundary edges remain uncertain.
- `unresolved`: interface exists, but its runtime implementation or behavior cannot be established.

Never remove a partial or unresolved row to improve the coverage percentage. State exactly what evidence is missing and how to obtain it.

## Per-interface record

Record all applicable fields for every interface:

### Identity and contract

- stable ID, protocol, method/operation/topic/command, path or external name
- registration location and runtime selection condition
- request headers, path/query parameters, body/message fields, defaults, limits, and content type
- decode, normalization, and validation rules
- success response/message fields, status/code, headers, serialization, and empty-body behavior
- authentication, authorization, tenancy, rate limit, idempotency, deadline, trace, locale, and feature-flag inputs

### Ordered chain

For each step record:

- stage and concrete symbol
- what the step does, not merely its function name
- inputs consumed and outputs produced
- state read or mutated
- outbound calls or emitted messages
- context values, transaction, timeout, cancellation, retry, cache, batching, or async behavior
- source evidence and confidence

A useful minimum chain is:

```text
registration -> global middleware -> route middleware -> decoder -> validator
-> auth/policy -> handler -> application service -> domain operation
-> repository/client/event -> response mapper -> serializer
```

Do not invent empty layers. Preserve the concrete order observed in code.

### Branches, errors, and effects

- branch condition and both meaningful outcomes
- error source, wrapping/classification, translation, log/metric behavior, and external response
- persistence reads/writes and transaction boundaries
- cache keys/invalidation without copying sensitive values
- outbound protocol, target service, operation, timeout, retry, and fallback
- messages/events, delivery semantics, and producer/consumer handoff
- goroutine or channel boundary, ownership, and failure reporting
- tests that prove happy paths and important edge cases

## End-to-end trace procedure

For each ledger row:

1. Prove registration and the exact external identity.
2. Determine middleware/interceptor order from construction and mounting, not file order.
3. Follow request decoding and validation into the handler's internal input type.
4. Resolve each interface call through constructors or dependency-injection wiring.
5. Follow all meaningful success branches to persistence or external boundaries.
6. Follow validation, authorization, domain, dependency, timeout, and cancellation failures back to the external response.
7. Confirm response mapping and serialization.
8. Cross-check tests and contract files.
9. Add evidence for every step and mark remaining uncertainty.

Stop tracing standard-library/framework plumbing when repository-owned behavior ends. Name the boundary and the values crossing it.

## Shared chains

Shared behavior may be defined once to avoid repetition, but coverage remains per interface.

- Give each shared chain a stable ID such as `http-public-auth`.
- Record its ordered steps and evidence exactly as for an interface.
- In every affected interface, reference the shared-chain ID at the correct point in the order.
- Record route-specific overrides, skips, or configuration on the interface.
- Do not use “standard middleware” as a substitute for describing actual behavior.

## Reconciliation and completion

Before declaring coverage complete:

- compare registrations against schemas/contracts and tests;
- compare handler methods against registrations;
- account for versioned, admin, health, debug, and build-specific surfaces;
- count duplicate external identities and explain precedence;
- verify all shared-chain references resolve;
- ensure `discovered = traced + partial + unresolved`;
- list every partial/unresolved gap with a verification action.
