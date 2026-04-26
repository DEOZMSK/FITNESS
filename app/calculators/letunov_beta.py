"""Reference rule-based Letunov test interpretation (beta)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LetunovInput:
    resting_hr: int
    peak_hr: int
    recovery_hr_1min: int
    systolic_rest: int
    systolic_peak: int


LETUNOV_TYPES = (
    "нормотонический после 1-й нагрузки",
    "нормотонический после 2-й нагрузки",
    "дистонический",
    "гипертонический",
    "ступенчатый",
    "гипотонический",
)


def recovery_delta(peak_hr: int, recovery_hr_1min: int) -> int:
    return peak_hr - recovery_hr_1min


def pressure_reactivity_index(systolic_rest: int, systolic_peak: int) -> float:
    if systolic_rest <= 0:
        raise ValueError("systolic_rest must be > 0")
    return round(systolic_peak / systolic_rest, 3)


def classify_letunov(data: LetunovInput) -> dict[str, str | int | float]:
    hr_drop = recovery_delta(data.peak_hr, data.recovery_hr_1min)
    pressure_idx = pressure_reactivity_index(data.systolic_rest, data.systolic_peak)

    if hr_drop >= 30 and 1.2 <= pressure_idx <= 1.6:
        profile = "нормотонический после 1-й нагрузки"
    elif hr_drop >= 25 and 1.15 <= pressure_idx <= 1.6:
        profile = "нормотонический после 2-й нагрузки"
    elif pressure_idx > 1.7:
        profile = "гипертонический"
    elif pressure_idx < 1.1:
        profile = "гипотонический"
    elif 20 <= hr_drop < 25:
        profile = "дистонический"
    else:
        profile = "ступенчатый"

    return {
        "profile": profile,
        "recovery_delta": hr_drop,
        "pressure_reactivity_index": pressure_idx,
        "note": "Beta-справочник. Не использовать как медицинское заключение.",
    }
