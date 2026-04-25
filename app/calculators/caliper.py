"""Skinfold (caliper) estimations."""

from __future__ import annotations

from app.calculators.body_metrics import GAP_STATUS, RangeRule, classify_with_gap_status


AGE_RULES_MALE = (
    RangeRule(None, 7.99, "Очень низкий % жира"),
    RangeRule(8.0, 19.99, "Норма"),
    RangeRule(20.0, 24.99, "Повышенный % жира"),
    RangeRule(25.0, None, "Высокий % жира"),
)

AGE_RULES_FEMALE = (
    RangeRule(None, 20.99, "Очень низкий % жира"),
    RangeRule(21.0, 32.99, "Норма"),
    RangeRule(33.0, 38.99, "Повышенный % жира"),
    RangeRule(39.0, None, "Высокий % жира"),
)



def body_fat_percent(sum_of_folds_mm: float, age: int, sex: str) -> float:
    """Estimate body fat with Jackson-Pollock 3-site equations."""

    s = sum_of_folds_mm
    sex_key = sex.lower()

    if sex_key in {"male", "m", "man", "м", "муж"}:
        density = 1.10938 - 0.0008267 * s + 0.0000016 * (s**2) - 0.0002574 * age
    elif sex_key in {"female", "f", "woman", "ж", "жен"}:
        density = 1.0994921 - 0.0009929 * s + 0.0000023 * (s**2) - 0.0001392 * age
    else:
        raise ValueError("Unknown sex")

    if density <= 0:
        raise ValueError("Invalid skinfold values")

    return round((495 / density) - 450, 2)



def lean_body_mass(weight_kg: float, body_fat_pct: float) -> float:
    """Lean body mass (LBM)."""

    return round(weight_kg * (1 - body_fat_pct / 100), 2)



def age_interpretation(body_fat_pct: float, sex: str) -> str:
    """Age-aware simplification (rule-based; no strict clinical scope)."""

    sex_key = sex.lower()
    if sex_key in {"male", "m", "man", "м", "муж"}:
        return classify_with_gap_status(body_fat_pct, AGE_RULES_MALE, GAP_STATUS)
    if sex_key in {"female", "f", "woman", "ж", "жен"}:
        return classify_with_gap_status(body_fat_pct, AGE_RULES_FEMALE, GAP_STATUS)

    raise ValueError("Unknown sex")
