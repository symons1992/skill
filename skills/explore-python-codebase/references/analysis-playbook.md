# Python codebase analysis playbook

## Contents

- Investigation order
- Evidence and confidence
- Project and package shapes
- Entry-point and framework discovery
- Python call-chain resolution
- Runtime and data behavior
- Validation strategy

## Investigation order

Start broad, then narrow:

1. Read `pyproject.toml`, setup/requirements files, lock files, supported Python versions, top-level directories, build files, deployment manifests, and existing docs.
2. Identify source and import roots, including `src/` layouts, flat packages, namespace packages, monorepo members, editable/local dependencies, and generated packages.
3. Find executable surfaces: ASGI/WSGI apps and factories, framework URL/router modules, console scripts, `python -m` modules, workers, schedulers, workflows, serverless handlers, operational notebooks, and public libraries.
4. Find composition roots: settings modules, application factories, dependency providers, app registries, startup/lifespan hooks, container wiring, and plugin loading.
5. Build a complete inbound-interface coverage ledger before deep tracing.
6. Trace every interface into domain/service code, ORM/repositories, clients, and emitted events. Prioritize high-risk interfaces first without stopping at a subset.
7. Read tests beside implementation. Fixtures, dependency overrides, factories, mocks, and parametrization often prove contracts and runtime selections.
8. Inspect schemas, migrations, generated clients/stubs, templates, configuration, and deployment commands for behavior not obvious in `.py` files.

Avoid reading files sequentially. Search symbols, decorators, call sites, import aliases, and configuration keys to form hypotheses, then verify them.

## Evidence and confidence

Classify findings internally:

- **Confirmed**: direct source calls/decorators, URL composition, production factory wiring, settings, schema, migration, or executable tests prove the claim.
- **Corroborated**: independent evidence agrees, but environment, plugin, or runtime selection remains possible.
- **Inferred**: naming or framework convention suggests the claim; state the assumption and verification method.
- **Unknown**: dynamic import, monkey patching, missing dependency source, metaprogramming, generated runtime state, or environment prevents resolution.

Use repository-relative evidence paths and the smallest useful line range. Include the qualified symbol in prose. Refresh line numbers after edits. Use solid visual edges for confirmed behavior and dashed edges only with an explicit legend.

Treat type hints, docstrings, protocols, abstract base classes, `.pyi` stubs, and mocks as shape evidence, not proof of the production implementation. Treat runtime introspection as corroboration only when it can be executed safely without triggering external effects.

## Project and package shapes

Recognize conventions without assuming semantics:

- `src/<package>/` and top-level `<package>/` are common import roots; map import names to files before tracing.
- `__init__.py` may re-export symbols or trigger import-time registration and side effects.
- PEP 420 namespace packages can span directories or distributions without `__init__.py`.
- `apps.py`, `settings*.py`, `urls.py`, `asgi.py`, `wsgi.py`, `manage.py`, and `migrations/` commonly indicate Django roles.
- `main.py`, `app.py`, `application.py`, `routes/`, `routers/`, `views/`, `api/`, and `dependencies.py` are hints, not proof.
- `tasks.py`, `consumers.py`, `signals.py`, `commands/`, `dags/`, and `workflows/` often expose non-HTTP triggers.
- `setup.py`, `setup.cfg`, and `[project.scripts]` or tool-specific script tables define packaging and CLI surfaces.
- `requirements*.txt`, `poetry.lock`, `uv.lock`, `Pipfile.lock`, `pdm.lock`, and environment manifests help select relevant framework/version behavior.

For monorepos, map project and distribution boundaries before module boundaries. Note editable installs, path dependencies, extras, dependency groups, and optional plugins because they can change the active graph.

## Entry-point and framework discovery

Search concrete registration plus declared contracts. Common candidates include:

```text
FastAPI|APIRouter|add_api_route|include_router|mount|websocket
Flask|Blueprint|route|add_url_rule|register_blueprint
urlpatterns|path|re_path|include|ViewSet|router.register
Starlette|Route|WebSocketRoute|Mount|aiohttp|add_routes
add_*Servicer_to_server|grpc.*Server
strawberry|graphene|ariadne|resolver|mutation|subscription
Celery|shared_task|task|send_task|RQ|dramatiq|consumer|subscribe
APScheduler|add_job|cron|schedule|Airflow|Prefect|Dagster
click|typer|argparse|console_scripts|project.scripts
lambda_handler|handler|functions_framework|cloud_event
if __name__ == "__main__"|__main__.py
```

Resolve registrations rather than merely listing decorated functions:

- Compose router, blueprint, mount, and Django `include()` prefixes into the final external identity.
- Account for class-based views, DRF routers/actions, inherited handlers, generic views, and HTTP method maps.
- Link generated gRPC registration functions to concrete servicers and protobuf methods.
- Distinguish task declaration names from queue/routing configuration and worker discovery.
- Derive CLI command paths through nested groups and aliases, not function names alone.
- Inspect deployment commands (`uvicorn`, `gunicorn`, `celery`, `manage.py`, serverless handler strings) to prove the production application or factory.
- Reconcile implementation routes with OpenAPI/protobuf/GraphQL/event contracts and test clients in both directions.

## Python call-chain resolution

Trace each inbound interface as:

```text
trigger -> framework adapter -> handler/use case -> domain operation
-> repository/client/message -> effect -> external result
```

Expand the chain with middleware, decorators, dependency providers, parsing/validation, identity/policy, serializers, transactions, signals/hooks, exception handlers, and background handoffs. Preserve actual runtime order; decorator source order and middleware configuration order can differ from execution order.

For every edge, locate the call/access expression and resolve the runtime object:

1. Resolve relative imports, aliases, wildcard imports where possible, and package re-exports.
2. Locate the function, method, callable object, descriptor, or decorator wrapper.
3. Follow factory return values and production construction/settings to the selected implementation.
4. For protocols, ABCs, injected dependencies, and duck-typed objects, find candidates and prove selection at the composition root.
5. Track callbacks, partials, closures, bound methods, and callable instances to construction.
6. If selection remains runtime-dependent, list candidates and the selection condition; do not guess.

Treat these carefully:

- Decorators replace or wrap symbols; inspect wrapper behavior and `functools.wraps` chains.
- Descriptors, properties, `__getattr__`, `__getattribute__`, metaclasses, and ORM managers can redirect attribute access.
- Imports execute module top-level code once per interpreter and can register handlers or signals.
- Monkey patches and plugin entry points can replace implementations after import.
- Framework dependency injection may cache values per request, application, or process.
- `async def` is not automatically concurrent; record actual `await`, task creation, executor, thread, and process boundaries.
- `asyncio.create_task`, task groups, callbacks, Celery/RQ submission, and broker publishes create distinct ownership and error-reporting boundaries.
- Context variables, thread locals, request state, and scoped sessions have different propagation rules.
- Lazy QuerySets and generators defer work; identify where evaluation and exceptions actually occur.
- Signals/events can add side effects invisible at the direct call site.

Use language-server references, AST tools, or framework route inspection when already available, but verify high-value results in source/configuration. Avoid importing arbitrary application modules only for discovery: imports can connect to databases, read secrets, start threads, or mutate state.

## Runtime and data behavior

For each critical flow, answer:

- What parses, validates, normalizes, and serializes input/output?
- What identity, authorization, tenant, locale, trace, deadline, request, session, or context-variable state propagates?
- What state is read or mutated, and when are lazy operations evaluated?
- Which transaction/session/unit-of-work owns the operation and its commit/rollback?
- Which operations are idempotent, retried, cached, batched, rate-limited, or eventually consistent?
- What leaves the process: SQL, RPC, HTTP, queues, object storage, files, metrics, logs, email, or events?
- How are exceptions caught, chained, classified, retried, logged, and translated to an external result?
- Who owns event loops, tasks, threads, processes, greenlets, locks, pools, and shutdown?

Confirm persistence relationships with ORM mappings, queries, migrations, schemas, or repository code. Do not infer them only from model names or type annotations. Never copy secret values from `.env`, settings, deployment manifests, or fixtures.

## Validation strategy

Prefer the project's declared environment and cheapest meaningful checks:

- Run the bundled scanner and syntax-compile owned sources without importing them.
- Use the existing test runner/configuration (`pytest`, `unittest`, tox, nox, Hatch, Poetry, uv, PDM) when practical.
- Run focused tests before a slow full suite; do not install or update dependencies without authorization.
- Use framework checks or safe route introspection only when the environment is configured and execution will not trigger external effects.
- Treat type-checker, linter, and coverage configuration as design evidence; run them only when useful.
- Record failures caused by missing services, environment variables, optional extras, incompatible Python versions, generated files, private indexes, or genuine defects.

Cross-check every interface against registration and implementation evidence, then against at least one of tests, schema/configuration, or deployment metadata when available. Report disagreements. Finish with `discovered = traced + partial + unresolved`; never omit an uncertain interface.
