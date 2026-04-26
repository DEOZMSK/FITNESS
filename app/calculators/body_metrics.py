"""Body metrics calculators (BMI, indices, WHR and somatotype)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

GAP_STATUS = "Пограничное значение / нужна дополнительная оценка"
WHR_NEUTRAL_STATUS = "Пограничное значение WHR: нужна дополнительная оценка"

SEX_ALIASES = {
    "male": {"male", "m", "man", "м", "муж"},
    "female": {"female", "f", "woman", "ж", "жен"},
}

BODY_TYPE_ALIASES = {
    "asthenic": {"asthenic", "астеник"},
    "normosthenic": {"normosthenic", "нормостеник"},
    "hypersthenic": {"hypersthenic", "гиперстеник"},
}

IDEAL_WEIGHT_COEFFICIENTS = {
    "male": {
        "asthenic": 0.85,
        "normosthenic": 0.9,
        "hypersthenic": 0.95,
    },
    "female": {
        "asthenic": 0.8,
        "normosthenic": 0.85,
        "hypersthenic": 0.9,
    },
}


@dataclass(frozen=True)
class RangeRule:
    """Classification interval.

    low and high are inclusive boundaries.
    """

    low: Optional[float]
    high: Optional[float]
    label: str


def _in_range(value: float, rule: RangeRule) -> bool:
    lower_ok = rule.low is None or value >= rule.low
    upper_ok = rule.high is None or value <= rule.high
    return lower_ok and upper_ok


def classify_with_gap_status(value: float, rules: Iterable[RangeRule], gap_status: str = GAP_STATUS) -> str:
    """Classify value by ranges and return a dedicated status for uncovered gaps."""

    for rule in rules:
        if _in_range(value, rule):
            return rule.label
    return gap_status


def bmi(height_cm: float, weight_kg: float) -> float:
    """Calculate body-mass index."""

    if height_cm <= 0:
        raise ValueError("height_cm must be > 0")
    return round(weight_kg / ((height_cm / 100) ** 2), 2)


def bmi_interpretation(bmi_value: float) -> str:
    rules = (
        RangeRule(None, 18.49, "Недостаточная масса тела"),
        RangeRule(18.5, 24.99, "Нормальная масса тела"),
        RangeRule(25.0, 29.99, "Избыточная масса тела"),
        RangeRule(30.0, 34.99, "Ожирение I степени"),
        RangeRule(35.0, 39.99, "Ожирение II степени"),
        RangeRule(40.0, None, "Ожирение III степени"),
    )
    return classify_with_gap_status(bmi_value, rules)


def _normalize_sex(sex: str) -> str:
    sex_key = sex.lower()
    if sex_key in SEX_ALIASES["male"]:
        return "male"
    if sex_key in SEX_ALIASES["female"]:
        return "female"
    raise ValueError("Unknown sex")


def _normalize_body_type(body_type: str) -> Optional[str]:
    body_type_key = body_type.lower()
    if body_type_key in BODY_TYPE_ALIASES["asthenic"]:
        return "asthenic"
    if body_type_key in BODY_TYPE_ALIASES["normosthenic"]:
        return "normosthenic"
    if body_type_key in BODY_TYPE_ALIASES["hypersthenic"]:
        return "hypersthenic"
    return None


def ideal_weight_by_body_type(height_cm: float, sex: str, body_type: str) -> float | tuple[float, float]:
    """Ideal weight by Broca-like coefficient and body type.

    Returns:
        float: for known body type.
        tuple[float, float]: min/max range for unknown body type.
    """

    normalized_sex = _normalize_sex(sex)
    coefficients = IDEAL_WEIGHT_COEFFICIENTS[normalized_sex]
    normalized_body_type = _normalize_body_type(body_type)

    if normalized_body_type:
        return round((height_cm - 100) * coefficients[normalized_body_type], 2)

    values = [round((height_cm - 100) * value, 2) for value in coefficients.values()]
    return (min(values), max(values))


def ideal_weight(height_cm: float, sex: str) -> float:
    """Deprecated Broca-based ideal weight.

    Kept for backward compatibility, equivalent to `normosthenic`.
    """

    result = ideal_weight_by_body_type(height_cm=height_cm, sex=sex, body_type="normosthenic")
    if isinstance(result, tuple):
        raise ValueError("Unexpected range result for normalized body type")
    return result


def somatotype(height_cm: float, weight_kg: float, wrist_cm: float) -> str:
    """Simple rule-based somatotype classification."""

    if wrist_cm <= 0:
        raise ValueError("wrist_cm must be > 0")

    bmi_value = bmi(height_cm, weight_kg)
    bone_index = height_cm / wrist_cm

    if bmi_value < 18.5 and bone_index > 10.5:
        return "Эктоморф"
    if 18.5 <= bmi_value <= 27 and 9.6 <= bone_index <= 10.5:
        return "Мезоморф"
    if bmi_value > 27 and bone_index < 9.6:
        return "Эндоморф"

    return GAP_STATUS


def chest_index(chest_circumference_cm: float, height_cm: float) -> float:
    """Chest development index in percent."""

    if height_cm <= 0:
        raise ValueError("height_cm must be > 0")
    return round((chest_circumference_cm / height_cm) * 100, 2)


def limb_index(limb_circumference_cm: float, height_cm: float) -> float:
    """Limb index in percent."""

    if height_cm <= 0:
        raise ValueError("height_cm must be > 0")
    return round((limb_circumference_cm / height_cm) * 100, 2)


def whr(waist_cm: float, hip_cm: float) -> float:
    """Waist-to-hip ratio."""

    if hip_cm <= 0:
        raise ValueError("hip_cm must be > 0")
    return round(waist_cm / hip_cm, 3)


def whr_interpretation(whr_value: float, sex: str) -> str:
    """WHR interpretation with neutral response for exact boundaries."""

    normalized_sex = _normalize_sex(sex)
    if normalized_sex == "male":
        low_boundary = 0.9
        high_boundary = 1.0
        low_text = "Низкий риск"
        normal_text = "Умеренный риск"
        high_text = "Высокий риск"
    elif normalized_sex == "female":
        low_boundary = 0.8
        high_boundary = 0.85
        low_text = "Низкий риск"
        normal_text = "Умеренный риск"
        high_text = "Высокий риск"
    else:
        raise ValueError("Unknown sex")

    if whr_value in {low_boundary, high_boundary}:
        return WHR_NEUTRAL_STATUS
    if whr_value < low_boundary:
        return low_text
    if low_boundary < whr_value < high_boundary:
        return normal_text
    if whr_value > high_boundary:
        return high_text
    return GAP_STATUS
