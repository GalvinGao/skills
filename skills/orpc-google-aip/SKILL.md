---
name: orpc-google-aip
description: Apply Google AIP-121/126/130 conventions when designing oRPC procedures, routers, contracts, or resource schemas. Use whenever the user designs new oRPC endpoints, refactors existing ones, models a new domain resource in Zod, picks an HTTP route/verb, names a collection, defines an enum, or asks any "how should I shape this API?" question — even when Google AIPs are not mentioned. The Google AIPs were written for gRPC, but oRPC's contract-first model and OpenAPI emission make the same conventions transfer with small adjustments; this skill provides the translated rules.
---

# oRPC × Google AIP

Google's [AIPs](https://google.aip.dev) are the most thoroughly explained API design conventions in public. They target gRPC, but oRPC's contract-first model and hierarchical routers map cleanly onto gRPC + REST, so most of the guidance carries over. This skill is the translation.

## Four rules that almost always apply

1. **Model nouns, not verbs.** Each endpoint acts on a named resource. Reach for the standard methods (`list`, `get`, `create`, `update`, `delete`) before inventing anything else. (AIP-121)
2. **Be consistent across methods.** The schema for a resource must be the same whether it appears in `create`'s response, `get`'s response, or `list`'s items. Derive input shapes via `Schema.omit(...)` / `Schema.pick(...)` / `.partial()` rather than hand-writing parallel schemas that drift. (AIP-121)
3. **Guarantee read-after-write.** After a successful mutation, a subsequent `get` must reflect it. If the operation is long-running, return a job/operation resource the client can poll — never an eventually-consistent "we'll get to it" response. (AIP-121)
4. **Pick enums conservatively.** Use an enum (a Zod literal union in UPPER_SNAKE_CASE) only when the set is small, stable (changes ≲ once/year), and not already standardized elsewhere. Include an `<ENUM>_UNSPECIFIED` member as the default sentinel. Otherwise use a documented `string`. (AIP-126)

Everything else is in the references below.

## References

Read the file matching what you're working on.

- [aip-121.md](references/aip-121.md) — **Resource-oriented design.** What counts as a resource, hierarchies, the standard-method matrix, schema consistency across methods, strong-consistency expectations, when to deviate.
- [aip-126.md](references/aip-126.md) — **Enumerations.** Zod literal unions vs `z.enum`, the `_UNSPECIFIED` zero-value convention, when to fall back to a `string`, when a `boolean` is the better choice.
- [aip-130.md](references/aip-130.md) — **Methods.** The canonical HTTP verb + path for each standard method, `PATCH` semantics for `update`, and cursor pagination using `limit` + `cursor`.

## How to use this skill in practice

1. Skim the four rules above.
2. Open the reference(s) that match the immediate question. If unsure, start with `aip-121.md` — it frames the others.
3. Apply the convention. When a rule and the user's existing codebase conflict, follow the codebase — surface the AIP as a suggestion, not a correction. Established APIs have legitimate reasons to deviate.
4. When proposing a design, cite the specific AIP rule that drove the choice (e.g. "PATCH for partial update, AIP-130") so the user can audit the reasoning instead of taking it on faith.
