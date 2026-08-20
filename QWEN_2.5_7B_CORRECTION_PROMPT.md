# Qwen 2.5 7B — Correction Prompt Reference

## Purpose

This document defines the correction prompt used when the Qwen 2.5 7B model
produces output that fails QA validation. The correction prompt is the
mechanism by which we guide the model back to compliance on retries.

## Correction Prompt Structure

The correction prompt consists of:

1. **System prompt** — The original rules/prompt (unchanged from the first attempt)
2. **User message** — Contains:
   - The list of validation errors from the previous attempt
   - The raw output the model produced
   - The facts JSON that must be expressed
   - Explicit instructions to fix ALL errors and return ONLY valid JSON

## Key Principles

### Error Feedback
Each error is listed as a bullet point with:
- The field name that failed
- The specific violation detected
- What the model should do instead

### Fact Anchoring
The facts JSON is always re-included in the correction prompt so the model
has the ground truth available. This prevents the model from "remembering"
incorrect facts from its previous attempt.

### Instruction Emphasis
The correction prompt explicitly states:
- "Fix ALL errors" (not just some)
- "Return ONLY valid JSON" (no markdown, no prose wrappers)
- "Do NOT invent any facts, dates, planets, or remedies"
- "Express the provided facts in natural language"

## Retry Behavior

- Maximum retries: 2 (total 3 attempts including the original)
- Each retry uses the same correction prompt structure
- After all retries are exhausted, the system falls back to deterministic prose

## Error Categories Handled

The correction prompt addresses these error categories:

1. **Schema errors** — Missing required keys, wrong types
2. **Customer placeholder errors** — Template markers like `{{...}}`, `[TODO]`
3. **Forbidden content errors** — Invented dates, certainty language, remedies
4. **Quality errors** — Too short, too long, filler phrases
5. **Parse errors** — Invalid JSON, markdown wrappers

## Implementation

The correction prompt is built by `_build_correction_prompt()` in
`engines/astro/llm/humanize.py`. See that function for the exact implementation.

## Example Error Messages

```
- conclusion: too short (25 words, minimum 40). Write a complete substantive paragraph.
- remedy: contains forbidden remedy/prescription ("you should wear")
- headline: contains template placeholder ({{area}})
- conclusion: contains invented date (March 15, 2025)
- conclusion: contains forbidden certainty language ("definitely")
```

## Fallback Behavior

When all retry attempts fail:
1. The system logs the final errors
2. A deterministic fallback is generated from the facts
3. The fallback output has `source: "fallback"` instead of `source: "llm"`
4. The customer sees clean, factual prose (never the raw LLM errors)
