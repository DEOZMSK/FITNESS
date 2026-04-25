"""Calories and macros calculators."""

from __future__ import annotations

from app.calculators.body_metrics import GAP_STATUS, RangeRule, classify_with_gap_status


SEX_COEFFICIENT = {
    "male": 5,
    "m": 5,
    "man": 5,
    "м": 5,
    "муж": 5,
    "female": -161,
    "f": -161,
    "woman": -161,
    "ж": -161,
    "жен": -161,
}

ACTIVITY_COEFFICIENT = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "high": 1.725,
    "extreme": 1.9,
}



def sex_coefficient(sex: str) -> int:
    try:
        return SEX_COEFFICIENT[sex.lower()]
    except KeyError as exc:
        raise ValueError("Unknown sex") from exc



def fat_index(body_fat_pct: float) -> str:
    rules = (
        RangeRule(None, 12.99, "Низкий"),
        RangeRule(13.0, 24.99, "Норма"),
        RangeRule(25.0, 29.99, "Повышенный"),
        RangeRule(30.0, None, "Высокий"),
    )
    return classify_with_gap_status(body_fat_pct, rules, GAP_STATUS)



def bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    """Basal metabolic rate (Mifflin-St Jeor)."""

    return round(10 * weight_kg + 6.25 * height_cm - 5 * age + sex_coefficient(sex), 2)



def tdc(bmr_value: float, activity_level: str) -> float:
    """Total daily calories."""

    try:
        coeff = ACTIVITY_COEFFICIENT[activity_level.lower()]
    except KeyError as exc:
        raise ValueError("Unknown activity level") from exc

    return round(bmr_value * coeff, 2)



def bju_distribution(weight_kg: float, calories_target: float, goal: str = "maintain") -> dict[str, float]:
    """Protein/Fat/Carb daily grams by goal."""

    goal_key = goal.lower()
    if goal_key == "cut":
        protein_g = 2.0 * weight_kg
        fat_g = 0.8 * weight_kg
    elif goal_key == "bulk":
        protein_g = 1.8 * weight_kg
        fat_g = 1.0 * weight_kg
    elif goal_key == "maintain":
        protein_g = 1.6 * weight_kg
        fat_g = 0.9 * weight_kg
    else:
        raise ValueError("Unknown goal")

    protein_kcal = protein_g * 4
    fat_kcal = fat_g * 9
    carbs_kcal = max(calories_target - protein_kcal - fat_kcal, 0)
    carbs_g = carbs_kcal / 4

    return {
        "protein_g": round(protein_g, 2),
        "fat_g": round(fat_g, 2),
        "carbs_g": round(carbs_g, 2),
    }



def per_meal(macros: dict[str, float], meals: int) -> dict[str, float]:
    """Split macro plan equally by meals count."""

    if meals <= 0:
        raise ValueError("meals must be > 0")

    return {key: round(value / meals, 2) for key, value in macros.items()}
