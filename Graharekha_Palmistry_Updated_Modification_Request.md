# Graharekha Palmistry — Updated Modification Request

## Objective

Modify the current Graharekha palmistry report-generation system so the paid report is evidence-driven, confidence-aware, deduplicated, concise, and production-ready.

**Core architecture:**

> **Software calculates. Qwen 2.5 7B explains. HTML presents.**

Qwen must not perform the core palmistry reasoning.

---

# 1. FINAL CUSTOMER REPORT STRUCTURE

The primary paid report should contain only:

1. **Chart / Palm Signature**
2. **Where You Are Now**
3. **Life Areas**
   - Work & Career
   - Money & Resources
   - Relationships & Emotions
   - Health & Vitality
   - Travel / Change / Imagination
   - Personal Growth / Direction
4. **Final Practical Guidance**

Every life area must contain:

```text
Verdict
One astrologer-style conclusion
Timing
What helps
▸ Calculation & future checkpoints [collapsed]
```

Remove redundant customer-facing sections such as repeated timelines, repeated special-mark explanations, duplicate summaries, and repeated evidence.

---

# 2. CHART / PALM SIGNATURE

Keep this short and evidence-based.

Example:

> **Palm Signature**
>
> Air-type hand with a clearly developed Venus mount, a defined Life line and stronger Jupiter-area markings. The overall pattern points toward an analytical, ambitious and people-oriented temperament, with the strongest themes around responsibility, professional growth and sustained effort.

Do not dump the detection database here.

---

# 3. WHERE YOU ARE NOW

This must describe the current phase from the **confluence of actual evidence**, not generic philosophy.

Example:

> **Where You Are Now**
>
> Your current pattern shows a demanding but constructive phase. The stronger Jupiter indications support ambition and professional visibility, while the weaker markings around the same area suggest that progress can feel scattered when too many responsibilities compete. The overall indication is not of failure, but of a phase where focus and disciplined execution matter more than speed.

---

# 4. LIFE-AREA CONCLUSION — MOST IMPORTANT

Each life area must have ONE useful astrologer/palmistry-style conclusion.

Do NOT output calculation fragments such as:

> House 10: Supported. Timing: Active now.

Instead, combine all relevant evidence.

### Example — Work & Career

**Verdict: Good with pressure**

> Your career pattern is fundamentally supportive, but the present phase is more demanding than the long-term picture. The stronger Jupiter indications support ambition, leadership and recognition, while the grille on the same mount shows periods where effort can become scattered. The stronger Head and Life line indicators provide persistence, so the current pressure appears more like a demanding phase than a structural career weakness. The direction improves when the conflicting indicators weaken and the stronger career-supporting pattern becomes dominant.

**Timing**

> Current phase: demanding but constructive.  
> Near-term: pressure remains while the conflicting indicators are active.  
> Next supportive window: only the engine-generated window may be shown.  
> Long-term direction: only if supported by calculated evidence.

**What helps**

> Concentrate on fewer priorities, take ownership of high-value work and avoid unnecessary professional fragmentation.

**▸ Calculation & future checkpoints**

Collapsed by default. Expanded content may contain the detailed evidence.

---

# 5. TRUE CONFLUENCE IS MANDATORY

The verdict for a life area must NOT be based on one mount, one line, one mark, or one generic rule.

The engine should combine relevant:

- line evidence
- mount evidence
- special-mark evidence
- left/right reconciliation
- feature confidence
- consistency between related indicators
- age/timing evidence
- positive signals
- conflicting signals

Conceptually:

```text
Life-area confluence
=
positive evidence
+ supporting evidence
+ timing support
+ consistency
- conflicting evidence
- uncertainty
```

The exact weights may use the existing engine, but the final verdict must demonstrably depend on multiple relevant signals.

### Example

Input:

```text
Jupiter mount = strong
Jupiter trident = strong
Jupiter grille = caution
Head line = strong
Life line = strong
Left-hand confidence = high
Right-hand confidence = moderate
Career age window = supportive
```

Expected:

```text
GOOD / SUPPORTIVE WITH PRESSURE
```

NOT:

```text
Career is good because Jupiter Trident exists.
```

---

# 6. FUTURE PERIODS MUST BE RECALCULATED

Never implement:

```text
new age window
→ automatically good
```

Instead:

```text
future checkpoint
→ recalculate relevant evidence
→ evaluate positive signals
→ evaluate conflicting signals
→ reconcile confidence
→ calculate future verdict
→ generate narrative
```

A future period may therefore remain Moderate, become Good, or become Challenging.

Example:

```text
Current: Moderate
Next window: Moderate
Later window: Good
```

is valid.

---

# 7. LLM MUST NOT INVENT REASONING

Pass Qwen structured facts.

Example:

```json
{
  "life_area": "career",
  "verdict": "good_with_pressure",
  "confidence": "moderate_high",
  "supporting_signals": [
    "strong Jupiter mount",
    "Jupiter trident",
    "clear Head line",
    "supportive Life line"
  ],
  "pressure_signals": [
    "Jupiter grille",
    "moderate right-hand image confidence"
  ],
  "timing": {
    "current": "demanding",
    "near_term": "pressure continues",
    "next_supportive_window": "age 42-45"
  },
  "future_checkpoints": [
    {
      "window": "42-45",
      "direction": "improving",
      "reason": "supportive career indicators become dominant"
    }
  ]
}
```

Qwen converts this into polished language.

Qwen must NOT:

- invent marks
- invent lines
- invent mounts
- invent dates
- invent age windows
- invent confidence
- invent future events
- upgrade low-confidence evidence
- make medical diagnoses
- make guaranteed predictions

---

# 8. DEDUPLICATION — MANDATORY

The current reports contain a serious duplicate-mark problem.

Example:

```text
Jupiter Grille
Jupiter Trident
Jupiter Grille
Jupiter Trident
```

This must never reach the final report.

Deduplicate at the **data layer**, not with CSS.

Use a stable identity such as:

```python
key = (
    hand,
    normalize(feature_type),
    normalize(mount),
    normalize(description)
)
```

If the same mark is detected multiple times, merge the evidence/confidence instead of rendering duplicates.

---

# 9. LEFT / RIGHT HAND RECONCILIATION

Always preserve hand identity.

Example:

```text
Left hand:
Jupiter Trident — Moderate confidence

Right hand:
No reliable fine mark detected

Final interpretation:
Jupiter Trident is a moderate-confidence left-hand indication.
```

Do not silently convert:

```text
Left hand only
```

into:

```text
You have a confirmed Jupiter Trident.
```

---

# 10. IMAGE QUALITY → CONFIDENCE

Image quality must affect downstream reasoning.

If the image is Fair/Poor, fine marks should be restricted.

The current Ananya sample already has the correct principle: fine marks are not reported from the right hand when the photograph is insufficient to distinguish them reliably. Preserve that behavior.

Confidence must propagate:

```text
Image quality
↓
Feature confidence
↓
Evidence confidence
↓
Life-area confidence
↓
Timing confidence
↓
LLM wording strength
```

A low-confidence feature must never produce a high-confidence customer conclusion.

---

# 11. HEALTH SAFETY

Do not produce medical diagnoses or medical-sounding certainty.

Avoid:

> You have excellent health.

> You have strong physical capacity.

> This line predicts heart problems.

Use traditional palmistry framing:

> Traditional palmistry associates this pattern with vitality and the importance of regular rest, routine and balanced habits.

No palm reading should replace medical advice.

---

# 12. NO ABSOLUTE PREDICTIONS

Avoid:

- definitely
- guaranteed
- certain
- will happen
- impossible to avoid
- you will become rich
- you will marry
- you will get promoted

Prefer:

- strongly suggests
- supports
- indicates
- may coincide with
- favourable period
- pressure phase
- improvement is indicated
- traditionally associated with

---

# 13. TIMING MUST COME FROM THE ENGINE

If no reliable future checkpoint exists, say:

> Timing cannot be established reliably from the available palm evidence.

Do not invent dates or ages.

Example structured input:

```json
{
  "future_checkpoint": {
    "age_start": 42,
    "age_end": 45,
    "direction": "improving",
    "confidence": "moderate",
    "basis": [
      "career line development",
      "supportive Jupiter indicators"
    ]
  }
}
```

Only then may Qwen write:

> The stronger career-supporting pattern becomes more prominent around ages 42–45.

---

# 14. REMEDIES

Remedies must be linked to an actual detected weakness.

Avoid generic remedies.

Bad:

> Wear gemstone X because Jupiter is weak.

Better:

> The current reading shows scattered Jupiter-area energy. Traditional palmistry guidance would emphasize focused effort, disciplined routine and avoiding unnecessary overextension.

Spiritual remedies should be clearly labelled as traditional/spiritual guidance.

---

# 15. QWEN SYSTEM PROMPT

Use a strict narrative-layer instruction:

```text
You are the narrative layer of a palmistry analysis system.

You DO NOT perform palmistry calculations.

Use ONLY the structured evidence supplied to you.

Never invent:
- marks
- lines
- mounts
- dates
- age windows
- confidence
- future events
- remedies not supplied by the system

Never upgrade uncertain evidence.

Never make medical diagnoses.

Never make guaranteed predictions.

For each life area:
1. State the supplied verdict.
2. Explain the dominant supporting evidence.
3. Explain important conflicting evidence.
4. Describe the current phase.
5. Use only supplied future checkpoints.
6. Write one concise astrologer/palmistry-style conclusion.
7. Give practical guidance derived from the supplied evidence.

If evidence is insufficient, say so.

Do not repeat technical calculations in the main paragraph.
```

---

# 16. QWEN OUTPUT CONTRACT

Require structured output:

```json
{
  "life_areas": {
    "career": {
      "verdict": "Good with pressure",
      "confidence": "Moderate",
      "conclusion": "...",
      "timing": "...",
      "what_helps": "...",
      "calculation": {
        "supporting": [],
        "conflicting": [],
        "future_checkpoints": []
      }
    }
  }
}
```

Validate this JSON before rendering.

If validation fails:

```text
Retry Qwen
OR
use deterministic fallback wording
```

Never render unvalidated LLM output directly.

---

# 17. PIPELINE

Implement the system as:

```text
PALM IMAGE
   ↓
VISION / FEATURE DETECTION
   ↓
STRUCTURED PALM EVIDENCE
   ↓
NORMALIZATION
   ↓
DEDUPLICATION
   ↓
LEFT / RIGHT RECONCILIATION
   ↓
CONFIDENCE FILTERING
   ↓
LIFE-AREA CONFLUENCE ENGINE
   ↓
CURRENT + FUTURE CHECKPOINT CALCULATION
   ↓
STRUCTURED REPORT JSON
   ↓
QWEN 2.5 7B
   ↓
LLM JSON VALIDATION
   ↓
HTML RENDERER
```

HTML must never perform reasoning.

---

# 18. COLLAPSED TECHNICAL EVIDENCE

Use:

```html
<details>
  <summary>Calculation & future checkpoints</summary>
  ...
</details>
```

Default:

```text
closed
```

Expanded content can contain:

- observed features
- hand
- confidence
- supporting evidence
- conflicting evidence
- confluence calculation
- future checkpoints
- timing basis

The normal customer should see only the conclusion.

---

# 19. AUTOMATED QA TESTS

### Test 1 — Duplicate marks

Input:

```text
Jupiter grille
Jupiter trident
Jupiter grille
Jupiter trident
```

Expected:

```text
Jupiter grille
Jupiter trident
```

### Test 2 — Fair right-hand image

Expected:

```text
No unsupported right-hand fine-mark conclusion.
```

### Test 3 — Conflicting evidence

Input:

```text
Jupiter mount = strong
Trident = strong
Grille = caution
```

Expected:

```text
Good with pressure / Mixed-positive
```

Not:

```text
Excellent
```

### Test 4 — No timing evidence

Expected:

```text
Timing cannot be established reliably from the available evidence.
```

### Test 5 — Medical wording

Expected:

```text
Traditional palmistry associates this with vitality and the importance of routine.
```

Not:

```text
You have excellent health.
```

### Test 6 — Hallucination protection

Input contains:

```text
Jupiter mount
Life line
Head line
```

and does NOT contain:

```text
Trident
```

Expected:

Qwen output must not mention a Jupiter Trident.

---

# 20. PRODUCTION ACCEPTANCE CRITERIA

The implementation is complete only when:

- [ ] No duplicate special marks
- [ ] Left/right evidence is preserved
- [ ] Confidence propagates through the pipeline
- [ ] Life-area verdicts use true confluence
- [ ] Future checkpoints are engine-derived
- [ ] Future verdicts are recalculated rather than assumed
- [ ] Qwen cannot introduce unsupported evidence
- [ ] Qwen cannot invent dates
- [ ] Qwen cannot make medical diagnoses
- [ ] No guaranteed predictions
- [ ] Main report is concise
- [ ] Technical evidence is collapsed
- [ ] Redundant sections are removed
- [ ] Remedies are evidence-linked
- [ ] Unsupported life areas explicitly say insufficient evidence
- [ ] Qwen JSON is validated before rendering
- [ ] Deterministic fallback exists
- [ ] Sample reports pass automated QA

---

# 21. FINAL CUSTOMER EXAMPLE

## Work & Career

**Good with pressure**

> Your career pattern is fundamentally supportive, but the present phase is more demanding than the long-term picture. The stronger Jupiter indications support ambition, leadership and recognition, while the grille on the same mount shows periods where effort can become scattered. The stronger Head and Life line indicators provide persistence, so the current pressure appears more like a demanding phase than a structural career weakness.

**Timing:** Current phase is demanding; improvement is indicated only in the supplied supportive window.

**What helps:** Concentrate on fewer priorities and avoid unnecessary professional fragmentation.

▸ **Calculation & future checkpoints**

[collapsed technical evidence]

---

## Money & Resources

**Moderate / Improving**

> Your financial pattern supports gradual accumulation more strongly than sudden gains. The stronger resource indicators favour disciplined earning and retention, while conflicting signs suggest that progress can become uneven when decisions are made too quickly. The overall direction is steady improvement rather than speculative windfalls.

**Timing:** Only engine-generated timing.

**What helps:** Maintain disciplined saving and avoid short-term emotional decisions.

▸ **Calculation & future checkpoints**

---

## Relationships & Emotions

**Supportive with sensitivity**

> Your relationship pattern shows a strong need for emotional security and meaningful connection, but the current evidence also indicates sensitivity to inconsistency and periods of withdrawal. The supportive indicators favour stable bonds when communication remains direct and expectations are expressed clearly.

**Timing:** Only engine-generated timing.

**What helps:** Communicate directly rather than relying on assumptions.

▸ **Calculation & future checkpoints**

---

# FINAL RULE

The customer should feel that an astrologer/palmist has interpreted the **whole pattern**, not that an LLM has generated paragraphs from isolated detected objects.

**Software calculates. Qwen explains. HTML presents.**
