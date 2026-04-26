"""Body metrics calculators (BMI, indices, WHR and somatotype)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

GAP_STATUS = "Пограничное значение / нужна дополнительная оценка"
WHR_NEUTRAL_STATUS = "Пограничное значение WHR / нужна дополнительная оценка"

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


def bmi_interpretation(bmi_value: float, age: int) -> str:
    """Interpret BMI for age ranges 18–25 and 26–45 years."""

    if 18 <= age <= 25:
        normal_low = 18.5
        normal_high = 24.9
    elif 26 <= age <= 45:
        normal_low = 19.0
        normal_high = 25.9
    else:
        raise ValueError("age must be in [18, 45]")

    rules = (
        RangeRule(None, normal_low - 0.01, "Недостаточная масса тела"),
        RangeRule(normal_low, normal_high, "Нормальная масса тела"),
        RangeRule(normal_high + 0.01, 29.99, "Избыточная масса тела"),
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


def somatotype(sex: str, wrist_cm: float) -> str:
    """Somatotype classification by wrist circumference and sex."""

    if wrist_cm <= 0:
        raise ValueError("wrist_cm must be > 0")

    normalized_sex = _normalize_sex(sex)
    if normalized_sex == "male":
        ecto_limit = 18.0
        meso_limit = 20.0
    else:
        ecto_limit = 15.0
        meso_limit = 17.0

    if wrist_cm < ecto_limit:
        return "Эктоморф"
    if ecto_limit < wrist_cm < meso_limit:
        return "Мезоморф"
    if wrist_cm > meso_limit:
        return "Эндоморф"

    return GAP_STATUS


def chest_index(chest_circumference_cm: float, height_cm: float) -> float:
    """Chest development index in percent."""

    if height_cm <= 0:
        raise ValueError("height_cm must be > 0")
    return round((chest_circumference_cm / height_cm) * 100, 2)


def chest_index_interpretation(chest_index_value: float, sex: str) -> str:
    """Chest index interpretation by sex with boundary-gap handling."""

    normalized_sex = _normalize_sex(sex)
    if normalized_sex == "male":
        low_boundary = 50.0
        high_boundary = 55.0
    else:
        low_boundary = 48.0
        high_boundary = 53.0

    rules = (
        RangeRule(None, low_boundary - 0.01, "Узкая грудная клетка"),
        RangeRule(low_boundary + 0.01, high_boundary - 0.01, "Нормальная грудная клетка"),
        RangeRule(high_boundary + 0.01, None, "Широкая грудная клетка"),
    )
    return classify_with_gap_status(chest_index_value, rules)


def limb_index(height_standing_cm: float, height_sitting_cm: float | None) -> float | None:
    """Limb index in percent from standing and sitting heights."""

    if height_sitting_cm is None:
        return None
    if height_standing_cm <= 0:
        raise ValueError("height_standing_cm must be > 0")
    if height_sitting_cm <= 0:
        raise ValueError("height_sitting_cm must be > 0")
    return round(((height_standing_cm - height_sitting_cm) / height_standing_cm) * 100, 2)


def whr(waist_cm: float, hip_cm: float) -> float:
    """Waist-to-hip ratio."""

    if hip_cm <= 0:
        raise ValueError("hip_cm must be > 0")
    return round(waist_cm / hip_cm, 3)


def whr_interpretation(whr_value: float, sex: str) -> str:
    """WHR interpretation with boundary-gap handling."""

    normalized_sex = _normalize_sex(sex)
    if normalized_sex == "male":
        low_boundary = 0.90
        high_boundary = 1.00
    else:
        low_boundary = 0.80
        high_boundary = 0.85

    rules = (
        RangeRule(None, low_boundary - 0.001, "Низкий риск"),
        RangeRule(low_boundary + 0.001, high_boundary - 0.001, "Умеренный риск"),
        RangeRule(high_boundary + 0.001, None, "Высокий риск"),
    )
    status = classify_with_gap_status(whr_value, rules, gap_status=WHR_NEUTRAL_STATUS)
    return status
