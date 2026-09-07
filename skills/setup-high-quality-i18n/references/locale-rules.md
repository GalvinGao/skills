# Derive a locale policy

Use this reference after discovery and the user's high-level choices. It is a decision framework,
not a universal house style or a pre-approved set of translations.

## Shared voice

Express the product's chosen tone as observable rules with short before/after examples:

- Emotional intensity, humor, celebrations, apologies, and reassurance.
- Sentence case or other casing conventions; emoji and exclamation usage by surface.
- Action labels, recovery instructions, sentence endings, and concise hints.
- Personal address, possessives, gender assumptions, and inclusive language.
- Domain terminology, units, numbers, dates, and formatting ownership.
- Sentence restructuring and layout budgets without loss of meaning.

Avoid absolute bans inherited from a different product. For example, a playful onboarding
surface and a destructive confirmation can have different intensity within the same voice.
Do not shorten away consequences, consent, negation, limits, or recovery instructions.

## One row per supported locale

Document these fields, citing local evidence or a language reference where applicable:

| Field | Decision to make |
| --- | --- |
| Locale identity | Language, region, and script; resolve ambiguous tags. |
| Register | Pronoun and politeness level; differences between prose and controls. |
| Grammar | Gender, case, agreement, imperative/infinitive choices, possessives. |
| Typography | Quotes, apostrophes, colons, terminal punctuation, dashes, spacing. |
| Terminology | Regional vocabulary and domain terms; approved loans and brand treatment. |
| Dynamic content | Placeholder agreement, number/date formatting, plural/select semantics. |
| Layout | Wrapping, font coverage, truncation, text expansion, and directionality. |
| Evidence | Explicit requirement, language convention, or provisional recommendation. |

Do not confuse a house preference with a grammar rule. A regex can find likely register drift;
it cannot establish that every matching word is wrong in every sentence.

## Language-driven questions

Investigate only the relevant groups. These are prompts for reasoning, not fixed answers:

- **Languages with address levels:** choose a consistent level based on audience and tone.
  Consider German du/Sie, Romance address forms, and Japanese/Korean speech levels separately;
  do not derive one language's register by mechanically translating another's pronoun.
- **Regional vocabulary or scripts:** establish the intended variety for Portuguese, Spanish,
  Chinese, and any other ambiguous locale. Check whether the project's tags and formatters
  express the same choice as its copy.
- **Case and agreement:** test arbitrary names and titles in inflected phrases. Restructure
  sentences where runtime values cannot carry the required case, gender, or particle. Quoting
  a placeholder is not a universal grammatical fix.
- **CJK and Thai:** evaluate punctuation, boundaries around numbers/Latin text, segmentation,
  and wrapping in the actual UI. Do not force English spaces or character ratios onto them.
- **Arabic, Hebrew, and other RTL text:** verify bidirectional behavior with mixed-script
  placeholders, numbers, and punctuation. Distinguish language direction from icon/layout rules.
- **Locale-sensitive casing and diacritics:** check runtime transformations and font coverage,
  not just catalog spelling.

Consult current authoritative language or locale-data sources when uncertain. For framework
syntax, inspect the installed version and its documentation; do not transfer one compiler's
fallback or selector rules to a different message format.

## Counts and variables

Determine cardinal versus ordinal selection and supported numeric inputs. Use the runtime's
actual locale-data behavior, including reachable zero, fractions, and large values. Never infer
plural categories from the source language or an old hardcoded language list.

Some translations need selectors where the source does not. Some count-invariant phrases need
no selector. Preserve required runtime inputs without forcing all languages into identical
message shapes. Verify catch-all behavior and branch order against the actual compiler.

Check placeholders and markup per reachable variant, including multiplicity and nesting.
Compare corresponding semantic branches; a source branch can legitimately omit a token, so
the union of every source branch is not automatically required in every translation branch.
Separate grammatical restructuring from accidental token loss.

## Fit and consistency

Use the real control width, adjacent labels, and rendering behavior as evidence. Character
ratios are screening heuristics, not universal pass/fail thresholds. Prefer a concise equivalent
when one exists; otherwise flag a layout problem instead of deleting meaning or shrinking fonts.

When changing a term, sweep the whole relevant concept family, including plural branches and
placeholder-bearing strings. Keep distinct concepts distinct even if they share a source word.
