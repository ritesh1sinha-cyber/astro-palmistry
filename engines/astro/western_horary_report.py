#!/usr/bin/env python3
"""Deterministic Western horary report generator — no LLM.

Casts the Tropical Placidus chart (``western_horary_precompute``), applies the
Lilly/Louis judgment engine (``western_horary_rules``), and renders an HTML
report in the audited ``reports/WesternHorary_template.html`` format with the
mandatory Louis Chapter-2 checklist, perfection analysis, ephemeris timing and a
book precedent from ``western-horary-data/rules_v6.json``.

Usage:
    python3 western_horary_report.py "Will I get the bonus?" 2026-04-10 01:20 Hyderabad \
        --quesited-house 10 --out reports/WesternHorary_Bonus_20260410.html
"""
from __future__ import annotations

import argparse
import re
from datetime import date
from html import escape

from western_horary_precompute import precompute_western, lon_in_placidus_house
import western_horary_rules as R

DEG = "\u00b0"


def fmt_deg(lon: float) -> str:
    d = R.deg_in_sign(lon)
    whole = int(d)
    minutes = int(round((d - whole) * 60))
    if minutes == 60:
        whole += 1
        minutes = 0
    return f"{whole}{DEG}{minutes:02d}\u2032"


def choose_quesited_house(question: str, override: int | None) -> int:
    if override:
        return override
    return R.parse_question(question)["house"]


def judge(data: dict, question: str, quesited_house: int) -> dict:
    angles = data["angles"]
    cusps = data["cusps"]
    planets = data["planets"]
    is_day = data["meta"].get("chart_type") == "day"
    jd = data["meta"]["julian_day_ut"]

    asc_sign = angles["asc_sign"]
    asc_lord = R.DOMICILE[R.SIGN_IDX[asc_sign]]
    q_sign = R.sign_of(cusps[quesited_house - 1])
    q_lord = R.DOMICILE[R.SIGN_IDX[q_sign]]
    same_lord = asc_lord == q_lord

    # Moon is co-ruler of the querent unless it is itself a significator.
    moon_is_sig = "Moon" in (asc_lord, q_lord)

    def ed(name):
        return R.essential_dignities(name, planets[name]["longitude"], is_day)

    asc_ed = ed(asc_lord)
    q_ed = ed(q_lord)
    moon_ed = ed("Moon")

    # Perfection between querent & quesited significators.
    perfection = None
    recept_a = recept_b = []
    if asc_lord != q_lord:
        perfection = R.aspect_between(planets[asc_lord], planets[q_lord], (asc_lord, q_lord))
        recept_a = R.reception(planets[q_lord]["longitude"], 0, q_lord, asc_lord, is_day)
        recept_b = R.reception(planets[asc_lord]["longitude"], 0, asc_lord, q_lord, is_day)

    # Louis 11th-house "hope" rule.
    h11_sign = R.sign_of(cusps[10])
    h11_lord = R.DOMICILE[R.SIGN_IDX[h11_sign]]
    hope_aspect = (R.aspect_between(planets[asc_lord], planets[h11_lord], (asc_lord, h11_lord))
                   if asc_lord != h11_lord else None)

    # Moon condition.
    moon_void, moon_void_note = R.moon_void_of_course(jd)
    moon_lon = planets["Moon"]["longitude"]
    via_combusta = 195.0 <= moon_lon < 225.0
    sun_lon = planets["Sun"]["longitude"]
    moon_last, moon_next = R.moon_aspects(planets)

    # Combustion of significators / Moon.
    combust = []
    for nm in (asc_lord, q_lord, "Moon"):
        if nm == "Sun":
            continue
        d = R.ang_sep(planets[nm]["longitude"], sun_lon)
        if d < 8.5:  # proper combustion (within ~8.5°); 8.5–17° is merely "under the Sun's beams"
            combust.append((nm, round(d, 1)))

    # Considerations.
    asc_deg = angles["asc_deg_in_sign"]
    early_asc = asc_deg < 3.0
    late_asc = asc_deg > 27.0
    sat_house = lon_in_placidus_house(planets["Saturn"]["longitude"], cusps)
    plu_house = lon_in_placidus_house(planets["Pluto"]["longitude"], cusps)

    # Pars Fortuna (day: Asc + Moon − Sun; night: Asc + Sun − Moon).
    asc = angles["ascendant_deg"]
    pf_lon = R.norm360(asc + (moon_lon - sun_lon if is_day else sun_lon - moon_lon))
    pf_house = lon_in_placidus_house(pf_lon, cusps)

    # Reception, translation, collection of light, question mode.
    same_lord = asc_lord == q_lord
    mr = None if same_lord else R.mutual_reception(planets, asc_lord, q_lord, is_day)
    transl = None if same_lord else R.translation_of_light(planets, asc_lord, q_lord)
    collect = None if same_lord else R.collection_of_light(planets, asc_lord, q_lord)
    lost_mode = R.is_lost_question(question)
    return_mode = R.is_return_question(question)
    parsed_q = R.parse_question(question)
    when_mode = parsed_q["when"]
    amount_mode = bool(parsed_q.get("amount"))
    combust_names = {nm for nm, _ in combust}
    q_lord_house = planets[q_lord]["house"]
    opp_only = bool(perfection and perfection["applying"] and perfection["aspect"] == "opposition")

    # Minor (awkward) aspect between significators — not perfection, just a weak link.
    minor_link = None if same_lord else R.minor_aspect_between(planets[asc_lord], planets[q_lord])
    # Mutual application (one direct, one retrograde, both applying) — a potent contact.
    mutual_app = bool(perfection and perfection.get("mutual_application"))
    # A significator (or the Moon) applying to the Ascendant brings the matter/person to
    # the querent (Louis: "Venus applying to conjoin the Ascendant ... we will be reunited").
    asc_lon = angles["ascendant_deg"]
    sig_to_asc = None
    for nm in ([q_lord] if not same_lord else []) + (["Moon"] if not moon_is_sig else []):
        a = R.applies_to_angle(planets[nm], asc_lon)
        if a and a["applying"]:
            sig_to_asc = nm
            break
    # Almuten of the quesited-house cusp (covers intercepted / co-ruled houses).
    q_almuten = R.almuten_at(cusps[quesited_house - 1], is_day)

    # Multi-significator: besides the domicile ruler, the matter is also signified by the
    # almuten of its cusp and by any planet posited in the house. Louis routinely judges
    # through these co-significators when the domicile ruler is weak or makes no aspect.
    q_co_sigs: list[str] = []
    for nm in [q_almuten] + [p for p in planets if planets[p]["house"] == quesited_house]:
        if nm not in q_co_sigs and nm not in (q_lord, asc_lord):
            q_co_sigs.append(nm)
    # Does a secondary significator of the matter apply to the querent (Asc lord or Moon)?
    co_perfection = None
    for nm in q_co_sigs:
        for target in ([asc_lord] if not same_lord else []) + (["Moon"] if not moon_is_sig else []):
            if nm == target:
                continue
            a = R.aspect_between(planets[target], planets[nm], (target, nm))
            if a and a["applying"] and a["aspect"] in ("trine", "sextile", "conjunction"):
                co_perfection = (nm, target, a)
                break
        if co_perfection:
            break

    # In a lost/return question, a planet posited in the quesited house that applies to a
    # querent body is the object's own co-significator carrying it back (Louis, Chart 21:
    # "Mars mutually applying to a trine of Saturn" = the red cat returning). Such a planet is
    # the object itself, not an "obstacle" in the house, so we identify it once here.
    obj_cosig = None
    obj_cosig_mutual = False
    if lost_mode or return_mode:
        querent_bodies0 = [asc_lord, "Moon"] + [p for p in planets if planets[p]["house"] == 1]
        for nm in [p for p in planets if planets[p]["house"] == quesited_house and p not in (asc_lord, q_lord)]:
            for tgt in querent_bodies0:
                if tgt == nm:
                    continue
                a = R.aspect_between(planets[nm], planets[tgt], (nm, tgt))
                if a and a["applying"] and a["aspect"] in ("trine", "sextile", "conjunction"):
                    obj_cosig, obj_cosig_mutual = nm, bool(a.get("mutual_application"))
                    break
            if obj_cosig:
                break

    # Any traditional mode of perfection present? (Louis: void is far less damning if the
    # matter still perfects by aspect, reception, translation, or collection.)
    perfection_present = (
        same_lord
        or (perfection and perfection["applying"] and (
            perfection["aspect"] in ("trine", "sextile", "conjunction")
            or (perfection["aspect"] == "square" and mr in ("strong", "minor"))))
        or bool(transl) or bool(collect) or bool(sig_to_asc)
        or (bool(co_perfection) and (lost_mode or return_mode))
        or (moon_next and moon_next["planet"] == q_lord
            and moon_next["aspect"] in ("trine", "sextile", "conjunction"))
    )

    # ---- Testimony tally → verdict (Lilly/Louis weighting) ----
    score = 0.0
    reasons: list[str] = []

    # 1. Perfection by direct aspect between the significators.
    if same_lord:
        score += 1.6
        reasons.append(f"one planet ({asc_lord}) rules both querent and quesited — the matter is naturally linked (perfection within one significator)")
    elif perfection and perfection["applying"]:
        asp = perfection["aspect"]
        if asp in ("trine", "sextile"):
            score += 2.0
            reasons.append(f"the significators apply by a favourable {asp} — clean perfection")
        elif asp == "conjunction":
            score += 1.8
            reasons.append("the significators apply to conjunction — the matter comes together")
        elif asp == "square":
            if mr in ("strong", "minor"):
                score += 0.6
                reasons.append("the significators apply by square but with mutual reception — yes, through effort and friction")
            else:
                score -= 1.0
                reasons.append("the significators apply by square without reception — a hostile contact that tends to deny")
        else:  # opposition
            score -= 0.9
            reasons.append("the significators apply by opposition — even if it completes, tradition warns of loss/regret; it tends to deny")
    elif perfection and not perfection["applying"]:
        score -= 0.8
        reasons.append(f"their {perfection['aspect']} is separating — the moment has likely passed")
    else:
        score -= 0.6
        reasons.append("the significators make no direct applying major aspect — no clean perfection")
        # Louis: a connection by minor aspect only (semi-sextile/quincunx) is awkward and
        # confirms a qualified/negative reading, not a marriage or completion.
        if minor_link:
            score -= 0.3
            reasons.append(f"they link only by an awkward {minor_link['aspect']} — a weak, non-perfecting contact")

    # Mutual application (direct + retrograde applying) strengthens a real perfection.
    if mutual_app and perfection and perfection["aspect"] in ("trine", "sextile", "conjunction"):
        score += 0.6
        reasons.append("the significators are in mutual application (one direct, one retrograde) — a potent force bringing the matter to pass")

    # 1b. Perfection through a secondary significator of the matter (the almuten of the cusp
    # or a planet posited in the house) when the domicile ruler itself makes no clean aspect.
    direct_perfected = same_lord or bool(
        perfection and perfection["applying"]
        and perfection["aspect"] in ("trine", "sextile", "conjunction"))
    hard_main_aspect = bool(
        perfection and perfection["applying"]
        and perfection["aspect"] in ("square", "opposition"))
    # Co-significator perfection is a recovery/return testimony (Louis judges lost objects and
    # returns through the almuten or in-house planet). It must not override a clear denial
    # between the actual significators, nor manufacture a yes for an ordinary yes/no question.
    if co_perfection and not direct_perfected and (lost_mode or return_mode) and not hard_main_aspect:
        co_nm, co_target, co_a = co_perfection
        w = 1.4 if co_a.get("mutual_application") else 1.2
        score += w
        reasons.append(f"a secondary significator of the matter ({co_nm} — almuten or occupant of the quesited house) applies by {co_a['aspect']} to {co_target} — the matter perfects through this co-significator")

    # 2. Translation / collection of light (a third body perfects the matter). Secondary to
    # a direct aspect, so weighted below it and unable to override a strong denial.
    if not same_lord:
        if transl:
            score += 1.1
            reasons.append(f"{transl} translates the light between {asc_lord} and {q_lord} — a third party or flow helps bring the matter together")
        elif collect:
            score += 0.9
            reasons.append(f"{collect} collects the light of both significators — the matter is gathered to a conclusion")

    # A significator (or the Moon) applying to the Ascendant brings the matter to the querent.
    if sig_to_asc:
        score += 0.7
        reasons.append(f"{sig_to_asc} applies to the Ascendant — the matter (or person) comes to the querent")

    # 3. Reception between the significators (tainted when the only contact is an opposition).
    rec_factor = 0.0 if opp_only else 1.0
    if mr == "strong":
        score += 1.0 * rec_factor
        if rec_factor:
            reasons.append("there is strong mutual reception (by sign or exaltation) — the parties genuinely favour each other")
        else:
            reasons.append("there is mutual reception, but only across an opposition — desire mixed with conflict, not a clean yes")
    elif mr == "minor":
        score += 0.4 * rec_factor
        if rec_factor:
            reasons.append("there is mutual reception by minor dignity — mild goodwill on both sides")
    elif mr == "oneway":
        score += 0.25 * rec_factor
        if rec_factor:
            reasons.append("there is one-way reception — partial goodwill")

    # 4. Louis's 11th-house hope testimony.
    if hope_aspect and hope_aspect["applying"] and hope_aspect["aspect"] in ("trine", "sextile", "conjunction"):
        score += 0.5
        reasons.append("the Ascendant lord links favourably to the 11th lord (Louis's hope testimony)")

    # 5. Moon condition. Void of course is modulated by the Moon's sign (Lilly/Bonatus):
    # in Taurus/Cancer/Sagittarius/Pisces she "still performs"; in Gemini/Scorpio/
    # Capricorn it is especially negative; and for lost objects/persons it often means
    # the thing returns. Void is also far less damning if the matter perfects another way.
    moon_sign = planets["Moon"]["sign"]
    moon_combust = "Moon" in combust_names
    if moon_void:
        if lost_mode:
            score -= 0.1
            reasons.append("the Moon is void of course — for a lost object or person this often means it returns of its own accord")
        elif moon_sign in R.VOID_PERFORMS_SIGNS and not moon_combust:
            score -= 0.2
            reasons.append(f"the Moon is void of course but in {moon_sign}, where Lilly says she still performs — the matter can still come about")
        elif moon_sign in R.VOID_WORSE_SIGNS:
            score -= 1.6
            reasons.append(f"the Moon is void of course in {moon_sign} — an especially negative testimony; the matter tends to come to nothing")
        elif perfection_present:
            score -= 0.5
            reasons.append("the Moon is void of course, but mitigated since the matter perfects another way")
        else:
            score -= 1.2
            reasons.append("the Moon is void of course — often \u201cnothing comes of the matter,\u201d or marked delay")
    else:
        score += 0.3
        reasons.append("the Moon is not void — the matter is active")

    # Moon in mutual reception with a significator supports a favourable outcome (Louis, Chart 20).
    if not moon_void or moon_sign in R.VOID_PERFORMS_SIGNS:
        for sig in (asc_lord, q_lord):
            if sig != "Moon" and R.mutual_reception(planets, "Moon", sig, is_day) in ("strong", "minor"):
                score += 0.4
                reasons.append(f"the Moon is in mutual reception with {sig} — this supports a favourable outcome")
                break
    # (skip if the Moon is already credited as the translator — same testimony)
    if moon_next and moon_next["planet"] == q_lord and not same_lord and transl != "Moon":
        if moon_next["aspect"] in ("trine", "sextile", "conjunction"):
            score += 0.8
            reasons.append(f"the Moon applies to the quesited lord {q_lord} — it carries the matter to completion")
        else:
            score += 0.2
    if via_combusta:
        score -= 0.4
        reasons.append("the Moon is in the Via Combusta (stress/instability colour)")

    # 6. Combustion of a main significator (severe — but context-dependent).
    if q_lord in combust_names:
        if lost_mode:
            score -= 0.3
            reasons.append(f"the quesited lord {q_lord} is combust — the object is hidden, near a source of heat or light, but still recoverable")
        elif when_mode:
            score -= 0.5
            reasons.append(f"the quesited lord {q_lord} is combust — delay and obscurity, but the event still ripens")
        else:
            score -= 1.3
            reasons.append(f"the quesited lord {q_lord} is combust the Sun — the matter is hidden, weakened, or denied")
    if asc_lord in combust_names:
        # A combust querent does not prevent a lost object from being found.
        score -= 0.2 if lost_mode else 0.6
        reasons.append(f"the querent's lord {asc_lord} is combust the Sun — the querent is weakened in the matter")
    if "Moon" in combust_names and "Moon" not in (asc_lord, q_lord) and not lost_mode:
        score -= 0.3
        reasons.append("the Moon is combust the Sun — a weak flow of events")

    # 7. Retrograde quesited significator.
    if not same_lord and planets[q_lord].get("retrograde"):
        if return_mode or lost_mode:
            score += 0.7
            reasons.append(f"the quesited significator {q_lord} is retrograde — for a return/recovery this argues the thing comes back")
        else:
            score -= 0.5
            reasons.append(f"the quesited significator {q_lord} is retrograde — instability or reversal in the matter")

    # A denying hard aspect (square/opposition without reception) is an obstacle that a
    # mere house-occupant benefic cannot overrule (Louis, Chart 53: squares = obstacles).
    hard_denial = bool(perfection and perfection["applying"]
                       and perfection["aspect"] in ("square", "opposition")
                       and mr not in ("strong", "minor"))

    # 8. Benefic / malefic occupying the house of the matter.
    for nm in [p for p in planets if planets[p]["house"] == quesited_house]:
        e = ed(nm)
        if nm in R.BENEFIC and not hard_denial:
            if e["score"] >= 4:
                score += 0.5
                reasons.append(f"{nm} (a benefic) is dignified in the house of the matter ({', '.join(e['dignities'])}) — a promise for the topic")
            else:
                score += 0.25
                reasons.append(f"{nm} (a benefic) sits in the house of the matter — a helping hand on the topic")
        elif nm in R.MALEFIC and nm != obj_cosig:
            if e["score"] <= -4:
                score -= 0.5
                reasons.append(f"{nm} (a malefic) is debilitated in the house of the matter ({', '.join(e['debilities'])}) — an obstacle on the topic")
            elif e["score"] < 4:
                score -= 0.25
                reasons.append(f"{nm} (a malefic) sits in the house of the matter — friction/delay on the topic")

    # 9. Natural significator of the topic.
    for nat in R.NATURAL_SIGNIFICATOR.get(quesited_house, []):
        if nat in (asc_lord, q_lord):
            continue
        e = ed(nat)
        if e["score"] >= 4:
            score += 0.3
            reasons.append(f"the natural significator {nat} is dignified ({', '.join(e['dignities'])}) — it favours the topic")
        elif e["score"] <= -4 and nat != obj_cosig:
            # In a recovery question the natural significator may BE the object carrying itself
            # back; don't penalise its debility as a drag in that case.
            score -= 0.3
            reasons.append(f"the natural significator {nat} is weak ({', '.join(e['debilities'])}) — a drag on the topic")
        break

    # 10. Essential dignity of the significators reinforces an existing perfection (it shows
    # the parties able and willing), but strong dignity with NO contact does not create a yes.
    if perfection_present:
        for nm, e in ((asc_lord, asc_ed), (q_lord, q_ed)):
            if e["score"] >= 5:
                score += 0.3
            elif e["score"] <= -5:
                score -= 0.3
    else:
        # With no perfection, only debility counts (a weak party further drags the matter).
        for nm, e in ((asc_lord, asc_ed), (q_lord, q_ed)):
            if e["score"] <= -5:
                score -= 0.3

    # 10b. Both significators severely debilitated — neither party has the strength or
    # will to bring the matter about (Lilly: weak significators rarely act).
    if (not same_lord and asc_ed["score"] <= -4 and q_ed["score"] <= -4
            and not lost_mode and not (transl or collect)):
        # Weak significators cannot carry the matter — UNLESS a third party translates or
        # collects their light and carries it for them (Louis, Chart 20: the Moon in Pisces
        # translates light between debilitated Mercury and Venus, and the loan still perfects).
        score -= 1.0
        reasons.append(f"both significators ({asc_lord} and {q_lord}) are debilitated — neither party is strong enough to carry the matter through")

    # 11. Lost-object recovery (Louis Ch. 12 / Lilly). Recovery is shown by: the Moon or the
    # querent's ruler applying to the object's significator (reunion); a retrograde object
    # significator (it "comes back"); and the significator's house — angular = easy to find,
    # succedent = harder, cadent = concealed/difficult but usually still found.
    if lost_mode:
        recovery = 0.0
        # Moon or querent's ruler applying to the object's significator → reunion. Louis uses
        # the Moon applying to the object's ruler anywhere in its course (kitten: "the Moon is
        # applying to conjoin Saturn in nine degrees"), not only its very next aspect.
        moon_obj = (R.aspect_between(planets["Moon"], planets[q_lord], ("Moon", q_lord))
                    if q_lord != "Moon" else None)
        moon_to_obj = (moon_next and moon_next["planet"] == q_lord) or bool(moon_obj and moon_obj["applying"])
        querent_to_obj = perfection and perfection["applying"]
        if moon_to_obj or querent_to_obj:
            recovery += 1.0
            reasons.append("the Moon or the querent's ruler applies to the object's significator — querent and object are reunited (recovery)")
        # The object's significator applying to the Ascendant brings it to the querent.
        if sig_to_asc:
            recovery += 0.6
            reasons.append(f"{sig_to_asc} applies to the Ascendant — the object/person comes to the querent")
        # Retrograde significator of the object → it comes back (Louis, p. 287).
        if planets[q_lord].get("retrograde"):
            recovery += 0.6
            reasons.append(f"the object's significator {q_lord} is retrograde — the lost object usually comes back or returns")
        # Findability by the significator's house.
        if q_lord_house in (1, 4, 7, 10):
            recovery += 0.7
            reasons.append(f"the object's significator {q_lord} is angular (house {q_lord_house}) — the item is near and easy to find")
        elif q_lord_house in (2, 5, 8, 11):
            recovery += 0.3
            reasons.append(f"the object's significator {q_lord} is succedent (house {q_lord_house}) — recoverable, but harder and slower to find")
        else:
            recovery += 0.1
            reasons.append(f"the object's significator {q_lord} is cadent (house {q_lord_house}) — concealed and difficult, but usually still found in time")
        # Co-significators: planets occupying the quesited house also describe/signify the
        # object (e.g. Mars describing a red cat). If such a co-significator applies — and
        # especially by mutual application — to the querent's ruler or the Moon, the object
        # is brought back (Louis, Chart 21: "Mars mutually applying to a trine of Saturn").
        if obj_cosig:
            recovery += 0.7 if obj_cosig_mutual else 0.5
            reasons.append(f"a co-significator of the object ({obj_cosig}) in the house applies to the querent — it is brought back")
        # The 4th house is the home and the terminus ("end") of the matter. The Moon or the
        # missing party's significator there shows the person/thing is at home or returns home
        # (Louis, Tommy/Chart 40: the Moon in the 4th with retrograde planets = he comes home).
        home_sig = next((nm for nm in ("Moon", q_lord)
                         if nm != asc_lord and planets[nm]["house"] == 4), None)
        if home_sig:
            retro_in_4th = any(planets[p]["house"] == 4 and planets[p].get("retrograde")
                               for p in planets)
            recovery += 0.5 if retro_in_4th else 0.3
            tail = " conjunct retrograde planets (it returns home)" if retro_in_4th else " (it is at home)"
            reasons.append(f"{home_sig} is in the 4th house, the home and end of the matter{tail}")
        # A gravely afflicted significator (combust and cadent) can deny recovery.
        if q_lord in combust_names and q_lord_house in (3, 6, 9, 12) and not (moon_to_obj or querent_to_obj):
            recovery -= 1.2
            reasons.append(f"the object's significator {q_lord} is combust and cadent with no applying contact — recovery looks doubtful")
        score += recovery

    # 11b. "When will…" questions presume the event occurs; they ask timing, not whether.
    if when_mode and not lost_mode:
        score += 1.0
        reasons.append("the question asks *when*, not *if* — the event is presumed to occur; the timing is given below")

    # 11c. "How much…" questions ask magnitude, not a binary yes/no.
    if amount_mode and not lost_mode:
        score += 0.35
        reasons.append(
            "the question asks *how much / what size*, not a flat yes or no — "
            "tradition can lean high or modest but cannot name an exact figure"
        )

    # 12. Fertility for conception/childbearing questions only (5th house).
    if quesited_house == 5 and any(k in question.lower() for k in
                                   ("have children", "ever have children", "pregnan", "conceive", "baby", "fall pregnant")):
        q5_sign = R.sign_of(cusps[4])
        l5_sign = planets[q_lord]["sign"]
        if q5_sign in R.BARREN_SIGNS or l5_sign in R.BARREN_SIGNS:
            score -= 0.7
            reasons.append("a barren sign rules / holds the house of children — tradition argues against offspring")
        elif q5_sign in R.FRUITFUL_SIGNS or l5_sign in R.FRUITFUL_SIGNS:
            score += 0.4
            reasons.append("a fruitful sign rules / holds the house of children — supports offspring")

    # 13. Considerations before judgment (Lilly/Bonatus). These warn that the chart is not
    # safe to judge or that the question is premature/insincere — a genuine negative weight.
    # The early/late-ascendant cautions concern the ripeness of a yes/no decision; they do not
    # deny a location ("where is…") or timing ("when…") question, so skip them in those modes.
    ripeness_modes = lost_mode or return_mode or when_mode or amount_mode
    if early_asc and not ripeness_modes:
        score -= 0.6
        reasons.append("an early degree rises (under 3°) — by Bonatus a premature or insincere question; the matter is not ripe")
    if late_asc and not ripeness_modes:
        score -= 0.5
        reasons.append("a late degree rises (over 27°) — the matter is too far along or already decided; little can change it")
    if sat_house == 7 and asc_lord != "Saturn" and q_lord != "Saturn":
        score -= 0.3
        reasons.append("Saturn is in the 7th — the classic warning of difficulty or a flawed judgment")

    if amount_mode and not lost_mode:
        # Magnitude language — never a bare Yes/No for "how much hike"
        if score >= 1.5:
            verdict, conf = "Larger increase favoured", "good"
        elif score >= 0.6:
            verdict, conf = "Modest increase favoured", "moderate"
        elif score > -0.6:
            verdict, conf = "Size unclear / qualified", "low"
        elif score > -1.5:
            verdict, conf = "Increase looks limited", "moderate"
        else:
            verdict, conf = "Little room for a hike", "good"
    elif score >= 1.5:
        verdict, conf = "Yes", "good"
    elif score >= 0.6:
        verdict, conf = "Likely yes", "moderate"
    elif score > -0.6:
        verdict, conf = "Uncertain / qualified", "low"
    elif score > -1.5:
        verdict, conf = "Unlikely", "moderate"
    else:
        verdict, conf = "No", "good"

    # Timing windows.
    timing = []
    if perfection and perfection["applying"] and asc_lord != q_lord:
        pdate = R.perfection_date(jd, asc_lord, q_lord, perfection["angle"])
        if pdate:
            timing.append((pdate, f"{asc_lord}\u2013{q_lord} {perfection['aspect']} perfects",
                           f"the querent's and quesited's significators complete their {perfection['aspect']} "
                           f"\u2014 the symbolic moment the matter \u201ccomes together.\u201d"))
    if moon_next:
        pdate = R.perfection_date(jd, "Moon", moon_next["planet"], moon_next["angle"], max_days=30)
        if pdate:
            timing.append((pdate, f"Moon {moon_next['aspect']} {moon_next['planet']}",
                           "the Moon (the flow of events) completes its next contact \u2014 a near-term "
                           "nudge in the story."))
    ing = R.ingress_date(jd, "Jupiter")
    if ing:
        timing.append((ing[0], f"Jupiter enters {ing[1]}",
                       "the general benefic shifts sign \u2014 a broader change of chapter around the matter."))
    timing.sort(key=lambda t: t[0])

    conditions = set()
    if any(planets[p].get("retrograde") for p in planets):
        conditions.add("retrograde")
    if moon_void:
        conditions.add("void")
    if combust:
        conditions.add("combust")
    if via_combusta:
        conditions.add("moon_in_via_combusta")
    if sat_house == 7:
        conditions.add("saturn_in_7th")
    if early_asc:
        conditions.add("early_asc")
    result_lean = "YES" if score >= 0.6 else ("NO" if score <= -0.6 else "MIXED")
    precedent = R.match_book_case(conditions, result_lean)

    return {
        "is_day": is_day, "asc_sign": asc_sign, "asc_lord": asc_lord, "asc_ed": asc_ed,
        "asc_deg": asc_deg, "early_asc": early_asc, "late_asc": late_asc,
        "quesited_house": quesited_house, "q_sign": q_sign, "q_lord": q_lord, "q_ed": q_ed,
        "same_lord": same_lord, "moon_is_sig": moon_is_sig, "moon_ed": moon_ed,
        "perfection": perfection, "recept_a": recept_a, "recept_b": recept_b,
        "h11_sign": h11_sign, "h11_lord": h11_lord, "hope_aspect": hope_aspect,
        "moon_void": moon_void, "moon_void_note": moon_void_note,
        "via_combusta": via_combusta, "moon_last": moon_last, "moon_next": moon_next,
        "combust": combust, "sat_house": sat_house, "plu_house": plu_house,
        "pf_lon": pf_lon, "pf_house": pf_house,
        "verdict": verdict, "confidence": conf, "score": round(score, 2),
        "reasons": reasons, "timing": timing, "precedent": precedent,
        "planets_in_1st": [p for p in planets if planets[p]["house"] == 1],
    }


def _planet_house(name: str, j: dict, data: dict) -> int:
    return data["planets"][name]["house"]


# ───────────────────────── HTML ─────────────────────────
_CSS = """
    :root { --ink:#1a1a1e; --muted:#5c5c66; --bg:#f7f5f0; --card:#fff; --accent:#2c5282; --border:#e2ddd4; }
    * { box-sizing:border-box; }
    body { font-family:Georgia,"Times New Roman",serif; background:var(--bg); color:var(--ink); line-height:1.55; margin:0; padding:1.5rem; }
    main { max-width:52rem; margin:0 auto; }
    h1 { font-size:1.45rem; font-weight:600; border-bottom:2px solid var(--accent); padding-bottom:0.35rem; }
    h2 { font-size:1.1rem; margin-top:1.75rem; color:var(--accent); }
    .meta { color:var(--muted); font-size:0.92rem; margin:0.75rem 0 1.25rem; }
    .card { background:var(--card); border:1px solid var(--border); border-radius:8px; padding:1rem 1.25rem; margin:1rem 0; }
    table { width:100%; border-collapse:collapse; font-size:0.9rem; }
    th, td { text-align:left; padding:0.35rem 0.5rem; border-bottom:1px solid var(--border); }
    th { font-weight:600; background:#f0ebe3; }
    .verdict { font-size:1.05rem; margin:1rem 0; padding:0.75rem 1rem; background:#e8f0f8; border-left:4px solid var(--accent); }
    .warn { background:#fff8e6; border-left:4px solid #c9a227; padding:0.75rem 1rem; margin:1rem 0; font-size:0.95rem; }
    .disclaimer { font-size:0.85rem; color:var(--muted); margin-top:2rem; padding-top:1rem; border-top:1px solid var(--border); }
    code { font-size:0.88em; background:#eee; padding:0.1em 0.35em; border-radius:3px; }
    .checklist-table td:nth-child(2) { background:#faf9f6; }
"""

PLANET_ORDER = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
                "Uranus", "Neptune", "Pluto"]


def plain_western_parts(j: dict, asc_lord: str, q_lord: str) -> dict:
    """The warm, plain-English summary of the Western judgment, as separate parts.

    Used both by the standalone Western report (``_plain_western`` wraps this
    into the styled card) and by the customer-facing confluence answer
    (``horary_answer.py``), which needs the same sentences without the
    surrounding document chrome.
    """
    v = j["verdict"].lower()
    if "increase" in v or "hike" in v or "size" in v:
        if "larger" in v:
            opener = ("The chart favours a <strong>stronger upward move</strong> — "
                      "not a flat yes/no, and not an exact %.")
        elif "modest" in v:
            opener = ("The chart favours a <strong>modest rise</strong> rather than a large hike — "
                      "exact figures are outside horary.")
        elif "limited" in v or "little room" in v:
            opener = ("Any rise looks <strong>limited</strong> on this chart — "
                      "do not expect a large hike from this asking.")
        else:
            opener = ("The <strong>size</strong> of any change is not clearly fixed — "
                      "ask as yes/no or timing if you need a sharper call.")
    elif v.startswith("yes"):
        opener = "Yes — the chart genuinely supports this."
    elif "likely" in v:
        opener = "The signs lean towards <strong>yes</strong>, though not overwhelmingly."
    elif "uncertain" in v or "qualified" in v:
        opener = "Honestly, this one is finely balanced — the chart doesn't commit either way."
    elif "unlikely" in v:
        opener = "The chart leans towards <strong>no</strong> as things stand."
    else:
        opener = "The honest answer is <strong>no</strong> — at least not the way the question stands now."

    # How the two key players relate, in plain terms.
    perf = j["perfection"]
    if j["same_lord"]:
        link = ("Your side and the matter itself are ruled by the same planet, so the two are "
                "naturally bound together — a strong built-in thread pulling them to meet.")
    elif perf and perf["applying"] and perf["aspect"] in ("trine", "sextile", "conjunction"):
        link = ("Your ruler and the matter's ruler are moving towards a friendly meeting — the "
                "clearest sign that the thing actually comes together.")
    elif perf and perf["applying"] and perf["aspect"] in ("square", "opposition"):
        link = ("Your ruler and the matter's ruler are heading into a tense, friction-filled "
                "contact — the kind that usually blocks or complicates the result.")
    elif perf and not perf["applying"]:
        link = ("Your ruler and the matter's ruler have already drifted apart — the best moment "
                "for it may simply have passed.")
    else:
        link = ("Your ruler and the matter's ruler don't actually link up on their own, so a clean "
                "'yes' isn't built into the chart — it would have to lean on a helping hand, like "
                "the Moon carrying the matter or a go-between stepping in.")

    if j["moon_void"]:
        moon = ("On top of that, the Moon is \u2018void\u2019 \u2014 drifting without a strong next "
                "move \u2014 which traditionally warns that not much may come of it.")
    elif any(n == "Moon" for n, _ in j["combust"]):
        moon = "The Moon is rather overwhelmed by the Sun just now, dimming the flow of events."
    else:
        moon = "The Moon is still active and engaged, so the situation is live and moving."

    conf = j["confidence"].lower()
    if conf.startswith("good") or conf.startswith("high"):
        confline = "I'd hold this reading with reasonable confidence."
    elif conf.startswith("mod"):
        confline = "Take it as a genuine leaning rather than a cast-iron certainty."
    else:
        confline = "The signals are faint and mixed, so please treat this as a soft impression, not a firm promise."

    return {"opener": opener, "link": link, "moon": moon, "confline": confline}


def _plain_western(j: dict, asc_lord: str, q_lord: str) -> str:
    """A warm, plain-English summary of the Western judgment — spoken as an astrologer would."""
    p = plain_western_parts(j, asc_lord, q_lord)
    return f"""<h2>The Short Answer — In Plain Words</h2>
  <div class="verdict">
    <p style="margin:0 0 0.6rem 0;font-size:1.05rem;">{p['opener']}</p>
    <p style="margin:0 0 0.6rem 0;">{p['link']}</p>
    <p style="margin:0 0 0.6rem 0;">{p['moon']}</p>
    <p style="margin:0;color:var(--muted);">{p['confline']}</p>
  </div>"""


def render(data: dict, question: str, j: dict, judge_dt: str, location: str) -> str:
    meta = data["meta"]
    planets = data["planets"]
    angles = data["angles"]
    P = lambda n: n  # noqa: E731

    # Chart table.
    rows = [f"<tr><td>Ascendant</td><td>{angles['asc_sign']}</td><td>{fmt_deg(angles['ascendant_deg'])}</td><td>1</td></tr>",
            f"<tr><td>MC</td><td>{angles['mc_sign']}</td><td>{fmt_deg(angles['mc_deg'])}</td><td>10</td></tr>"]
    for nm in PLANET_ORDER:
        p = planets[nm]
        retro = " R" if p.get("retrograde") else ""
        rows.append(f"<tr><td>{nm}{retro}</td><td>{p['sign']}</td><td>{fmt_deg(p['longitude'])}</td><td>{p['house']}</td></tr>")

    asc_lord, q_lord = j["asc_lord"], j["q_lord"]
    coruler = R.MODERN_CORULER.get(j["asc_sign"])
    moon_co = "" if j["moon_is_sig"] else " The Moon is co-ruler of the querent (the flow of the matter)."

    # Significators bullets.
    sig_items = [
        f"<li><strong>Querent (you):</strong> {j['asc_sign']} rises \u2014 lord <strong>{asc_lord}</strong>"
        + (f" (modern co-ruler {coruler})" if coruler else "") + "."
        + (f" Planets in the 1st: {', '.join(j['planets_in_1st'])}." if j['planets_in_1st'] else "")
        + moon_co + "</li>",
        f"<li><strong>The matter (house {j['quesited_house']}):</strong> {R.HOUSE_TOPICS[j['quesited_house']]} \u2014 "
        f"cusp in {j['q_sign']}, lord <strong>{q_lord}</strong>.</li>",
    ]
    if j["same_lord"]:
        sig_items.append(f"<li><strong>Same lord:</strong> {asc_lord} rules both the 1st and house {j['quesited_house']} "
                         "\u2014 you and the matter are strongly linked (Lilly: the topics merge).</li>")
    else:
        sig_items.append("<li><strong>Same lord:</strong> N/A \u2014 querent and quesited have different rulers.</li>")
    if j["quesited_house"] in (2, 10):
        mc_lord = R.DOMICILE[R.SIGN_IDX[angles['mc_sign']]]
        sig_items.append(f"<li><strong>10th (employer / career):</strong> MC in {angles['mc_sign']}, lord {mc_lord} "
                         f"(house of {R.HOUSE_TOPICS[10]}).</li>")

    # Dignities bullets.
    dig_items = []
    for label, nm, e in (("Querent lord", asc_lord, j["asc_ed"]),
                         ("Quesited lord", q_lord, j["q_ed"]),
                         ("Moon", "Moon", j["moon_ed"])):
        dig_items.append(f"<li><strong>{nm}</strong> ({label}): {R.dignity_phrase(nm, e)} "
                         f"\u2014 dignity score {e['score']:+d}.</li>")

    # Considerations (precompute conditional strings to avoid backslashes in f-string exprs).
    EM = "\u2014"
    DEGc = "\u00b0"
    if j["early_asc"]:
        asc_consider = f"early degrees {EM} the matter may be too new to judge firmly"
    elif j["late_asc"]:
        asc_consider = f"late degrees {EM} the matter is mature / near its end, or you are at the end of patience"
    else:
        asc_consider = f"middle degrees {EM} a fit, judgeable chart"
    via_txt = (f"Yes {EM} Moon between 15{DEGc} Libra and 15{DEGc} Scorpio (stress band)"
               if j["via_combusta"] else f"N/A {EM} Moon outside 15{DEGc} Libra\u201315{DEGc} Scorpio")
    if j["sat_house"] == 7:
        sp7_txt = f"Saturn in 7th {EM} the astrologer\u2019s caution flag"
    elif j["plu_house"] == 7:
        sp7_txt = f"Pluto in 7th {EM} deep/hidden undertone"
    else:
        sp7_txt = f"N/A {EM} neither in the 7th"
    combust_txt = ("; ".join(f"{n} {d}{DEGc} from Sun" for n, d in j["combust"])
                   if j["combust"] else f"N/A {EM} no significator under the Sun\u2019s beams")
    voc_txt = "Yes" if j["moon_void"] else "No"
    cons_items = [
        f"<li><strong>Early / late Ascendant:</strong> Asc {fmt_deg(angles['ascendant_deg'])} {j['asc_sign']} {EM} {asc_consider}.</li>",
        f"<li><strong>Via Combusta (Moon):</strong> {via_txt}.</li>",
        f"<li><strong>Void of course Moon:</strong> {voc_txt} {EM} {escape(j['moon_void_note'])}. "
        "Lilly exempt signs: Cancer, Taurus, Sagittarius, Pisces.</li>",
        f"<li><strong>Saturn / Pluto in 7th:</strong> {sp7_txt}.</li>",
        f"<li><strong>Combustion:</strong> {combust_txt}.</li>",
        "<li><strong>Planetary hour:</strong> N/A \u2014 not computed.</li>",
    ]

    # Moon chain.
    def asp_txt(a):
        if not a:
            return "none within orb"
        return f"{a['aspect']} {a['planet']} (orb {a['orb']}{DEG})"
    moon_items = [
        f"<li><strong>Day vs night:</strong> {'Day' if j['is_day'] else 'Night'} chart \u2014 Sun in house {planets['Sun']['house']}.</li>",
        f"<li><strong>Moon</strong> in {planets['Moon']['sign']}, house {planets['Moon']['house']} \u2014 where the mind/attention sits.</li>",
        f"<li><strong>Moon last (separating) aspect:</strong> {asp_txt(j['moon_last'])} \u2014 tone of the recent past.</li>",
        f"<li><strong>Moon next (applying) aspect:</strong> {asp_txt(j['moon_next'])} \u2014 where the matter is heading.</li>",
    ]

    # Perfection.
    perf = j["perfection"]
    if asc_lord == q_lord:
        perf_line = f"<li><strong>{asc_lord}</strong> rules both querent and quesited \u2014 the matter perfects within one significator (a strong link).</li>"
    elif perf:
        rec = ""
        if j["recept_a"] or j["recept_b"]:
            rec = f" Reception present ({asc_lord}\u2194{q_lord}), which eases the contact."
        perf_line = (f"<li><strong>{asc_lord} \u2194 {q_lord}:</strong> {perf['aspect']} "
                     f"({'applying' if perf['applying'] else 'separating'}, orb {perf['orb']}{DEG})."
                     f"{rec}</li>")
    else:
        perf_line = f"<li><strong>{asc_lord} \u2194 {q_lord}:</strong> no major aspect within orb \u2014 no direct perfection (look to translation/collection or the Moon).</li>"
    hope = j["hope_aspect"]
    hope_line = (f"<li><strong>Asc lord \u2194 11th lord ({j['h11_lord']}, hopes):</strong> "
                 + (f"{hope['aspect']} ({'applying' if hope['applying'] else 'separating'}, orb {hope['orb']}{DEG}) "
                    "\u2014 Louis's hope testimony "
                    + ("supports" if hope['applying'] and hope['aspect'] in ('trine', 'sextile', 'conjunction') else "is weak/contrary")
                    if hope else "no aspect within orb \u2014 hope testimony absent")
                 + ".</li>")

    # Verdict + reasons.
    reasons_html = "".join(f"<li>{escape(r)}.</li>" for r in j["reasons"])
    timing_html = ""
    for d, label, plain in j["timing"]:
        timing_html += (f"<p><strong>{d.strftime('%d %B %Y').lstrip('0')} \u2014 {escape(label)}.</strong> {escape(plain)}</p>")
    if not timing_html:
        timing_html = "<p>No single dated perfection stands out; read this as a process rather than one calendar day.</p>"

    prec = j["precedent"]
    prec_html = ""
    if prec:
        prec_html = (f'<div class="card"><strong>Book precedent (Anthony Louis, {escape(prec.get("book_ref","case"))}):</strong> '
                     f'\u201c{escape(prec.get("question",""))}\u201d \u2014 outcome <strong>{escape(str(prec.get("result","")))}</strong>. '
                     f'{escape(prec.get("book_note",""))}</div>')

    # Methodology checklist.
    checklist = [
        ("B \u2014 Chart data + source", f"Done \u2014 pyswisseph MOSEPH, UTC {meta.get('q_time_ut_approx','')} {meta['q_date']}, {escape(location)}, Placidus."),
        ("C1 \u2014 Sun vs day/night", f"Done \u2014 {'day' if j['is_day'] else 'night'} chart; Sun in house {planets['Sun']['house']}."),
        ("C2\u2013C3 \u2014 Asc fit, Moon last/next", f"Done \u2014 {j['asc_sign']} {fmt_deg(angles['ascendant_deg'])}; Moon {asp_txt(j['moon_last'])} / {asp_txt(j['moon_next'])}."),
        ("D \u2014 Considerations", f"Done \u2014 void Moon: {'yes' if j['moon_void'] else 'no'}; Via Combusta: {'yes' if j['via_combusta'] else 'no'}; Saturn 7th: {'yes' if j['sat_house']==7 else 'no'}."),
        ("E \u2014 Significators + 10th", f"Done \u2014 querent {asc_lord}; quesited {q_lord} (house {j['quesited_house']})."),
        ("F \u2014 Dignities", f"Done \u2014 {asc_lord} {j['asc_ed']['score']:+d}, {q_lord} {j['q_ed']['score']:+d}."),
        ("G \u2014 Perfection, Asc vs 11th lord", "Done \u2014 see Perfection section."),
        ("4th / PF", f"Done \u2014 Pars Fortuna in house {j['pf_house']}."),
        ("H \u2014 Verdict tied to gaps", f"Done \u2014 {j['verdict']} ({j['confidence']} confidence); tally {j['score']:+.1f}."),
    ]
    checklist_html = "".join(f"<tr><td>{escape(s)}</td><td>{escape(v)}</td></tr>" for s, v in checklist)

    plain_html = _plain_western(j, asc_lord, q_lord)

    short = re.sub(r"[^A-Za-z0-9 ]", "", question).strip()[:48]
    out = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Western Horary — {escape(short)}</title>
  <style>{_CSS}</style>
</head>
<body>
<main>
  <h1>Western Horary Report — {escape(question)}</h1>
  <p class="meta">
    <strong>Method:</strong> Traditional Western horary (Tropical), Anthony Louis / Lilly-style \u2014 deterministic engine over the mandatory §2b checklist below.<br />
    <strong>House system:</strong> Placidus (Louis often uses Koch; cusps may shift slightly under Koch).<br />
    <strong>Judgment:</strong> {escape(judge_dt)} \u2014 {escape(location)} ({meta['lat']}\u00b0N, {meta['lon']}\u00b0E).<br />
    <strong>UTC equivalent:</strong> {meta.get('q_time_ut_approx','')} UTC, {meta['q_date']}.<br />
    <strong>Question (verbatim):</strong> {escape(question)}
  </p>
  <div class="warn">Symbolic / traditional art only. Horary describes tendencies and timing windows \u2014 it is not medical, legal, or financial advice, and cannot name exact amounts.</div>

  {plain_html}

  <h2>Chart data</h2>
  <p class="meta">Computed with Swiss Ephemeris (MOSEPH), Tropical, geocentric, Placidus.</p>
  <div class="card"><table>
    <thead><tr><th>Point</th><th>Sign</th><th>{DEG}</th><th>House</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>

  <h2>Significators</h2>
  <div class="card"><ul>{''.join(sig_items)}</ul></div>

  <h2>Dignities (essential)</h2>
  <div class="card"><ul>{''.join(dig_items)}</ul></div>

  <h2>Considerations before judgment (Louis Ch. 2)</h2>
  <div class="card"><ul>{''.join(cons_items)}</ul></div>

  <h2>Radicality &amp; Moon chain</h2>
  <div class="card"><ul>{''.join(moon_items)}</ul></div>

  <h2>Perfection &amp; Louis's 11th-house rule</h2>
  <div class="card">
    <p>Louis: a fortunate aspect between the Ascendant ruler and the 11th ruler supports a positive hoped-for outcome (11th = hopes).</p>
    <ul>{perf_line}{hope_line}</ul>
  </div>

  <h2>4th house &amp; Pars Fortuna</h2>
  <div class="card"><ul>
    <li><strong>4th (end of matter):</strong> cusp in {R.sign_of(data['cusps'][3])} \u2014 how things finally settle.</li>
    <li><strong>Pars Fortuna ({'day' if j['is_day'] else 'night'} formula):</strong> {R.sign_of(j['pf_lon'])} {fmt_deg(j['pf_lon'])}, falling in house {j['pf_house']} \u2014 where ease/benefit flows in this matter.</li>
  </ul></div>

  <h2>Louis Chapter 2 — methodology checklist (auditable)</h2>
  <div class="card"><table class="checklist-table">
    <thead><tr><th>Step</th><th>Status</th></tr></thead>
    <tbody>{checklist_html}</tbody>
  </table></div>

  <h2>Judgment</h2>
  <div class="verdict">
    <strong>{escape(question)}</strong> \u2014 <strong>{j['verdict']}</strong> ({j['confidence']} confidence).<br /><br />
    This reading rests on the following testimonies:
    <ul>{reasons_html}</ul>
  </div>
  {prec_html}

  <h2>Timing windows (ephemeris)</h2>
  <div class="card">
    {timing_html}
    <p class="meta">Dates are symbolic reminders computed on Swiss Ephemeris (MOSEPH) for this question's instant \u2014 not guarantees; life does not read the clock literally.</p>
  </div>

  <p class="disclaimer">Symbolic / traditional art only; not medical, legal, or financial advice. Tropical Placidus chart computed with Swiss Ephemeris MOSEPH.</p>
</main>
</body>
</html>"""
    return out


def generate_western_horary_html(question: str, q_date: str, q_time: str,
                                 location: str = "New Delhi",
                                 quesited_house: int | None = None) -> tuple[str, dict]:
    data = precompute_western(question, q_date, q_time, location)
    if data.get("precompute_engine") != "swiss_ephemeris_moseph":
        raise RuntimeError("Swiss Ephemeris (pyswisseph) required for deterministic judgment.")
    qh = choose_quesited_house(question, quesited_house)
    j = judge(data, question, qh)
    judge_dt = f"{q_date}, {q_time} IST"
    html = render(data, question, j, judge_dt, location)
    return html, j


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministic Western horary report (no LLM)")
    ap.add_argument("question")
    ap.add_argument("q_date", help="YYYY-MM-DD")
    ap.add_argument("q_time", help="HH:MM (24h IST)")
    ap.add_argument("location", nargs="?", default="New Delhi")
    ap.add_argument("--quesited-house", type=int, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    html, j = generate_western_horary_html(args.question, args.q_date, args.q_time,
                                           args.location, args.quesited_house)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", args.question).strip("_")[:30] or "Question"
    out = args.out or f"reports/WesternHorary_{slug}_{args.q_date.replace('-', '')}.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {out}")
    print(f"  Verdict: {j['verdict']} ({j['confidence']}); tally {j['score']:+.1f}; quesited house {j['quesited_house']}")


if __name__ == "__main__":
    main()
