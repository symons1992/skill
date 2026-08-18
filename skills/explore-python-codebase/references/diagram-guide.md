# Offline report visualization guide

## General rules

- Answer one question per visual and state it in the title.
- Prefer the report template's native HTML and CSS.
- Use inline SVG only when a relationship is materially clearer than the ordered chain or a table.
- Never use Mermaid, CDNs, remote fonts/icons/images, canvas libraries, or runtime network requests in the delivered HTML.
- Keep source paths out of visual labels; place evidence beside the relevant step.
- Back every node and edge with inspected source, configuration, schema, migration, or test evidence.

## Architecture and execution views

Use a small component table or inline SVG for repository/process boundaries and dependency direction. Do not label an import/dependency diagram as a runtime execution chain.

Use the ordered step rail for each interface. Record stage, qualified symbol, behavior, input/output, state/effect, sync/async boundary, evidence, and confidence. Place shared-chain references at their actual execution point and show decorator/middleware execution order rather than source order.

Use an ordered sequence table when timing, transactions, lazy evaluation, or async handoffs matter. Represent task submission and later worker consumption separately. Show transaction, retry, timeout, and cancellation behavior only when proven.

Use branch and exception tables for validation, policy, retry/fallback, status mapping, and transformations. Do not collapse failures with different status codes, retries, exit codes, dead-letter paths, or operational signals.

## Accuracy and offline checks

- Back every edge with a call, decorator, registration, setting, message operation, or state update.
- Distinguish import-time, sync, await, background-task, thread, process, and queue behavior.
- Show transaction, lazy-evaluation, timeout, retry, cancellation, and process boundaries.
- Mark dynamic, plugin-selected, environment-specific, or inferred edges.
- Keep evidence discoverable without a separate legend.
- Render with networking disabled and no external URLs.
