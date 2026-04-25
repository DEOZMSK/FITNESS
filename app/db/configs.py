"""Seed configuration for database entities."""

from __future__ import annotations

SEED_PRODUCTS: list[dict[str, object]] = [
    {
        "code": "fitness_consult_basic",
        "name": "Базовая консультация",
        "description": "Разбор целей, текущей формы и базовый план на 2 недели.",
        "price": 1990,
        "currency": "RUB",
        "is_active": 1,
    },
    {
        "code": "fitness_consult_pro",
        "name": "PRO сопровождение",
        "description": "Персональный план тренировок и питания на 1 месяц.",
        "price": 4990,
        "currency": "RUB",
        "is_active": 1,
    },
    {
        "code": "fitness_consult_vip",
        "name": "VIP сопровождение",
        "description": "Глубокая диагностика и персональное сопровождение 6 недель.",
        "price": 11990,
        "currency": "RUB",
        "is_active": 1,
    },
]

SEED_REVIEWS: list[dict[str, object]] = [
    {
        "author_name": "Анна",
        "rating": 5,
        "text": "За 3 недели появилась система и стало легче держать режим.",
        "is_published": 1,
    },
    {
        "author_name": "Игорь",
        "rating": 5,
        "text": "Понравился формат диагностики: быстро и по делу.",
        "is_published": 1,
    },
    {
        "author_name": "Марина",
        "rating": 4,
        "text": "Хороший старт для тех, кто возвращается к тренировкам.",
        "is_published": 1,
    },
]
