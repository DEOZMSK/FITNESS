"""Body metrics calculators (BMI, indices, WHR and somatotype) per coach protocol."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Optional

GAP_STATUS = "Пограничное значение, нужна дополнительная оценка"
WHR_NEUTRAL_STATUS = "Показатель находится около пограничного значения, лучше оценивать его вместе с другими замерами."

SEX_ALIASES = {
    "male": {"male", "m", "man", "м", "муж", "мужчина", "мужской", "парень"},
    "female": {"female", "f", "woman", "ж", "жен", "женщина", "женский", "девушка"},
}

BODY_TYPE_ALIASES = {
    "asthenic": {"asthenic", "астеник"},
    "normosthenic": {"normosthenic", "нормостеник"},
    "hypersthenic": {"hypersthenic", "гиперстеник"},
}

IDEAL_WEIGHT_COEFFICIENTS = {
    "male": {
        "asthenic": 0.375,
        "normosthenic": 0.39,
        "hypersthenic": 0.41,
    },
    "female": {
        "asthenic": 0.325,
        "normosthenic": 0.34,
        "hypersthenic": 0.355,
    },
}


@dataclass(frozen=True)
class RangeRule:
    low: Optional[float]
    high: Optional[float]
    label: str


def _in_range(value: float, rule: RangeRule) -> bool:
    lower_ok = rule.low is None or value >= rule.low
    upper_ok = rule.high is None or value <= rule.high
    return lower_ok and upper_ok


def classify_with_gap_status(value: float, rules: Iterable[RangeRule], gap_status: str = GAP_STATUS) -> str:
    for rule in rules:
        if _in_range(value, rule):
            return rule.label
    return gap_status


def bmi(height_cm: float, weight_kg: float) -> float:
    if height_cm <= 0:
        raise ValueError("height_cm must be > 0")
    return round(weight_kg / ((height_cm / 100) ** 2), 2)


def bmi_interpretation(bmi_value: float, age: int) -> str:
    if 18 <= age <= 25:
        rules = (
            RangeRule(None, 19.0, "Дистрофия 1 степени / выраженный дефицит массы"),
            RangeRule(19.5, 22.9, "Норма"),
            RangeRule(23.0, 27.5, "Повышенный вес"),
            RangeRule(27.6, 29.9, "Ожирение 1 степени"),
            RangeRule(30.0, 34.9, "Ожирение 2 степени"),
            RangeRule(35.0, 39.9, "Ожирение 3 степени"),
            RangeRule(40.0, None, "Ожирение 4 степени"),
        )
        return classify_with_gap_status(bmi_value, rules)

    if 26 <= age <= 45:
        rules = (
            RangeRule(None, 19.0, "Дистрофия 1 степени / выраженный дефицит массы"),
            RangeRule(20.0, 25.0, "Норма"),
            RangeRule(25.1, 27.9, "Повышенный вес"),
            RangeRule(28.0, 30.0, "Ожирение 1 степени"),
            RangeRule(31.0, 35.9, "Ожирение 2 степени"),
            RangeRule(36.0, 40.9, "Ожирение 3 степени"),
            RangeRule(41.0, None, "Ожирение 4 степени"),
        )
        return classify_with_gap_status(bmi_value, rules)

    return "Возраст вне диапазона 18–45 для этой шкалы; нужна дополнительная оценка"


def _normalize_sex(sex: str | None) -> str:
    if sex is None:
        raise ValueError("Unknown sex")
    sex_key = str(sex).strip().lower()
    if not sex_key:
        raise ValueError("Unknown sex")
    # Strip emoji and punctuation to support labels like "👨 Мужчина", "♀️ Женщина".
    sex_key = re.sub(r"[^a-zа-яё]+", " ", sex_key).strip()
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


def ideal_weight_by_body_type(height_cm: float, sex: str, body_type: str) -> float | tuple[float, float, float]:
    normalized_sex = _normalize_sex(sex)
    coefficients = IDEAL_WEIGHT_COEFFICIENTS[normalized_sex]
    normalized_body_type = _normalize_body_type(body_type)

    if normalized_body_type:
        return round(height_cm * coefficients[normalized_body_type], 2)

    low = round(height_cm * coefficients["asthenic"], 2)
    mid = round(height_cm * coefficients["normosthenic"], 2)
    high = round(height_cm * coefficients["hypersthenic"], 2)
    return (low, mid, high)


def ideal_weight(height_cm: float, sex: str) -> float:
    result = ideal_weight_by_body_type(height_cm=height_cm, sex=sex, body_type="normosthenic")
    if isinstance(result, tuple):
        raise ValueError("Unexpected range result")
    return result


def somatotype(sex: str, wrist_cm: float) -> str:
    if wrist_cm <= 0:
        raise ValueError("wrist_cm must be > 0")

    normalized_sex = _normalize_sex(sex)
    if normalized_sex == "male":
        rules = (
            RangeRule(14.0, 16.5, "Астеник"),
            RangeRule(16.6, 18.8, "Нормостеник"),
            RangeRule(18.9, None, "Гиперстеник"),
        )
    else:
        rules = (
            RangeRule(11.7, 14.0, "Астеник"),
            RangeRule(14.1, 15.8, "Нормостеник"),
            RangeRule(15.9, None, "Гиперстеник"),
        )

    return classify_with_gap_status(wrist_cm, rules)


def chest_index(chest_circumference_cm: float, height_cm: float) -> float:
    if height_cm <= 0:
        raise ValueError("height_cm must be > 0")
    return round((chest_circumference_cm / height_cm) * 100, 2)


def chest_index_interpretation(chest_index_value: float, sex: str) -> str:
    normalized_sex = _normalize_sex(sex)
    if normalized_sex == "male":
        rules = (
            RangeRule(None, 51.99, "Астенический тип"),
            RangeRule(52.0, 54.0, "Нормостенический тип"),
            RangeRule(54.01, None, "Гиперстенический тип"),
        )
    else:
        rules = (
            RangeRule(None, 49.99, "Астенический тип"),
            RangeRule(50.0, 52.0, "Нормостенический тип"),
            RangeRule(52.01, None, "Гиперстенический тип"),
        )

    return classify_with_gap_status(chest_index_value, rules)


def limb_index(height_standing_cm: float, height_sitting_cm: float | None) -> float | None:
    if height_sitting_cm is None:
        return None
    if height_standing_cm <= 0:
        raise ValueError("height_standing_cm must be > 0")
    if height_sitting_cm <= 0:
        raise ValueError("height_sitting_cm must be > 0")
    return round(((height_standing_cm - height_sitting_cm) / height_standing_cm) * 100, 2)


def limb_index_interpretation(limb_index_value: float | None) -> str:
    if limb_index_value is None:
        return "Не рассчитан (рост сидя не указан)"
    rules = (
        RangeRule(None, 86.99, "Гиперстеник"),
        RangeRule(87.0, 92.0, "Нормостеник"),
        RangeRule(92.01, None, "Астеник"),
    )
    return classify_with_gap_status(limb_index_value, rules)


def whr(waist_cm: float, hip_cm: float) -> float:
    if hip_cm <= 0:
        raise ValueError("hip_cm must be > 0")
    return round(waist_cm / hip_cm, 3)


def whr_interpretation(whr_value: float, sex: str) -> str:
    normalized_sex = _normalize_sex(sex)
    threshold = 0.9 if normalized_sex == "male" else 0.85
    if abs(whr_value - threshold) <= 1e-9:
        return WHR_NEUTRAL_STATUS
    if whr_value > threshold:
        return "Абдоминальный тип жироотложения"
    return "Бедренно-ягодичный тип жироотложения"


def waist_to_height_ratio(waist_cm: float, height_cm: float) -> float:
    if height_cm <= 0:
        raise ValueError("height_cm must be > 0")
    return round(waist_cm / height_cm, 3)


def waist_to_height_interpretation(whtr_value: float) -> str:
    if whtr_value < 0.4:
        return "Ниже стандартного диапазона"
    if whtr_value < 0.5:
        return "Нет повышенного риска"
    if whtr_value < 0.6:
        return "Повышенный риск"
    return "Высокий риск"
