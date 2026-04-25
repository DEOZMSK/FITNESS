"""Flexibility tests and scoring."""

from __future__ import annotations

from app.calculators.body_metrics import GAP_STATUS, RangeRule, classify_with_gap_status


SIT_AND_REACH_RULES = (
    RangeRule(None, -0.01, "Ниже среднего"),
    RangeRule(0.0, 9.99, "Средний"),
    RangeRule(10.0, 19.99, "Хороший"),
    RangeRule(20.0, None, "Отличный"),
)

SHOULDER_RULES = (
    RangeRule(None, -0.01, "Ограниченная мобильность"),
    RangeRule(0.0, 4.99, "Пограничная мобильность"),
    RangeRule(5.0, 14.99, "Функциональная мобильность"),
    RangeRule(15.0, None, "Высокая мобильность"),
)



def sit_and_reach_score(distance_cm: float) -> dict[str, str | float]:
    """Forward bend test with points."""

    if distance_cm < 0:
        points = 1
    elif distance_cm < 10:
        points = 2
    elif distance_cm < 20:
        points = 3
    else:
        points = 4

    status = classify_with_gap_status(distance_cm, SIT_AND_REACH_RULES, GAP_STATUS)
    return {"test": "sit_and_reach", "value_cm": round(distance_cm, 2), "status": status, "points": points}



def shoulder_flex_score(overlap_cm: float) -> dict[str, str | float]:
    """Behind-the-back shoulder test with points."""

    if overlap_cm < 0:
        points = 1
    elif overlap_cm < 5:
        points = 2
    elif overlap_cm < 15:
        points = 3
    else:
        points = 4

    status = classify_with_gap_status(overlap_cm, SHOULDER_RULES, GAP_STATUS)
    return {"test": "shoulder_flex", "value_cm": round(overlap_cm, 2), "status": status, "points": points}



def total_flexibility_score(sit_and_reach_cm: float, shoulder_overlap_cm: float) -> dict[str, int | str]:
    """Total points for two flexibility tests."""

    first = sit_and_reach_score(sit_and_reach_cm)
    second = shoulder_flex_score(shoulder_overlap_cm)
    total = int(first["points"] + second["points"])

    if total <= 3:
        label = "Низкая гибкость"
    elif total <= 5:
        label = "Средняя гибкость"
    elif total <= 7:
        label = "Хорошая гибкость"
    else:
        label = "Отличная гибкость"

    return {"total_points": total, "label": label}
