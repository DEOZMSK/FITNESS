"""Body metrics calculators (BMI, indices, WHR and somatotype)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

GAP_STATUS = "Пограничное значение / нужна дополнительная оценка"
WHR_NEUTRAL_STATUS = "Пограничное значение WHR: нужна дополнительная оценка"


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



def ideal_weight(height_cm: float, sex: str) -> float:
    """Broca-based ideal weight."""

    if sex.lower() in {"male", "m", "man", "м", "муж"}:
        coefficient = 0.9
    elif sex.lower() in {"female", "f", "woman", "ж", "жен"}:
        coefficient = 0.85
    else:
        raise ValueError("Unknown sex")

    return round((height_cm - 100) * coefficient, 2)



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

    sex_key = sex.lower()
    if sex_key in {"male", "m", "man", "м", "муж"}:
        low_boundary = 0.9
        high_boundary = 1.0
        low_text = "Низкий риск"
        normal_text = "Умеренный риск"
        high_text = "Высокий риск"
    elif sex_key in {"female", "f", "woman", "ж", "жен"}:
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
