"""Flexibility tests and scoring per coach protocol."""

from __future__ import annotations


def shoulder_girdle_test(result: str) -> dict[str, str | int]:
    normalized = result.strip().lower()
    if normalized == "ладони касаются":
        return {"points": 4, "status": "Очень хорошая гибкость"}
    if normalized == "пальцы касаются":
        return {"points": 3, "status": "Хорошая гибкость"}
    if normalized == "до 3 см":
        return {"points": 2, "status": "Средняя гибкость"}
    if normalized == "> 4 см":
        return {"points": 1, "status": "Ниже средней"}
    return {"points": 0, "status": "Нужна ручная оценка"}


def passive_shoulder_test(distance_cm: float) -> dict[str, str | int | float]:
    if distance_cm <= 85:
        points, status = 4, "Превосходная гибкость"
    elif distance_cm <= 95:
        points, status = 3, "Хорошая гибкость"
    elif distance_cm <= 120:
        points, status = 2, "Средняя гибкость"
    else:
        points, status = 1, "Ниже средней"

    return {"points": points, "status": status, "distance_cm": round(distance_cm, 2)}


def total_flexibility_score(shoulder_girdle_points: int, passive_shoulder_points: int) -> dict[str, int | str]:
    total = shoulder_girdle_points + passive_shoulder_points
    if total >= 7:
        label = "Отличная гибкость"
    elif total >= 5:
        label = "Хорошая гибкость"
    elif total >= 3:
        label = "Средняя гибкость"
    else:
        label = "Гибкость ниже средней"
    return {"total_points": total, "label": label}
