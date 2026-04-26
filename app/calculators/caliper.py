"""Skinfold (caliper) estimations by coach protocol."""

from __future__ import annotations

import math
from typing import Literal


def body_surface_area(height_cm: float, weight_kg: float) -> float:
    return math.sqrt(height_cm * weight_kg / 3600)


def _norms_by_sex_age(sex: str, age: int) -> tuple[float, float, float] | None:
    sex_key = sex.lower()
    male = {"male", "m", "man", "м", "муж", "мужчина"}
    female = {"female", "f", "woman", "ж", "жен", "женщина"}

    if sex_key in male:
        if 18 <= age <= 29:
            return (8.0, 18.0, 19.0)
        if 30 <= age <= 39:
            return (11.0, 20.0, 26.0)
        if 40 <= age <= 49:
            return (13.0, 22.0, 28.0)
        if 50 <= age <= 59:
            return (15.0, 24.0, 30.0)
    elif sex_key in female:
        if 18 <= age <= 29:
            return (20.0, 28.0, 29.0)
        if 30 <= age <= 39:
            return (22.0, 30.0, 30.01)
        if 40 <= age <= 49:
            return (24.0, 32.0, 32.01)
        if 50 <= age <= 59:
            return (26.0, 35.0, 35.01)

    return None


def age_interpretation(body_fat_pct: float, sex: str, age: int) -> str:
    norms = _norms_by_sex_age(sex=sex, age=age)
    if norms is None:
        return "Возраст вне шкалы 18–59; нужна дополнительная оценка"

    normal_low, normal_high, elevated_threshold = norms
    if body_fat_pct < normal_low:
        return "Ниже нормы"
    if normal_low <= body_fat_pct <= normal_high:
        return "Норма"
    if normal_high < body_fat_pct < elevated_threshold:
        return "Выше нормы / погранично"
    return "Повышенный вес"


def coach_caliper_estimate(
    *,
    sex: str,
    age: int,
    height_cm: float,
    weight_kg: float,
    forearm: float,
    arm_front: float,
    arm_back: float,
    scapula: float,
    abdomen: float,
    thigh: float,
    calf: float,
    chest: float | None = None,
) -> dict[str, float | str]:
    sex_key = sex.lower()
    male = {"male", "m", "man", "м", "муж", "мужчина"}
    female = {"female", "f", "woman", "ж", "жен", "женщина"}

    bsa = body_surface_area(height_cm=height_cm, weight_kg=weight_kg)

    if sex_key in female:
        sum_folds = forearm + arm_front + arm_back + scapula + abdomen + thigh + calf
        average_skinfold = sum_folds / 14
    elif sex_key in male:
        if chest is None:
            raise ValueError("chest is required for male protocol")
        sum_folds = forearm + arm_front + arm_back + chest + scapula + abdomen + thigh + calf
        average_skinfold = sum_folds / 16
    else:
        raise ValueError("Unknown sex")

    fat_mass_kg = average_skinfold * bsa * 1.3
    fat_percent = (fat_mass_kg / weight_kg) * 100
    lbm_kg = weight_kg - weight_kg * (fat_percent / 100)

    return {
        "sum_folds": round(sum_folds, 2),
        "body_surface_area": round(bsa, 4),
        "average_skinfold": round(average_skinfold, 4),
        "fat_mass_kg": round(fat_mass_kg, 2),
        "fat_percent": round(fat_percent, 2),
        "lbm_kg": round(lbm_kg, 2),
        "fat_percent_status": age_interpretation(fat_percent, sex=sex, age=age),
        "method_note": "Оценка по калиперной методике из тренерского протокола.",
    }


def lean_body_mass(weight_kg: float, body_fat_pct: float) -> float:
    return round(weight_kg * (1 - body_fat_pct / 100), 2)
