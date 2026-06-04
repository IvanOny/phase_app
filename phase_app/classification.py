from __future__ import annotations

import math
from typing import Any

# ---------------------------------------------------------------------------
# IPF GL Points formula — Men, Classic (Raw), Full Power
# Source: IPF Technical Rules, Appendix E (2020 revision)
# Formula: GL = Total × 100 / (A - B × e^(-C × BW))
#
# TODO: Verify these coefficients against the current IPF Technical Rules PDF
#       before production release. Download from:
#       https://www.powerlifting.sport/rules/codes/info/technical-rules
# ---------------------------------------------------------------------------
_GL_A = 1199.72839
_GL_B = 1025.18162
_GL_C = 0.00921


def ipf_gl_points(bodyweight_kg: float, total_kg: float) -> float:
    """Calculate IPF GL points for a male classic raw lifter."""
    if bodyweight_kg <= 0 or total_kg <= 0:
        return 0.0
    denom = _GL_A - _GL_B * math.exp(-_GL_C * bodyweight_kg)
    if denom <= 0:
        return 0.0
    return round(total_kg * 100.0 / denom, 2)


# Label scale — anchored to user spec: "100 pts = recreational".
# Each tuple is (min_points_inclusive, label).
# Ordered highest → lowest so we can find first match.
GL_LABELS: list[tuple[float, str]] = [
    (175, "World-class"),
    (150, "National-level"),
    (125, "Advanced"),
    (100, "Recreational"),
    (75,  "Intermediate"),
    (50,  "Beginner"),
    (0,   "Untrained"),
]


def gl_label(points: float) -> str:
    for threshold, label in GL_LABELS:
        if points >= threshold:
            return label
    return "Untrained"


def next_gl_threshold(points: float) -> tuple[float, str] | None:
    """Return (threshold, label) of the next GL level above current points, or None if at top."""
    for threshold, label in reversed(GL_LABELS):
        if points < threshold:
            return threshold, label
    return None


# ---------------------------------------------------------------------------
# UPF (Ukrainian Powerlifting Federation, IPF affiliate) classification
# Men, Classic (Raw), Full Power
#
# Weight categories used by IPF/UPF: 74 kg, 83 kg
#
# TODO: Confirm exact totals from official UPF standards document:
#       https://ukrpowerlifting.com/розрядні-нормативи/
#       The numbers below are approximated from the closest available UNPF
#       data (75 kg / 82.5 kg categories) and should be replaced with
#       verified UPF 74 kg / 83 kg figures before release.
# ---------------------------------------------------------------------------
UPF_STANDARDS: dict[int, dict[str, float]] = {
    74: {
        "Class 3":          340.0,
        "Class 2":          397.5,
        "Class 1":          452.5,
        "Candidate Master": 510.0,
        "Master of Sport":  570.0,
    },
    83: {
        "Class 3":          365.0,
        "Class 2":          422.5,
        "Class 1":          480.0,
        "Candidate Master": 540.0,
        "Master of Sport":  602.5,
    },
}

# Ladder from entry → top
CLASS_LADDER = ["Class 3", "Class 2", "Class 1", "Candidate Master", "Master of Sport"]


def weight_category(bodyweight_kg: float) -> int:
    """Return the UPF weight category (74 or 83) for a male lifter."""
    return 74 if bodyweight_kg <= 74.0 else 83


def upf_status(bodyweight_kg: float, total_kg: float) -> dict[str, Any]:
    """
    Determine current UPF class, next target class, and kg gap.
    Auto-advances: once a class is achieved, target moves up automatically.
    """
    cat = weight_category(bodyweight_kg)
    standards = UPF_STANDARDS.get(cat, UPF_STANDARDS[83])

    current_class: str | None = None
    next_class: str | None = None
    next_threshold: float | None = None
    gap_kg: float | None = None

    for cls in CLASS_LADDER:
        threshold = standards[cls]
        if total_kg >= threshold:
            current_class = cls
        else:
            if next_class is None:
                next_class = cls
                next_threshold = threshold
                gap_kg = round(threshold - total_kg, 1)

    return {
        "weightCategory":        cat,
        "currentClass":          current_class,
        "nextClass":             next_class,
        "nextClassThresholdKg":  next_threshold,
        "gapKg":                 gap_kg,
    }


def classification_payload(bodyweight_kg: float, total_kg: float) -> dict[str, Any]:
    """Full classification payload returned to the frontend."""
    gl = ipf_gl_points(bodyweight_kg, total_kg)
    next_gl = next_gl_threshold(gl)

    return {
        "bodyweightKg": bodyweight_kg,
        "totalKg":      total_kg,
        "upf":          upf_status(bodyweight_kg, total_kg),
        "gl": {
            "points":         gl,
            "label":          gl_label(gl),
            "nextThreshold":  next_gl[0] if next_gl else None,
            "nextLabel":      next_gl[1] if next_gl else None,
            "gapPoints":      round(next_gl[0] - gl, 2) if next_gl else None,
        },
    }
