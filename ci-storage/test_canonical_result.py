"""Regression tests for the single-source canonical life-area result."""
from __future__ import annotations

from datetime import date
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASTRO = ROOT / "engines" / "astro"
for p in (str(ROOT), str(ASTRO)):
    if p not in sys.path:
        sys.path.insert(0, p)


def test_canonical_contract_shape(monkeypatch):
    import canonical_result as CR

    class FakeCF:
        @staticmethod
        def build_confluence(pc, area, house, today=None):
            return {
                "direction": "up", "score": 0.8, "confidence": "high",
                "agreement": "strong",
                "promise": {"area": area, "status": "supported", "confidence": "high", "kind": "promise"},
                "activation": {"status": "strongly_active", "confidence": "high"},
                "families": [], "secondary_confirmations": [],
            }
    monkeypatch.setitem(sys.modules, 'report_confluence', FakeCF)
    monkeypatch.setitem(sys.modules, 'area_modules', type('AM', (), {
        'manifestations_for': staticmethod(lambda *a, **k: ['role expansion'])
    }))
    monkeypatch.setitem(sys.modules, 'report_timing', type('RT', (), {
        'windows_for_area': staticmethod(lambda *a, **k: [{
            'start': date(2027,1,1), 'end': date(2027,6,1), 'aligned': True,
            'confidence': 'high', 'source': 'dasha_ashtakavarga_transit_confluence'
        }])
    }))
    monkeypatch.setitem(sys.modules, 'area_report', type('AR', (), {
        'classical_area_remedy': staticmethod(lambda *a, **k: 'Practical support')
    }))
    monkeypatch.setitem(sys.modules, 'narration.stage_actions', type('SA', (), {
        'action_for_stage': staticmethod(lambda *a, **k: 'Show your work')
    }))

    r = CR.build_area_result({}, 'career', 10, today=date(2026, 8, 11))
    assert r['promise']['status'] == 'supported'
    assert r['activation']['status'] == 'strongly_active'
    assert 'timing' in r and 'manifestation' in r
    assert 'action' in r and 'remedy' in r and 'why' in r
    assert r['timing']['timing_can_create_promise'] is False


def test_mixed_promise_is_not_strong_event_window():
    import canonical_result as CR
    promise = {"area": "career", "status": "mixed", "confidence": "moderate", "kind": "promise"}
    windows = [{
        'start': date(2027,1,1), 'end': date(2027,6,1), 'aligned': True,
        'confidence': 'high', 'source': 'dasha_ashtakavarga_transit_confluence'
    }]
    t = CR._timing_summary(windows, promise)
    assert t['strong_windows'] == []
    assert len(t['opportunity_windows']) == 1
    assert t['timing_can_create_promise'] is False
