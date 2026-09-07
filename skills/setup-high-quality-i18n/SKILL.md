---
name: setup-high-quality-i18n
description: Set up a project-specific localization skill by discovering its catalogs and supported languages, asking about product voice and audit tooling, and generating tailored voice, glossary, review, and QA instructions. Use when establishing or revising a project's localization workflow.
---

# Set up high-quality i18n

Turn `$ARGUMENTS` and the current repository into a local `high-quality-i18n` skill.
This is an interactive setup workflow: discover what the project already knows, ask for the
remaining product choices, then write concrete instructions another agent can use without
repeating setup. Do not translate the whole application as part of setup.

## 1. Inspect before asking

Read repository instructions and locate the existing skill convention. Inspect localization
configuration, catalog paths, source locale, enabled locale list, generated catalogs, package
scripts, and representative call sites. Follow the repository's search conventions; keep
discovery focused on localization and product voice.

Record evidence for:

- Product purpose, audience, and existing editorial or brand guidance.
- Source language and supported locales, including regional/script variants. Distinguish
  enabled locales from unused files, fallback locales, and generated key/pseudo locales.
- Catalog format, placeholder and rich-text syntax, plural/select handling, fallback behavior,
  compilation commands, and existing checks.
- Existing voice decisions, glossary, audit rules, and local `high-quality-i18n` skill, if any.

Sample buttons, errors, hints, empty states, and onboarding in each supported language.
Existing copy is evidence, not proof of intent: do not silently turn inconsistencies or majority
usage into binding rules. Do not inherit policy from unrelated repositories.

## 2. Ask for direction

Present the findings briefly. Ask only unresolved questions, preferably in one short round.
Answers already supplied in the conversation count; never ask the user to repeat them.

- **Overall tone:** ask what the product should sound like. Offer a recommendation grounded
  in its audience, with concrete alternatives such as concise and professional, warm and
  approachable, or playful and expressive. Include two short versions of the same generic UI
  message so the choice is tangible. If explicit guidance already settles this, use it; if the
  tone is merely inferred from catalogs, ask the user to choose or refine it.
- **Languages:** use the configured source and supported locales when they are clear. Ask only
  if they cannot be established, conflict, or leave a material regional/script choice unresolved.
  Do not infer a region from a bare language code without supporting evidence.
- **Main localization audit:** ask which tool the user wants to use, unless they have already
  chosen. Present these preferences explicitly:

  | Choice | Guidance |
  | --- | --- |
  | Antigravity CLI | Most recommended for the main localization audit. |
  | `codex exec` with `5.6-terra` | A good alternative. Verify the installed tool's accepted model identifier. |
  | Opus 4.6 | Not recommended; can be used when it is the only option the user has. |

These are this workflow's recommendations, not claims of measured benchmark superiority.
Allow another tool or no external auditor. Tool availability does not decide the user's
preference. If their selected tool is unavailable, explain the concrete gap and ask whether to
configure it or choose an alternative; do not silently switch providers or models.

Continue independent discovery while waiting. Do not finalize voice, locale scope, or reviewer
configuration from unanswered questions. Avoid a long questionnaire: resolve lower-level
editorial choices from the selected direction and locale conventions in the next step.

## 3. Derive rules for the actual languages

Read [references/locale-rules.md](references/locale-rules.md). Build a tailored voice matrix
only for the languages this project supports. For each decision, distinguish an explicit
product choice, an established language convention, and a provisional recommendation.

Translate the overall tone into each locale's register, address forms, control verbs,
punctuation, regional vocabulary, placeholder grammar, and count handling. A friendly product
does not require the same literal pronoun or politeness device in every language. Resolve
material conflicts with the user; make ordinary editorial choices and document their basis.

Extract a small glossary from real UI concepts. Classify entries as do-not-translate, hard,
or contextual; record locale forms, surface distinctions, and allowed grammatical inflections.
Keep missing or disputed terms explicitly provisional. Do not manufacture a full glossary
from unrelated products or promote every existing translation to a hard lock.

## 4. Configure the selected auditor

Inspect the selected CLI's local help and available model configuration. Use current official
documentation when necessary, following repository documentation-tool rules. Do not guess
commands, flags, model IDs, authentication steps, or output capabilities.

Record the verified invocation, provider/model, prompt delivery method, and output format.
Prefer stdin or a prompt file supported by the tool. Never interpolate translation text into
shell code. Keep credentials out of generated files. Do not install tools, change accounts,
or choose paid fallbacks just to make the setup appear complete.

Configure the main audit to cover all changed strings in manageable per-locale batches, with
deeper review of errors, confirmations, onboarding, and other prominent text. A second
independent reviewer is optional, capability-dependent, and subject to the user's tool choices.
AI review is not human native-speaker validation. Report which actually occurred.

## 5. Generate the project skill

Read [references/generated-skill.md](references/generated-skill.md) for the output contract.
Use the repository's existing skill location; absent a convention, use
`.agents/skills/high-quality-i18n/`. Respect a user-specified path. Merge an existing skill
carefully, preserving intentional custom rules; do not overwrite the setup skill itself or
install project-specific instructions globally.

Write `SKILL.md`, `VOICE.md`, `GLOSSARY.md`, `ADVISORY.md`, and `QA.md` with real project paths,
languages, decisions, and verified commands. Include executable QA only when existing checks
leave a concrete gap and an adapter for the detected catalog format is justified. Reuse existing
checks first. Leave no fake commands, assumed locale counts, or unexplained policy defaults.

Keep future glossary updates and approved voice changes in the project-local files. Public
setup instructions and reusable templates must stay free of private names, URLs, account
identifiers, catalog snapshots, production metrics, and historical project audit findings.

## 6. Verify and hand off

- Check frontmatter, relative links, paths, and command availability. Confirm all enabled
  locales are covered and generated locales are identified separately.
- Exercise the workflow on a small representative sample without editing catalogs: one control,
  one error, one placeholder message, and a plural/select message if present. Run the chosen
  auditor on that sample when configured and authorized; report unavailable execution honestly.
- Run existing localization checks to establish a fresh baseline. If adding a QA script, test
  valid and intentionally invalid fixtures, including missing keys and broken variant tokens.
- Review generated rules against the user's tone, language, and auditor choices. No generic
  template text should masquerade as a settled project decision.

Summarize generated files, the selected voice and languages, auditor readiness, checks run,
and any unresolved decisions. Distinguish setup validation from a complete catalog audit.
Do not claim the application is fully localized or independently reviewed from a setup sample.
