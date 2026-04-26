"""Product/service configurations."""

products = [
    {
        "code": "fitness_diagnostics",
        "name": "Фитнес-диагностика",
        "description": "Первичная диагностика физической формы и целей.",
        "price": 1500,
        "currency": "RUB",
        "cta": "Записаться на диагностику",
        "is_active": True,
    },
    {
        "code": "personal_training",
        "name": "Персональные тренировки",
        "description": "Индивидуальная программа и сопровождение.",
        "price": 5000,
        "currency": "RUB",
        "cta": "Узнать про программу",
        "is_active": True,
    },
    {
        "code": "archive_program",
        "name": "Архивная программа",
        "description": "Старый пакет, скрыт из меню.",
        "price": 1000,
        "currency": "RUB",
        "cta": "Недоступно",
        "is_active": False,
    },
]
