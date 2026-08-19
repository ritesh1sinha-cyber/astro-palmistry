"""Palm remedies — authentic classical & Vedic astrological palmistry upayas.

Sources & Classical Traditions:
  * Hast Samudrika Shastra & Jyotish Palmistry (Narayan Dutt Shrimali, M. Katakkar, B.V. Raman)
  * Classical Hand Analysis (Cheiro's Language of the Hand, Benham's Laws of Scientific Hand Reading)
  * Mudra Vigyan (Sacred finger contact and pranic nerve channel activation)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PalmRemedy:
    bucket: str  # "mantra" | "mudra" | "gemstone" | "daan" | "do" | "dont"
    category: str
    action: str
    reason: str
    source: str


# Planetary Astrological Profiles for each Mount / Finger
_ASTRO_PROFILES: dict[str, dict[str, Any]] = {
    "jupiter": {
        "planet": "Jupiter (Guru / Brihaspati)",
        "finger": "Index Finger (Tarjani)",
        "metal": "Gold, Brass, or Ashtadhatu",
        "gemstone": "Yellow Sapphire (Pukhraj) or Natural Yellow Topaz / Citrine",
        "gem_timing": "Wear on Thursday morning during Shukla Paksha (waxing moon) on the Index Finger after chanting the Guru Mantra.",
        "mantra": "Om Gram Greem Graum Sah Gurave Namah",
        "mantra_desc": "Chant the Guru Beej Mantra 108 times on Thursday mornings facing North-East to expand wisdom, leadership authority, and career prosperity.",
        "mudra": "Gyan Mudra (Jnana Mudra)",
        "mudra_desc": "Gently join the tip of your thumb with the tip of your index finger while keeping the other three fingers relaxed. Practice for 15 minutes daily during morning meditation to stimulate the Jupiter nadi, sharpening memory, strategic clarity, and dignified leadership.",
        "daan": "Offer fresh water to a Peepal or Banana tree on Thursdays; donate yellow grams (chana dal), turmeric, or yellow sweets to scholars or temples; apply a sacred Saffron or Turmeric tilak on your forehead/throat chakra.",
    },
    "saturn": {
        "planet": "Saturn (Shani Dev)",
        "finger": "Middle Finger (Madhyama)",
        "metal": "Energized Horse-Shoe Iron (Loha) or Silver-Iron alloy",
        "gemstone": "Blue Sapphire (Neelam) or Amethyst (Jamunia) / Blue Topaz",
        "gem_timing": "Wear on Saturday evening around sunset on the Middle Finger after propitiation of Lord Shani.",
        "mantra": "Om Pram Preem Praum Sah Shanaishcharaya Namah",
        "mantra_desc": "Chant the Shani Beej Mantra 108 times on Saturday evenings to cultivate unshakable perseverance, clear karmic obstacles, and maintain calm through life trials.",
        "mudra": "Shuni Mudra (Akasha Mudra)",
        "mudra_desc": "Gently touch the tip of your middle finger with the tip of your thumb. Practice for 15 minutes daily to balance the ether element, calming restless anxiety and cultivating patience and steadfast focus.",
        "daan": "Light a mustard oil lamp (deepak) near a Peepal tree on Saturday evening; donate black sesame seeds (til), black umbrella, or warm footwear to laborers and the elderly.",
    },
    "apollo": {
        "planet": "Sun (Surya Dev)",
        "finger": "Ring Finger (Anamika)",
        "metal": "Pure Copper (Tamba) or Gold",
        "gemstone": "Natural Ruby (Manikya) or Red Garnet / Star Ruby",
        "gem_timing": "Wear on Sunday morning during sunrise on the Ring Finger in a copper or gold setting.",
        "mantra": "Om Hram Hreem Hraum Sah Suryaya Namah",
        "mantra_desc": "Chant the Surya Beej Mantra 108 times at sunrise or recite the Aditya Hridaya Stotram on Sundays to amplify public recognition, creative authority, and radiant self-confidence.",
        "mudra": "Surya Mudra (Agni Mudra)",
        "mudra_desc": "Fold your ring finger to touch the base of the thumb and press gently down with the thumb. Practice for 10–15 minutes daily during morning meditation to support vital stamina, mental focus, and confidence.",
        "daan": "Perform daily Surya Arghya: offer fresh water mixed with kumkum and red flowers to the rising Sun from a pure copper vessel; donate wheat or jaggery on Sundays.",
    },
    "sun": {
        "planet": "Sun (Surya Dev)",
        "finger": "Ring Finger (Anamika)",
        "metal": "Pure Copper (Tamba) or Gold",
        "gemstone": "Natural Ruby (Manikya) or Red Garnet / Star Ruby",
        "gem_timing": "Wear on Sunday morning during sunrise on the Ring Finger in a copper or gold setting.",
        "mantra": "Om Hram Hreem Hraum Sah Suryaya Namah",
        "mantra_desc": "Chant the Surya Beej Mantra 108 times at sunrise or recite the Aditya Hridaya Stotram on Sundays to amplify public recognition, creative authority, and radiant self-confidence.",
        "mudra": "Surya Mudra (Agni Mudra)",
        "mudra_desc": "Fold your ring finger to touch the base of the thumb and press gently down with the thumb. Practice for 10–15 minutes daily during morning meditation to support vital stamina, mental focus, and confidence.",
        "daan": "Perform daily Surya Arghya: offer fresh water mixed with kumkum and red flowers to the rising Sun from a pure copper vessel; donate wheat or jaggery on Sundays.",
    },
    "mercury": {
        "planet": "Mercury (Budh Dev)",
        "finger": "Little Finger (Kanishtha)",
        "metal": "Bronze, Pure Silver, or Gold",
        "gemstone": "Natural Emerald (Panna) or Green Tourmaline / Peridot",
        "gem_timing": "Wear on Wednesday morning during Shukla Paksha on the Little Finger in silver or gold.",
        "mantra": "Om Bram Breem Braum Sah Budhaya Namah",
        "mantra_desc": "Chant the Budh Beej Mantra 108 times on Wednesday mornings facing North to sharpen analytical intellect, persuasive speech, and commercial success.",
        "mudra": "Varun Mudra (Buddhi Mudra)",
        "mudra_desc": "Touch the tip of your little finger to the tip of your thumb. Practice for 15 minutes daily to balance the water element and nervous system, improving communication clarity and commercial acumen.",
        "daan": "Feed fresh green grass or spinach to cows on Wednesday mornings; donate green moong dal or stationery to students; keep living green plants in the Northern sector of your workspace.",
    },
    "venus": {
        "planet": "Venus (Shukra Dev)",
        "finger": "Thumb / Ring Finger",
        "metal": "Pure Silver (Chandi) or Platinum",
        "gemstone": "Natural Diamond (Heera), White Zircon, or White Opal",
        "gem_timing": "Wear on Friday morning on the Ring Finger or Thumb in a silver setting.",
        "mantra": "Om Dram Dreem Draum Sah Shukraya Namah",
        "mantra_desc": "Chant the Shukra Beej Mantra 108 times on Friday mornings to enhance personal charisma, harmonious relationships, artistic creativity, and material refinement.",
        "mudra": "Prithvi Mudra / Shukra Mudra",
        "mudra_desc": "Join the tip of the ring finger with the tip of the thumb. Practice for 15 minutes daily to nourish bodily tissues (Ojas), ground emotional fluctuations, and refine aesthetic vitality.",
        "daan": "Donate white items (curd, rice, sugar, milk, or white sweets) on Friday mornings; wear clean, fragrant clothing; respect women and life partner.",
    },
    "moon": {
        "planet": "Moon (Chandra Dev)",
        "finger": "Little Finger or Ring Finger",
        "metal": "Pure Silver (Chandi)",
        "gemstone": "Natural South Sea Pearl (Moti) or Moonstone",
        "gem_timing": "Wear on Monday evening on the Little Finger in pure silver.",
        "mantra": "Om Shram Shreem Shraum Sah Chandraya Namah",
        "mantra_desc": "Chant the Chandra Beej Mantra 108 times on Monday evenings to calm overthinking, harmonize emotional moods, and deepen intuitive perception.",
        "mudra": "Prana Mudra",
        "mudra_desc": "Join the tips of the ring finger and little finger with the tip of the thumb while keeping the index and middle fingers straight. Practice for 15 minutes daily to revitalize prana and ground mental restlessness.",
        "daan": "Offer fresh milk or water on a Shiva Lingam on Mondays; drink drinking water stored in a pure silver tumbler; seek the blessings of mother and elder women.",
    },
    "luna": {
        "planet": "Moon (Chandra Dev)",
        "finger": "Little Finger or Ring Finger",
        "metal": "Pure Silver (Chandi)",
        "gemstone": "Natural South Sea Pearl (Moti) or Moonstone",
        "gem_timing": "Wear on Monday evening on the Little Finger in pure silver.",
        "mantra": "Om Shram Shreem Shraum Sah Chandraya Namah",
        "mantra_desc": "Chant the Chandra Beej Mantra 108 times on Monday evenings to calm overthinking, harmonize emotional moods, and deepen intuitive perception.",
        "mudra": "Prana Mudra",
        "mudra_desc": "Join the tips of the ring finger and little finger with the tip of the thumb while keeping the index and middle fingers straight. Practice for 15 minutes daily to revitalize prana and ground mental restlessness.",
        "daan": "Offer fresh milk or water on a Shiva Lingam on Mondays; drink drinking water stored in a pure silver tumbler; seek the blessings of mother and elder women.",
    },
    "mars": {
        "planet": "Mars (Mangal Dev)",
        "finger": "Ring Finger (Anamika)",
        "metal": "Pure Copper (Tamba) or Red Gold",
        "gemstone": "Natural Red Coral (Moonga) or Carnelian",
        "gem_timing": "Wear on Tuesday morning on the Ring Finger in a copper or gold setting.",
        "mantra": "Om Kram Kreem Kraum Sah Bhaumaya Namah",
        "mantra_desc": "Chant the Mangal Beej Mantra 108 times or recite the Hanuman Chalisa on Tuesdays to transform aggressive impulse into disciplined stamina, courage, and protective strength.",
        "mudra": "Prithvi Mudra",
        "mudra_desc": "Join the tip of the ring finger with the tip of the thumb. Practice for 15 minutes daily to ground physical strength and prevent burnout from over-exertion.",
        "daan": "Donate red lentils (masoor dal), jaggery, or copper coins on Tuesdays; channel fiery adrenaline through regular physical sports or yogasana.",
    },
}


def build_palm_remedies(feats: dict[str, Any]) -> list[PalmRemedy]:
    """Return authentic classical & Vedic astrological remedies for the hand."""
    feats = feats or {}
    mounts = feats.get("mounts") or {}
    quality = feats.get("quality") or {}
    grade = str(quality.get("grade") or "fair").lower()
    allow_gemstones = grade == "good"
    marks = feats.get("special_marks") or []
    lines = feats.get("lines") or {}
    minor = feats.get("minor_lines") or {}
    
    out: list[PalmRemedy] = []
    seen: set[str] = set()

    def add(bucket: str, category: str, action: str, reason: str, source: str) -> None:
        key = " ".join((bucket, category, action[:40])).lower()
        if not action or key in seen:
            return
        seen.add(key)
        out.append(PalmRemedy(bucket=bucket, category=category, action=action, reason=reason, source=source))

    # 1. Targeted Mount Upayas (Triggered ONLY by specific afflictions, flat mounts, or prominent imbalance)
    # Jupiter: Only if Grille present or Mount is flat
    has_jup_grille = any(str(m.get("type") or "").lower() == "grille" and str(m.get("zone") or "").lower() == "jupiter" for m in marks)
    jup_lvl = str(mounts.get("jupiter") or "").lower()
    if has_jup_grille or jup_lvl == "flat":
        p = _ASTRO_PROFILES["jupiter"]
        add("mudra", "Sacred Mudra", f"<b>{p['mudra']}</b>: {p['mudra_desc']}", 
            "Stimulates the Jupiter nadi beneath the index finger, elevating leadership, intellect, and higher discernment.", "Hast Samudrika & Mudra Vigyan")
        add("mantra", "Planetary Mantra", f"<b>Guru Beej Mantra</b>: <code>{p['mantra']}</code><br>{p['mantra_desc']}", 
            "Harmonizes Jupiterian vibrations to pacify scattered ambition and channel authority.", "Brihat Samhita & Vedic Jyotish")
        add("daan", "Vedic Seva & Ritual", p["daan"], "Traditional Thursday Brihaspati propitiation.", "Classical Hast Rekha Upayas")

    # Mars: Only if Mars is Prominent / Aggressive
    mars_lvl = str(mounts.get("mars") or "").lower()
    if mars_lvl == "prominent":
        p = _ASTRO_PROFILES["mars"]
        add("mantra", "Planetary Mantra", f"<b>Mangal Beej Mantra & Hanuman Chalisa</b>: <code>{p['mantra']}</code><br>{p['mantra_desc']}", 
            "Channels high martial energy into disciplined courage and protects against impulsive disputes.", "Vedic Jyotish")
        add("mudra", "Sacred Mudra", f"<b>{p['mudra']}</b>: {p['mudra_desc']}", 
            "Grounds fiery physical adrenaline and prevents burnout from over-exertion.", "Mudra Vigyan")
        add("daan", "Vedic Seva & Ritual", p["daan"], "Mars propitiation to ground excess heat and protect physical stamina.", "Mangal Upasana")

    # Moon: Only if Star on Moon or Moon is Flat
    has_moon_star = any(str(m.get("type") or "").lower() == "star" and str(m.get("zone") or "").lower() in ("moon", "luna") for m in marks)
    moon_lvl = str(mounts.get("moon") or mounts.get("luna") or "").lower()
    if has_moon_star or moon_lvl == "flat":
        p = _ASTRO_PROFILES["moon"]
        add("mudra", "Sacred Mudra", f"<b>{p['mudra']}</b>: {p['mudra_desc']}", 
            "Calms mental restlessness, steadies emotional fluctuations, and deepens intuition.", "Prana Vidya")
        add("mantra", "Planetary Mantra", f"<b>Chandra Beej Mantra</b>: <code>{p['mantra']}</code><br>{p['mantra_desc']}", 
            "Harmonizes lunar currents for deep mental peace and restorative sleep.", "Chandra Upasana")
        add("daan", "Vedic Seva & Ritual", p["daan"], "Lunar propitiation for emotional calm.", "Vedic Upayas")

    # Saturn: Only if Saturn is Flat or Fate line is wavy/broken
    sat_lvl = str(mounts.get("saturn") or "").lower()
    fate_q = str((lines.get("fate") or {}).get("quality") or "").lower()
    if sat_lvl == "flat" or fate_q in ("broken", "wavy", "weak"):
        p = _ASTRO_PROFILES["saturn"]
        add("mudra", "Sacred Mudra", f"<b>{p['mudra']}</b>: {p['mudra_desc']}", 
            "Grounds career discipline, long-term patience, and emotional fortitude.", "Mudra Vigyan")
        add("mantra", "Planetary Mantra", f"<b>Shani Beej Mantra</b>: <code>{p['mantra']}</code><br>{p['mantra_desc']}", 
            "Pacifies Saturnine delays and turns diligent labor into lasting vocational standing.", "Shani Upasana")
        add("daan", "Vedic Seva & Ritual", p["daan"], "Saturday seva to remove career obstacles.", "Karmic Palmistry")

    # Special Mark Upayas
    for mark in marks:
        kind = str(mark.get("type") or mark.get("kind") or "").lower()
        zone = str(mark.get("zone") or mark.get("mount") or "palm").lower()
        if kind == "grille" and zone == "jupiter":
            add("do", "Daily Focus Discipline", 
                "Focus on finishing one primary leadership initiative at a time. The grille on Jupiter indicates multi-directional energy that yields the greatest rewards when channeled through single-pointed focus.", 
                "Channeling scattered Jupiterian energy.", "Cheiro, Language of the Hand")
        elif kind == "star" and zone in ("moon", "luna"):
            add("dont", "Water & Travel Prudence", 
                "Practice mindful caution during spontaneous long-distance journeys or around turbulent water bodies.", 
                "Classical Moon star sensitivity.", "Hast Samudrika")

    return out


def format_remedy_line(r: PalmRemedy) -> str:
    """Customer-safe remedy line."""
    return f"{r.action}"
