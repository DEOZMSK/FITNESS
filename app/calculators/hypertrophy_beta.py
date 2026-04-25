"""Experimental hypertrophy scoring helpers (beta)."""

from __future__ import annotations

from typing import Mapping

from app.calculators.body_metrics import GAP_STATUS, RangeRule, classify_with_gap_status

# Coefficients map kept as explicit dictionary structure for transparent tuning.
COEFFICIENT_MAP = {
    "volume_sets": {
        "low": 0.75,
        "medium": 1.0,
        "high": 1.15,
        "very_high": 1.25,
    },
    "intensity_rpe": {
        "submax": 0.85,
        "working": 1.0,
        "hard": 1.1,
        "near_limit": 1.2,
    },
    "frequency": {
        "1x": 0.85,
        "2x": 1.0,
        "3x": 1.1,
        "4x_plus": 1.15,
    },
    "recovery": {
        "poor": 0.8,
        "moderate": 0.95,
        "good": 1.05,
        "excellent": 1.15,
    },
    "exercise_quality": {
        "poor": 0.8,
        "acceptable": 0.95,
        "good": 1.05,
        "excellent": 1.15,
    },
}

PERCENT_RULES = (
    RangeRule(None, 59.99, "Недостаточный стимул"),
    RangeRule(60.0, 79.99, "Рабочий стимул"),
    RangeRule(80.0, 94.99, "Оптимальный стимул"),
    RangeRule(95.0, 100.0, "Погранично высокий стимул"),
)

PERIODIZATION_REFERENCE = {
    "Недостаточный стимул": "Добавьте 1-2 рабочих подхода и/или увеличьте частоту на 1 тренировку в неделю.",
    "Рабочий стимул": "Сохраните объём, прогрессируйте весом или повторениями каждую 1-2 недели.",
    "Оптимальный стимул": "Поддерживайте текущую фазу 3-5 недель, затем проведите разгрузку.",
    "Погранично высокий стимул": "Сократите объём на 15-30% в следующем микроцикле и усилите восстановление.",
    GAP_STATUS: "Показатель вне валидного диапазона, проверьте входные данные.",
}



def weekly_score(components: Mapping[str, str]) -> float:
    """Aggregate weekly hypertrophy score by coefficient labels."""

    score = 1.0
    for block, option in components.items():
        if block not in COEFFICIENT_MAP:
            raise ValueError(f"Unknown block: {block}")
        variants = COEFFICIENT_MAP[block]
        if option not in variants:
            raise ValueError(f"Unknown option '{option}' for block '{block}'")
        score *= variants[option]

    return round(score * 100, 2)



def hypertrophy_percent(score: float, min_score: float = 50.0, max_score: float = 130.0) -> float:
    """Normalize raw score to percent corridor."""

    if max_score <= min_score:
        raise ValueError("max_score must be > min_score")
    normalized = ((score - min_score) / (max_score - min_score)) * 100
    return round(max(0.0, min(normalized, 100.0)), 2)



def hypertrophy_status(percent: float) -> str:
    return classify_with_gap_status(percent, PERCENT_RULES, GAP_STATUS)



def periodization_reference(percent: float) -> str:
    status = hypertrophy_status(percent)
    return PERIODIZATION_REFERENCE[status]
