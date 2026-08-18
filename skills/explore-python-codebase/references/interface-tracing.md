# Exhaustive Python inbound-interface tracing

## Contents

- Coverage contract
- Interface discovery
- Framework resolution rules
- Coverage ledger
- Per-interface record
- End-to-end trace procedure
- Shared chains
- Reconciliation and completion

## Coverage contract

Treat an inbound interface as any externally invocable trigger that starts repository-owned behavior. In access-layer repositories, completeness is more valuable than selecting prominent flows.

Include HTTP routes; RPC methods; GraphQL operations; WebSocket/SSE handlers; queue/topic/stream consumers; task workers; scheduled jobs; workflow/DAG entry points; serverless handlers; CLI and management commands; and intentionally public library entry points. Include owned health, admin, debug, callback, and webhook routes.

Exclude framework internals and generated glue only after linking them to the owned registration or implementation. Keep generated contract evidence when it defines the external surface. Treat signals/listeners as shared or secondary triggers when the framework invokes them independently.

## Interface discovery

Search registrations and contracts independently:

1. Start at application/server/worker construction, settings, URL/router modules, task discovery, CLI groups, and deployment handler strings.
2. Inspect OpenAPI, protobuf, GraphQL, AsyncAPI/event schemas, serverless manifests, packaging entry points, and generated route/stub files.
3. Search handler/view/controller/resolver/task/command methods and framework decorators.
4. Inspect tests that invoke clients, routes, methods, tasks, commands, consumers, or handlers.
5. Resolve prefixes, mounts/includes, namespaces, versioning, app registries, autodiscovery, plugin entry points, and environment-specific settings.
6. Compare all lists. Report implementation-only, contract-only, deployment-only, and test-only entries.

Do not assume each decorated function is reachable. Prove that its router, blueprint, app, schema, or task module is mounted, included, imported, discovered, or selected in production.

## Framework resolution rules

- **FastAPI/Starlette:** combine `include_router` prefixes, router and route paths, mounted apps, host routes, and dependency layers. Preserve middleware and dependency execution/caching order.
- **Flask:** combine application/blueprint prefixes, nested blueprints, `add_url_rule`, endpoint names, subdomains, and factory registration. Resolve request hooks, teardown, and error handlers by scope.
- **Django/DRF:** recursively expand `urlpatterns`, `include`, namespaces, locale/version patterns, DRF routers/actions, class-based `as_view()` dispatch, middleware order, authentication/permission/throttle classes, serializers, and exception handlers. Separate framework-owned admin routes from repository customizations.
- **aiohttp/other ASGI:** expand route tables, sub-app prefixes, class views, middleware factories, lifespan/startup hooks, and method dispatch.
- **gRPC:** enumerate methods from protobuf descriptors, connect `add_*Servicer_to_server` calls to concrete servicers, and include interceptors and status translation.
- **GraphQL:** enumerate externally callable schema fields/operations rather than arbitrary helpers; connect schema construction, binding, middleware, context, dataloaders, and subscriptions.
- **Tasks/consumers:** prove task/topic/queue names, discovery, routing, serialization, acknowledgement/delivery, retries, time limits, and failure behavior.
- **Schedulers/workflows:** record triggers, DAG/workflow registration, ordering, retries, backfills, concurrency, and state storage without implying one process owns the whole workflow.
- **CLI:** combine nested group paths and packaging/framework registration; record arguments/options, environment, exit codes, output, and effects.
- **Serverless:** reconcile configured handler strings and event bindings with functions; include cold-start initialization, retry/idempotency, and platform response adapters.

## Coverage ledger

Create the ledger before deep tracing and update it continuously:

| ID | Protocol | External identity | Registration | Handler | Contract | Status | Gap |
|---|---|---|---|---|---|---|---|
| `http-post-orders` | HTTP | `POST /v1/orders` | `api/routes.py:L42` | `create_order` | `openapi.yaml` | traced | - |

Use these statuses:

- `traced`: production implementation and all meaningful steps are proven.
- `partial`: entry is known, but one or more internal or boundary edges remain uncertain.
- `unresolved`: interface exists, but its runtime implementation or behavior cannot be established.

Never remove a partial or unresolved row to improve coverage. State the missing evidence and a concrete way to obtain it.

## Per-interface record

Record all applicable identity and contract details: stable ID, protocol, final external name and aliases; registration, composition/import path, and selection conditions; inputs, defaults, limits, parsing, validation, serialization; success output/status; authentication, authorization, tenancy, rate limits, idempotency, deadlines, trace, locale, session, and feature flags.

For each ordered step record:

- stage and concrete qualified symbol;
- behavior, inputs, outputs, state read/mutated, and point of lazy evaluation;
- outbound calls/messages and external effects;
- request/context/session/transaction state;
- sync/async mode, await/task/thread/process/queue boundary, timeout, cancellation, retry, cache, or batching;
- source evidence and confidence.

Use only layers that exist. A common web chain is:

```text
registration -> application middleware -> router dependency/middleware
-> parser/model/serializer -> auth/policy -> handler -> service/domain
-> ORM/repository/client/event -> exception/response mapper -> serializer
```

Also record meaningful branches; exception source/chaining/classification/retry/translation; query evaluation and transaction boundaries; cache behavior; outbound targets; message delivery/ack semantics; async ownership/failure reporting; and tests for happy paths and edge cases.

## End-to-end trace procedure

For each ledger row:

1. Prove registration, reachability, production composition, and exact external identity.
2. Determine middleware/decorator/dependency/interceptor order from framework composition, not source appearance alone.
3. Follow parsing, coercion, validation, and serialization into internal types.
4. Resolve imports, re-exports, wrappers, descriptors, injected/duck-typed calls, and factories to production implementations.
5. Follow every meaningful success branch to persistence, output, or an external boundary.
6. Follow validation, authorization, domain, dependency, timeout, cancellation, and retry-exhaustion failures back to the external result.
7. Trace signals, hooks, callbacks, background tasks, and queue submissions as separate side-effect chains.
8. Confirm response/result/status/exit-code mapping and serialization.
9. Cross-check tests, contracts, settings, and deployment metadata.
10. Add evidence for every step and keep uncertainty explicit.

Stop tracing standard-library/framework plumbing when repository-owned behavior ends. Name the boundary and values crossing it. Do not import application modules solely to inspect routes unless safe execution has been established.

## Shared chains

Define shared behavior once while retaining per-interface coverage:

- Give each chain a stable ID such as `http-public-auth` or `celery-task-wrapper`.
- Record ordered steps and evidence exactly as for an interface.
- Reference the chain at the exact execution point in every affected interface.
- Record route/task/command-specific overrides, exclusions, and configuration.
- Do not use labels such as “standard middleware” in place of actual behavior.

## Reconciliation and completion

Before declaring coverage complete:

- compare registrations against contracts, deployment/configuration, and tests;
- compare handler/view/task/command/resolver declarations against reachable registrations;
- account for versioned, admin, health, debug, callback, webhook, management, and environment-specific surfaces;
- explain duplicate identities, route ordering, and precedence;
- verify mounted routers/blueprints/apps and discovered task/plugin modules are actually loaded;
- verify all shared-chain references resolve;
- ensure `discovered = traced + partial + unresolved`;
- list every gap with a verification action.
