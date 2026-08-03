#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Semantic + cross-encoder confluence for LaneClaim lists (75% gate)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from lane_claim import DOMAINS, LaneClaim

MIN_AGREEMENT_PCT = 0.75
MIN_SEMANTIC_SCORE = 0.40

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class DomainVerdict:
    domain: str
    direction: str
    timing: str
    lanes: list[str] = field(default_factory=list)
    claims: list[LaneClaim] = field(default_factory=list)
    headline: str = ""
    synthesis: str = ""
    lane_pct: float = 0.0
    semantic_score: float = 0.0
    meets_threshold: bool = False
    split_note: str = ""
    vote_positive: int = 0
    vote_caution: int = 0
    vote_neutral: int = 0


class LanesConfluenceEngine:
    """MiniLM embeddings + optional RoBERTa cross-encoder for claim agreement."""

    def __init__(self):
        from local_models import load_cross_encoder, load_sentence_transformer

        self.model = load_sentence_transformer()
        self.cross = load_cross_encoder()
        self._has_cross = self.cross is not None

    def semantic_agreement(self, texts: list[str]) -> float:
        uniq = list(dict.fromkeys(t.strip() for t in texts if t.strip()))[:8]
        if len(uniq) < 2:
            return 1.0
        embs = self.model.encode(uniq, normalize_embeddings=True)
        sims = [float(embs[i] @ embs[j]) for i in range(len(embs)) for j in range(i + 1, len(embs))]
        mini = float(np.mean(sims)) if sims else 0.5
        if not self._has_cross:
            return mini
        pairs = [(uniq[i], uniq[j]) for i in range(len(uniq)) for j in range(i + 1, len(uniq))][:12]
        try:
            ce = float(np.mean(self.cross.predict(pairs))) / 5.0
            ce = max(0.0, min(1.0, ce))
            return 0.45 * mini + 0.55 * ce
        except Exception:
            return mini

    def _best_snippet(self, texts: list[str], direction: str) -> str:
        if not texts:
            return ""
        anchors = {
            "positive": "growth success improvement favourable strong good peak harmony gains",
            "caution": "delay risk watch caution stress illness obstacle debt friction",
            "neutral": "life themes pattern rhythm steady mixed balance",
        }
        anchor = self.model.encode([anchors.get(direction, anchors["neutral"])], normalize_embeddings=True)[0]
        embs = self.model.encode(texts, normalize_embeddings=True)
        best_i = int(np.argmax(embs @ anchor))
        t = texts[best_i]
        if len(t) > 320:
            t = t[:317].rsplit(" ", 1)[0] + "..."
        return t

    def _split_sentences(self, text: str) -> list[str]:
        out: list[str] = []
        for part in _SENT_SPLIT.split(text or ""):
            s = part.strip()
            if len(s) >= 20 and s[-1] in ".!?":
                out.append(s)
        return out

    def _dedupe_sentences(self, texts: list[str], max_sents: int = 5) -> list[str]:
        sents: list[str] = []
        for t in texts:
            sents.extend(self._split_sentences(t))
        if not sents:
            return []
        uniq: list[str] = []
        for s in sents:
            if not uniq:
                uniq.append(s)
                continue
            em = self.model.encode([s], normalize_embeddings=True)[0]
            uem = self.model.encode(uniq, normalize_embeddings=True)
            if float(np.max(uem @ em)) < 0.84:
                uniq.append(s)
            if len(uniq) >= max_sents:
                break
        return uniq

    def _client_prose(
        self,
        lane_claims: list[LaneClaim],
        direction: str,
        vp: int,
        vc: int,
        meets: bool,
        timing: str,
        domain: str = "",
    ) -> str:
        from confluence_human import humanize_prose, humanize_sentence

        ranked = sorted(
            lane_claims,
            key=lambda c: (
                0 if c.direction == direction else (1 if c.direction == "neutral" else 2),
                -len(c.text),
            ),
        )
        max_sents = 8 if domain == "health" else 5
        raw_texts = [c.text for c in ranked]
        sents: list[str] = []
        for t in raw_texts:
            for s in self._split_sentences(t):
                hs = humanize_sentence(s)
                if hs:
                    sents.append(hs)
        if not sents:
            return ""
        uniq: list[str] = []
        for s in sents:
            if not uniq:
                uniq.append(s)
                continue
            em = self.model.encode([s], normalize_embeddings=True)[0]
            uem = self.model.encode(uniq, normalize_embeddings=True)
            if float(np.max(uem @ em)) < 0.84:
                uniq.append(s)
            if len(uniq) >= max_sents:
                break
        prose = " ".join(uniq)
        if len(prose) > 1400:
            while len(uniq) > 2 and len(" ".join(uniq)) > 1400:
                uniq.pop()
            prose = " ".join(uniq)
        prose = humanize_prose(prose, domain)
        if vc and vp and not meets:
            if direction == "caution":
                prose += " Supportive periods also appear - patience and clear agreements help."
            elif direction == "positive":
                prose += " Some seasons ask for caution before results settle fully."
            else:
                prose += " Themes clarify as the next dasha window opens."
        if timing and timing.lower() not in prose.lower():
            prose += f" Key window: {timing}."
        return prose

    def analyze(self, claims: list[LaneClaim], lanes_present: int) -> list[DomainVerdict]:
        by_domain: dict[str, list[LaneClaim]] = {d: [] for d in DOMAINS}
        for c in claims:
            if c.domain in by_domain:
                by_domain[c.domain].append(c)

        verdicts: list[DomainVerdict] = []
        for dom in DOMAINS:
            batch = by_domain[dom]
            if not batch:
                continue
            if dom == "health":
                lane_claims = batch
            else:
                by_lane: dict[str, LaneClaim] = {}
                for c in batch:
                    if c.lane not in by_lane or len(c.text) > len(by_lane[c.lane].text):
                        by_lane[c.lane] = c
                lane_claims = list(by_lane.values())
            lanes_used = sorted({c.lane for c in batch})
            vp = sum(1 for c in lane_claims if c.direction == "positive")
            vc = sum(1 for c in lane_claims if c.direction == "caution")
            vn = len(lane_claims) - vp - vc
            direction = "positive" if vp >= vc and vp >= vn else ("caution" if vc > vp else "neutral")
            agreeing = [c for c in lane_claims if c.direction == direction]
            if not agreeing:
                agreeing = lane_claims
            texts = [c.text for c in agreeing]
            sem = self.semantic_agreement(texts)
            lane_pct = len(agreeing) / max(lanes_present, 1)
            meets = lane_pct >= MIN_AGREEMENT_PCT and sem >= MIN_SEMANTIC_SCORE
            timings = [c.timing for c in lane_claims if c.timing]
            timing = max(timings, key=len) if timings else ""
            headline = self._best_snippet(texts, direction)
            synthesis = self._client_prose(lane_claims, direction, vp, vc, meets, timing, dom)
            split = ""
            if not meets:
                if vp and vc:
                    split = "mixed_signals"
                elif lane_pct < MIN_AGREEMENT_PCT:
                    split = "thin_coverage"
                else:
                    split = "wording_divergence"
            verdicts.append(DomainVerdict(
                dom, direction, timing, lanes_used, lane_claims,
                headline, synthesis, lane_pct, sem, meets, split.strip(), vp, vc, vn,
            ))
        return verdicts
