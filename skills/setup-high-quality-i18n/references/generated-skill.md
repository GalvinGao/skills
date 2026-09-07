# Generated high-quality-i18n contract

Generate project-specific instructions from verified findings and user choices. The files below
are the deliverables, not blank templates to copy verbatim. Keep them concise and cross-linked.

## SKILL.md

Use YAML frontmatter with `name: high-quality-i18n` and a description targeting translation,
wording audits, glossary consistency, and register drift in the discovered catalogs. Mention
the real source locale and catalog location. Link any existing framework mechanics skill only
when it exists; otherwise document the necessary syntax in QA.md.

Include this operational workflow:

1. Read VOICE.md and GLOSSARY.md. Establish the touched keys/locales and a fresh QA baseline.
2. Fix unclear source text before propagating it. Respect the user's requested scope; a focused
   locale correction need not rewrite every language, but source/key changes require checking
   all affected catalogs and generated artifacts.
3. Build a context pack per key: source, rendering call site, control type, adjacent strings,
   layout budget, placeholder meanings and sample values, glossary terms, and intended behavior.
4. Evaluate at least five structurally different candidates per key and locale: literal,
   idiomatic, concise, alternate-register, and restructured. Compare meaning, house register,
   terminology, grammar, dynamic values, and fit. The alternate-register candidate tests the
   choice; it does not authorize drift. Keep concise candidate notes and a selection reason,
   rather than a transcript of internal deliberation.
5. Run the configured audit from ADVISORY.md. Reconcile advice against meaning, runtime
   integrity, approved glossary, and voice; reviewers return suggestions rather than editing
   catalogs. Disclose unavailable review and exact coverage.
6. Apply small edits preserving keys, ordering, comments, and formatting where the format
   allows. Use the format's parser/editor for ambiguous replacements; never blindly replace
   duplicate text across a catalog. Preserve structural semantics and regenerate generated
   files using the project's real command.
7. Run QA.md checks and sweep changed term families. Summarize scope, meaningful wording
   decisions, validation, review coverage, and remaining findings.

## VOICE.md

Write the user's high-level brief, concrete shared rules, and the supported-locale matrix from
locale-rules.md. Include representative project-local examples and the basis of each major
decision. Preserve deliberate surface exceptions. Identify open recommendations honestly and
keep historical audit counts out of normative rules.

## GLOSSARY.md

Include approved terms and a compact schema:

`concept | source term | locale | preferred form | lock type | surface/context | allowed inflection | evidence`

- **Do-not-translate:** exact protected names or tokens, with explicit casing rules.
- **Hard:** approved concept term; grammatical inflection is allowed as documented.
- **Contextual:** variants selected by surface or meaning, with disambiguating examples.

Keep uncertain terms separate from approved locks. Never let an inflexible glossary create
ungrammatical text: surface a conflict for resolution. Describe how to update all occurrences
of a changed concept and any real upstream source. Do not invent a remote glossary dependency.

## ADVISORY.md

Record the user's main tool choice, exact verified invocation/model, safe prompt delivery,
batch size appropriate to context limits, and result format. If unconfigured, state the missing
prerequisite without supplying a plausible-looking command. Do not silently replace a selected
model when execution fails. A sample run establishes readiness; it is not a whole-catalog audit.

Use this provider-neutral prompt shape, populated from the project:

```text
Review UI copy for this product and audience: [brief].
Target locale and variety: [locale]. Voice and register: [rules].
Approved terms and contextual variants: [relevant glossary subset].
For each candidate, check meaning, naturalness, grammar, register, terminology,
placeholder behavior, and fit. Keep good text; do not rewrite solely for taste.
Return: key | keep/change | proposed text | concise reason | uncertainty, if any.

Key: [key]
Surface and neighbors: [context]
Source: [source text]
Candidate: [translation]
Dynamic values/variants: [meaning and examples]
Available width or length guidance: [budget]
```

Cover every changed string in the main audit. Give prominent or difficult strings a deeper
pass with neighboring copy and dynamic examples. A second independent channel is optional;
repeating the same model is not independent native-speaker validation. Follow the environment's
delegation permissions rather than assuming subagents are available.

Reject suggestions that alter meaning or break runtime structure. Enforce approved terminology
with grammatical agreement, then register and punctuation. Prefer a substantiated locale
convention over taste; agreement between reviewers does not override a concrete defect. Log
material overrides briefly and report human versus AI review accurately.

## QA.md and optional script

List real commands, expected outcomes, and manual checks. Separate structural errors from
editorial heuristics and pre-existing findings. Reuse the project's compiler, linter, and tests
before adding an adapter. Do not claim deterministic QA proves naturalness.

Cover:

- Catalog parsing, required key parity, unexpected keys, scoped missing keys, and source errors.
- Placeholders, rich-text token multiplicity/nesting, selectors, and fallback behavior per
  semantic variant, including legitimate locale-specific message shapes.
- Reachable count cases and generated key/pseudo locales, without linguistic checks on
  deliberately synthetic text.
- Register and glossary drift using this project's approved rules; narrowly justified
  exceptions rather than exemptions for entire unrelated key families.
- Source-identical text as a warning with explicit approved brands/loanwords; no assumption
  that every identical string is untranslated or every Latin word is exempt.
- Punctuation, whitespace, font coverage, representative rendered fit, and RTL where relevant.

If a script is needed, generate it for the detected format and configuration. Reject unsupported
shapes or invalid scope arguments clearly instead of silently reporting success. Test a valid
fixture and broken keys, tokens, and plural/select branches. Keep reports complete when piped;
verify nonzero exit status for structural failures. Record actual commands and observed results.

Setup should not silently fix the baseline or perform a bulk translation. Report findings and
leave the generated workflow ready for the user's next localization task.
