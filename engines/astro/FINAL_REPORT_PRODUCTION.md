# Graharekha final production report contract

The customer-facing paid report is intentionally limited to:

1. Chart Signature
2. Where You Are Now
3. Each Life Area
   - Verdict
   - One astrologer-style conclusion
   - Timing
   - What helps
   - Astrological calculation & future checkpoints (collapsed)
4. Final Practical Guidance

The deterministic astrology engine remains authoritative. Qwen writes only the
consultation prose from supplied facts.

Important invariants:
- A dasha change never equals improvement by itself.
- Every future checkpoint recalculates complete life-area confluence.
- Current Vimshottari dates come from the analytical timing object.
- Vimshottari is an approved customer-facing term.
- Raw scores, debug fields and analyst-only wording are not rendered.
- Legacy life-area mini-sections are not rendered.
- If Qwen fails to provide a conclusion, a deterministic safe fallback is used;
  the old redundant narrative renderer is never resurrected.
