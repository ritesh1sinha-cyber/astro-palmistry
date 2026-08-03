#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hybrid semantic confluence: MiniLM domain routing + cross-encoder agreement."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from vedic_confluence_report import Signal

MIN_AGREEMENT_PCT = 0.75
MIN_SEMANTIC_SCORE = 0.42


@dataclass
class EnrichedCluster:
    domain: str
    direction: str
    timing: str
    systems: list[str] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    affirmation: str = ""
    confidence: str = "SPECULATIVE"
    score: float = 0.0
    lane_pct: float = 0.0
    semantic_score: float = 0.0
    meets_threshold: bool = False
    split_note: str = ""


class HybridSemanticEngine:
    """MiniLM (sentence-BERT family) + cross-encoder for pairwise claim agreement."""

    def __init__(self, book_lines: dict, theme_anchors: dict, conf_label_fn):
        from local_models import load_cross_encoder, load_sentence_transformer

        self.model = load_sentence_transformer()
        self.cross = load_cross_encoder()
        self._has_cross = self.cross is not None
        self.book_lines = book_lines
        self.theme_anchors = theme_anchors
        self._conf_label = conf_label_fn
        self._anchor_emb: dict[str, np.ndarray] = {}
        self._book_emb: dict[tuple[str, str, int], np.ndarray] = {}
        for dom, anchors in theme_anchors.items():
            self._anchor_emb[dom] = self.model.encode(anchors, normalize_embeddings=True)
        for dom, dirs in book_lines.items():
            for direction, lines in dirs.items():
                for i, line in enumerate(lines):
                    self._book_emb[(dom, direction, i)] = self.model.encode([line], normalize_embeddings=True)[0]

    def assign_domain(self, text: str) -> str:
        emb = self.model.encode([text], normalize_embeddings=True)[0]
        best_dom, best_sc = "career", -1.0
        for dom, amat in self._anchor_emb.items():
            sc = float(np.max(amat @ emb))
            if sc > best_sc:
                best_sc, best_dom = sc, dom
        return best_dom

    def semantic_agreement(self, texts: list[str]) -> float:
        if len(texts) < 2:
            return 1.0
        uniq = list(dict.fromkeys(t.strip() for t in texts if t.strip()))[:8]
        if len(uniq) < 2:
            return 1.0
        embs = self.model.encode(uniq, normalize_embeddings=True)
        sims = []
        for i in range(len(embs)):
            for j in range(i + 1, len(embs)):
                sims.append(float(embs[i] @ embs[j]))
        mini = float(np.mean(sims)) if sims else 0.5
        if not self._has_cross or self.cross is None:
            return mini
        pairs = [(uniq[i], uniq[j]) for i in range(len(uniq)) for j in range(i + 1, len(uniq))][:15]
        try:
            ce = self.cross.predict(pairs)
            ce_norm = float(np.mean(ce)) / 5.0
            ce_norm = max(0.0, min(1.0, ce_norm))
            return 0.45 * mini + 0.55 * ce_norm
        except Exception:
            return mini

    def _pick_line(self, domain: str, direction: str, centroid: np.ndarray) -> str:
        if domain == "current" and direction in ("neutral", "caution"):
            return self.book_lines["current"]["positive"][0]
        candidates = self.book_lines.get(domain, self.book_lines["career"])
        lines = candidates.get(direction) or candidates.get("neutral") or list(candidates.values())[0]
        best_line, best_sc = lines[0], -1.0
        for i, line in enumerate(lines):
            key = (domain, direction, i)
            if key not in self._book_emb:
                self._book_emb[key] = self.model.encode([line], normalize_embeddings=True)[0]
            sc = float(self._book_emb[key] @ centroid)
            if sc > best_sc:
                best_sc, best_line = sc, line
        return best_line

    def cluster_signals(
        self,
        signals: list["Signal"],
        domains: tuple[str, ...],
        lanes_present: int,
        threshold: float = 0.52,
    ) -> list[EnrichedCluster]:
        for sig in signals:
            if sig.domain == "unknown":
                sig.domain = self.assign_domain(sig.text)
        if not signals:
            return []
        embs = self.model.encode([x.text for x in signals], normalize_embeddings=True)
        out: list[EnrichedCluster] = []

        for dom in domains:
            idxs = [i for i, s in enumerate(signals) if s.domain == dom]
            if not idxs:
                continue
            members = [signals[i] for i in idxs]
            systems = sorted({m.system for m in members})
            pos = sum(1 for m in members if m.direction == "positive")
            cau = sum(1 for m in members if m.direction == "caution")
            direction = "positive" if pos >= cau else ("caution" if cau > pos else "neutral")
            pos_systems = sorted({m.system for m in members if m.direction == "positive"})
            cau_systems = sorted({m.system for m in members if m.direction == "caution"})
            if direction == "positive" and cau_systems and len(cau_systems) >= len(pos_systems):
                direction = "caution" if cau > pos else "neutral"
            timings = [m.timing for m in members if m.timing]
            timing = max(timings, key=len) if timings else ""
            texts = [m.text for m in members]
            centroid = np.mean(embs[idxs], axis=0)
            centroid = centroid / (np.linalg.norm(centroid) + 1e-9)
            sem = self.semantic_agreement(texts)
            lane_pct = len(systems) / max(lanes_present, 1)
            meets = lane_pct >= MIN_AGREEMENT_PCT and sem >= MIN_SEMANTIC_SCORE
            split = ""
            if not meets:
                if lane_pct < MIN_AGREEMENT_PCT:
                    split = f"Only {len(systems)} of {lanes_present} methods lean the same way ({lane_pct:.0%}) � below the 75% bar for a headline call."
                elif sem < MIN_SEMANTIC_SCORE:
                    split = f"Methods mention {dom} but wording diverges (semantic match {sem:.0%}) � treat as mixed signal."
                if cau_systems and pos_systems:
                    split += f" Positive: {', '.join(pos_systems[:4])}. Caution: {', '.join(cau_systems[:3])}."
            out.append(EnrichedCluster(
                dom, direction, timing, systems, texts[:6],
                self._pick_line(dom, direction, centroid),
                self._conf_label(len(systems)), float(len(systems)),
                lane_pct, sem, meets, split.strip(),
            ))
        return out
