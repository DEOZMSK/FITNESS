"""Reference rule-based Letunov test interpretation (beta).

Module is intentionally standalone and can be imported from private pipelines
without a mandatory public scenario.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LetunovInput:
    """Input set for a simplified Letunov profile."""

    resting_hr: int
    peak_hr: int
    recovery_hr_1min: int
    systolic_rest: int
    systolic_peak: int



def recovery_delta(peak_hr: int, recovery_hr_1min: int) -> int:
    """Heart-rate drop at minute 1 after effort."""

    return peak_hr - recovery_hr_1min



def pressure_reactivity_index(systolic_rest: int, systolic_peak: int) -> float:
    """Systolic pressure response ratio."""

    if systolic_rest <= 0:
        raise ValueError("systolic_rest must be > 0")
    return round(systolic_peak / systolic_rest, 3)



def classify_letunov(data: LetunovInput) -> dict[str, str | int | float]:
    """Rule-based interpretation for coach reference."""

    hr_drop = recovery_delta(data.peak_hr, data.recovery_hr_1min)
    pressure_idx = pressure_reactivity_index(data.systolic_rest, data.systolic_peak)

    if hr_drop >= 30 and 1.2 <= pressure_idx <= 1.6:
        profile = "Нормотонический"
        recommendation = "Текущая реакция адекватна: можно продолжать плановую прогрессию нагрузки."
    elif hr_drop < 20 or pressure_idx > 1.7:
        profile = "Гипертонический"
        recommendation = "Снизьте интенсивность и добавьте контроль восстановления перед повышением нагрузки."
    elif hr_drop < 25 and pressure_idx < 1.15:
        profile = "Астенический"
        recommendation = "Увеличивайте нагрузку постепенно, уделите внимание ОФП и аэробной базе."
    else:
        profile = "Пограничный / нужна дополнительная оценка"
        recommendation = "Рекомендуется повторный контроль теста и консультация профильного специалиста."

    return {
        "profile": profile,
        "recovery_delta": hr_drop,
        "pressure_reactivity_index": pressure_idx,
        "recommendation": recommendation,
    }
