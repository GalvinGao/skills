---
name: orpc-google-aip
description: Apply Google AIP-121/122/123/126/130 conventions when designing oRPC procedures, routers, contracts, or resource schemas. Use whenever the user designs new oRPC endpoints, refactors existing ones, models a new domain resource in Zod, picks an HTTP route/verb, names a collection or a path parameter, defines an enum, or asks any "how should I shape this API?" question — even when Google AIPs are not mentioned. The Google AIPs were written for gRPC, but oRPC + OpenAPI maps so closely to gRPC + REST that the same conventions transfer with small adjustments; this skill provides the translated rules.
---

# oRPC × Google AIP

Google's [AIPs](https://google.aip.dev) are the most thoroughly explained API design conventions in public. They target gRPC, but oRPC's contract-first model, hierarchical routers, and OpenAPI emission map so cleanly onto gRPC + REST that almost all the guidance carries over. This skill is the translation.

## Five rules that almost always apply

1. **Model nouns, not verbs.** Each endpoint acts on a named resource. Reach for the standard methods (`list`, `get`, `create`, `update`, `delete`) before inventing a custom one. (AIP-121, AIP-130)
2. **Name resources hierarchically.** A resource's identifier is a slash-separated path that alternates `plural-collection / id`: `publishers/{publisher}/books/{book}`. The path in `.route({ path })` *is* the resource name, and the same string flows through the API as the resource's `name` field. (AIP-122)
3. **Be consistent across methods.** The schema for a resource must be the same whether it appears in `create`'s response, `get`'s response, or `list`'s items. Derive input shapes via `Schema.omit(...)` / `Schema.pick(...)` rather than hand-writing parallel schemas that can drift. (AIP-121)
4. **Guarantee read-after-write.** After a successful mutation, a subsequent `get` must reflect it. If the operation is long-running, return a job/operation resource the client can poll — never an eventually-consistent "we'll get to it" response. (AIP-121)
5. **Pick enums conservatively.** Use an enum (a Zod literal union in UPPER_SNAKE_CASE) only when the set is small, stable (changes ≲ once/year), and not already standardized elsewhere. Include an `<ENUM>_UNSPECIFIED` member as the default sentinel. Otherwise use a documented `string`. (AIP-126)

Everything else is in the references below.

## References

Read the file matching what you're working on. Each one is short, oRPC-specific, and includes runnable Zod + oRPC snippets.

- [aip-121.md](references/aip-121.md) — **Resource-oriented design.** When to make something a resource, hierarchies vs flat namespaces, schema consistency across methods, the standard-method matrix, when a custom method is justified, strong-consistency expectations.
- [aip-122.md](references/aip-122.md) — **Resource names.** Path patterns for `.route({ path })`, collection identifier rules (plural, camelCase, DNS-safe), user-supplied vs system IDs, the `name` field on resource schemas, parent fields on list/create inputs, aliases like `users/me`, and why never to embed one resource inside another.
- [aip-123.md](references/aip-123.md) — **Resource types.** The `{service}/{Type}` identifier (e.g. `library.example.com/Book`), where to declare it in an oRPC project, how it relates to the resource-name pattern, and how to surface it for cross-service references.
- [aip-126.md](references/aip-126.md) — **Enumerations.** Zod literal unions vs `z.enum`, the `_UNSPECIFIED` zero-value convention, prefixing for package-level enums, when to fall back to a `string`, when a `boolean` is the better choice.
- [aip-130.md](references/aip-130.md) — **Methods.** The selection priority (standard → batch → custom → streaming), the canonical HTTP verb + path for each standard method, custom-method `:verb` suffix, and when to reach for streaming.

## How to use this skill in practice

1. Skim the five rules above.
2. Open the reference(s) that match the immediate question. If the user is naming a path, open `aip-122.md`. If they're adding a status field, open `aip-126.md`. If unsure, start with `aip-121.md` — it frames everything else.
3. Apply the convention. When a rule and the user's existing codebase conflict, follow the codebase — surface the AIP as a suggestion, not a correction. Established APIs have legitimate reasons to deviate.
4. When proposing a design, cite the specific AIP rule that drove the choice (e.g. "plural collection, AIP-122") so the user can audit the reasoning instead of taking it on faith.
