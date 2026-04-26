"""Calories and macros calculators per coach protocol."""

from __future__ import annotations


SEX_COEFFICIENT = {
    "male": 1.0,
    "m": 1.0,
    "man": 1.0,
    "м": 1.0,
    "муж": 1.0,
    "female": 0.9,
    "f": 0.9,
    "woman": 0.9,
    "ж": 0.9,
    "жен": 0.9,
}

ACTIVITY_COEFFICIENT = {
    "1.2": 1.2,
    "1.3": 1.3,
    "1.4": 1.4,
    "1.5": 1.5,
    "1.6": 1.6,
    "1.7": 1.7,
    "1.8": 1.8,
    "low": 1.2,
    "light": 1.3,
    "light_training": 1.4,
    "moderate": 1.5,
    "hard": 1.6,
    "very_hard": 1.7,
    "override": 1.8,
}


def sex_coefficient(sex: str) -> float:
    try:
        return SEX_COEFFICIENT[sex.lower()]
    except KeyError as exc:
        raise ValueError("Unknown sex") from exc


def fat_index(body_fat_pct: float, sex: str) -> float:
    sex_key = sex.lower()
    male = {"male", "m", "man", "м", "муж"}
    female = {"female", "f", "woman", "ж", "жен"}

    if sex_key in male:
        if 10 <= body_fat_pct <= 14:
            return 1.0
        if 14 < body_fat_pct <= 20:
            return 0.95
        if 20 < body_fat_pct <= 28:
            return 0.9
        if body_fat_pct > 28:
            return 0.85
        return 1.0

    if sex_key in female:
        if 14 <= body_fat_pct <= 18:
            return 1.0
        if 18 < body_fat_pct <= 28:
            return 0.95
        if 28 < body_fat_pct <= 38:
            return 0.9
        if body_fat_pct > 38:
            return 0.85
        return 1.0

    raise ValueError("Unknown sex")


def bmr(weight_kg: float, sex: str, body_fat_pct: float, calorie_adjustment: int = 0) -> float:
    bmr_value = (sex_coefficient(sex) * weight_kg * 24 * fat_index(body_fat_pct, sex)) + calorie_adjustment
    return round(bmr_value, 2)


def tdc(bmr_value: float, activity_level: str | float) -> float:
    if isinstance(activity_level, float):
        coeff = activity_level
    else:
        try:
            coeff = ACTIVITY_COEFFICIENT[activity_level.lower()]
        except KeyError as exc:
            raise ValueError("Unknown activity level") from exc
    return round(bmr_value * coeff, 2)


def bju_distribution(
    *,
    tdc_value: float,
    protein_share: float = 0.2,
    fat_share: float = 0.3,
) -> dict[str, float]:
    carb_share = 1 - protein_share - fat_share
    if carb_share < 0:
        raise ValueError("protein_share + fat_share must be <= 1")

    protein_kcal = tdc_value * protein_share
    fat_kcal = tdc_value * fat_share
    carb_kcal = tdc_value - protein_kcal - fat_kcal

    return {
        "protein_g": round(protein_kcal / 4, 2),
        "fat_g": round(fat_kcal / 9, 2),
        "carbs_g": round(carb_kcal / 4, 2),
    }


def bmr_mifflin_st_jeor(*, weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    sex_key = sex.lower().strip()
    male = {"male", "m", "man", "м", "муж", "мужчина", "мужской"}
    female = {"female", "f", "woman", "ж", "жен", "женщина", "женский"}

    if sex_key in male:
        return round((10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5, 2)
    if sex_key in female:
        return round((10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161, 2)
    raise ValueError("Unknown sex")


def goal_calories(*, tdee_value: float, goal_type: str) -> int:
    if goal_type == "muscle_gain":
        return int(round((tdee_value * 1.1) / 10) * 10)
    if goal_type == "fat_loss":
        return int(round((tdee_value * 0.85) / 10) * 10)
    if goal_type == "recomposition":
        return int(round((tdee_value * 0.95) / 10) * 10)
    return int(round(tdee_value / 10) * 10)


def goal_macros(*, weight_kg: float, target_calories: int, goal_type: str) -> dict[str, int]:
    if goal_type == "muscle_gain":
        protein = weight_kg * 1.8
        fat = weight_kg * 0.9
    elif goal_type == "fat_loss":
        protein = weight_kg * 2.0
        fat = weight_kg * 0.8
    elif goal_type == "recomposition":
        protein = weight_kg * 2.0
        fat = weight_kg * 0.8
    else:
        protein = weight_kg * 1.6
        fat = weight_kg * 0.9

    protein_cals = protein * 4
    fat_cals = fat * 9
    carbs = (target_calories - protein_cals - fat_cals) / 4
    if carbs < 30:
        carbs = 30.0

    return {
        "protein_g": int(round(protein)),
        "fat_g": int(round(fat)),
        "carbs_g": int(round(carbs)),
    }


def per_meal(macros: dict[str, float], meals: int = 4) -> dict[str, float]:
    if meals <= 0:
        raise ValueError("meals must be > 0")
    return {key: round(value / meals, 2) for key, value in macros.items()}
