"""Unified fitness diagnostics flow and result views."""

from __future__ import annotations

import logging
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.bot.keyboards import (
    BUTTON_CONSULT_NO,
    BUTTON_CONSULT_YES,
    BUTTON_CONTACT,
    BUTTON_DIAGNOSTICS,
    BUTTON_DONT_KNOW,
    BUTTON_HOME_MENU,
    BUTTON_KEEP,
    BUTTON_NO,
    BUTTON_REENTER,
    BUTTON_RETAKE,
    BUTTON_RESULT_MY_DATA,
    BUTTON_RESULT_REPORT,
    BUTTON_RESULT_UPDATE,
    BUTTON_SEX_MAN,
    BUTTON_SEX_WOMAN,
    BUTTON_SKIP_PRESSURE,
    BUTTON_SKIP_SITTING,
    BUTTON_VIEW_RESULTS,
    BUTTON_YES,
    get_contact_trainer_keyboard,
    get_instagram_dm_keyboard,
    get_existing_profile_actions_keyboard,
    get_main_menu_keyboard,
    get_post_diagnostics_keyboard,
)
from app.bot.states import QuickDiagnosticsStates
from app.bot.texts import (
    get_final_report_text,
    get_goal_explanation,
    get_input_error_text,
    get_intermediate_processing_text,
    get_metric_explanation,
    get_question_text,
)
from app.calculators.body_metrics import (
    bmi,
    bmi_interpretation,
    chest_index,
    chest_index_interpretation,
    ideal_weight_by_body_type,
    limb_index,
    limb_index_interpretation,
    somatotype,
    whr,
    whr_interpretation,
)
from app.calculators.calories import bju_distribution, tdc
from app.config import load_settings
from app.db import Database

router = Router(name=__name__)
logger = logging.getLogger(__name__)

GOALS = [
    "Похудеть",
    "Улучшить здоровье",
    "Начать тренироваться с нуля",
    "Подтянуть тело",
    "Набрать мышечную массу",
    "Улучшить выносливость",
    "Другое",
]
GOAL_TYPE_TEXTS = {
    "muscle_gain": {
        "title": "набрать мышечную массу",
        "plain": (
            "Вам нужно есть немного больше, чем организм тратит, и давать мышцам регулярную "
            "силовую нагрузку. Без профицита калорий масса обычно не растёт, даже если тренировки хорошие."
        ),
        "calories_details": (
            "Для набора массы обычно нужен небольшой профицит: примерно +10–15% к текущей норме."
        ),
        "calories_hint": "Если вес не растёт 10–14 дней, калории можно аккуратно повысить ещё на 100–150 ккал.",
        "macros_hint": (
            "При наборе массы особенно важно добирать белок и углеводы. Белок помогает "
            "восстанавливаться, а углеводы дают энергию для силовых тренировок. Если еды мало — мышцам просто не из чего расти."
        ),
        "attention_items": [
            "Если вес не растёт — скорее всего, не хватает калорий.",
            "Если растёт только живот — профицит может быть слишком большим.",
            "Если силовые не растут — возможно, не хватает восстановления, сна или структуры тренировок.",
            "Для набора важно не просто «много есть», а регулярно тренироваться и отслеживать прогресс.",
        ],
        "pain_point": (
            "Многие тренируются, но не растут, потому что едят «на глаз» и недобирают калории. "
            "Кажется, что еды много, но по факту организм остаётся около поддержания."
        ),
        "trainer_extra": [
            "какой набор выбрать: более «чистый» или более быстрый;",
            "как понять, что растут мышцы, а не только вес;",
        ],
    },
    "fat_loss": {
        "title": "снизить вес",
        "plain": (
            "Вам нужно создать умеренный дефицит калорий: тратить чуть больше, чем получаете с едой. "
            "При этом важно сохранить белок и силовые нагрузки, чтобы уходил в основном жир, а не мышцы."
        ),
        "calories_details": "Для снижения веса обычно нужен умеренный дефицит: примерно –10–20% от текущей нормы.",
        "calories_hint": "Если вес уходит слишком быстро, повышается усталость или падает сила — дефицит может быть слишком жёстким.",
        "macros_hint": (
            "При снижении веса белок особенно важен: он помогает сохранять мышцы и лучше держать сытость. "
            "Углеводы и жиры не нужно «обнулять» — их нужно грамотно настроить."
        ),
        "attention_items": [
            "Если вес стоит — возможно, фактических калорий больше, чем кажется.",
            "Если постоянная усталость — дефицит может быть слишком жёстким.",
            "Если уходит сила — нужно проверить белок, сон и тренировочную нагрузку.",
            "Цель — не просто меньше весить, а сохранить мышцы и улучшить форму тела.",
        ],
        "pain_point": (
            "Многие начинают слишком жёстко: резко режут еду, устают, срываются и возвращаются назад. "
            "Рабочий путь — не наказание, а понятная система."
        ),
        "trainer_extra": [
            "какой дефицит выбрать без жёстких ограничений;",
            "как снижать вес без потери мышц и энергии;",
        ],
    },
    "maintenance": {
        "title": "удержать форму",
        "plain": (
            "Вам важно держать баланс: получать примерно столько энергии, сколько тратите. "
            "Основная задача — стабильный вес, нормальное самочувствие и регулярная активность."
        ),
        "calories_details": "Ваша задача — держаться рядом с текущим ориентиром.",
        "calories_hint": "Если вес стабилен 2–3 недели, значит питание примерно совпадает с расходом.",
        "macros_hint": (
            "БЖУ помогает держать стабильность: не переедать хаотично, не проваливаться по белку "
            "и не зависеть только от «ем как получится»."
        ),
        "attention_items": [
            "Если вес постепенно растёт — калорий чуть больше, чем нужно.",
            "Если вес падает без цели — калорий может быть мало.",
            "Если нет энергии — стоит проверить сон, питание и нагрузку.",
            "Поддержание — это не «ничего не делать», а стабильная система.",
        ],
        "pain_point": (
            "Когда нет системы, форма постепенно «уплывает»: сегодня чуть больше, завтра меньше движения, "
            "потом усталость — и результат теряется незаметно."
        ),
        "trainer_extra": [],
    },
    "general_fitness": {
        "title": "улучшить физическую форму",
        "plain": (
            "Фокус не только на весе. Важно постепенно улучшать силу, выносливость, "
            "подвижность, осанку и общее самочувствие."
        ),
        "calories_details": "Начните с текущего ориентира.",
        "calories_hint": (
            "Дальше корректировка зависит от того, что важнее: больше энергии, снижение жира, "
            "рост силы или улучшение выносливости."
        ),
        "macros_hint": (
            "БЖУ — это не диета, а ориентир. Он помогает понять, хватает ли телу строительного материала, "
            "энергии и восстановления."
        ),
        "attention_items": [
            "Не оценивайте прогресс только по весам.",
            "Важны сила, выносливость, подвижность, осанка и самочувствие.",
            "Слишком резкий старт часто приводит к откату.",
            "Лучше стабильные 2–3 тренировки в неделю, чем рывок на 10 дней и срыв.",
        ],
        "pain_point": (
            "Многие ждут мотивацию, но форму создаёт не мотивация, а повторяемая система: "
            "понятные тренировки, питание и восстановление."
        ),
        "trainer_extra": [],
    },
}
ACTIVITY_OPTIONS = [
    "Низкая активность",
    "Лёгкая активность",
    "Лёгкая активность + тренировки",
    "Средняя активность",
    "Тяжёлая активность",
    "Очень тяжёлая активность",
]
ACTIVITY_COEFFS = {
    "Низкая активность": 1.2,
    "Лёгкая активность": 1.3,
    "Лёгкая активность + тренировки": 1.4,
    "Средняя активность": 1.5,
    "Тяжёлая активность": 1.6,
    "Очень тяжёлая активность": 1.7,
}
WORKOUT_OPTIONS = ["0", "1–2", "3–4", "5+"]
HEALTH_LIMIT_OPTIONS = ["Нет", "Да", "Не знаю"]
PREGNANCY_OPTIONS = ["Нет", "Да", "Не применимо"]


def _two_col_keyboard(items: list[str], add_home: bool = False) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    for i in range(0, len(items), 2):
        rows.append([KeyboardButton(text=x) for x in items[i : i + 2]])
    if add_home:
        rows.append([KeyboardButton(text=BUTTON_HOME_MENU)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def _single_col_keyboard(items: list[str]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=item)] for item in items],
        resize_keyboard=True,
    )


def _to_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw.strip().replace(",", "."))
    except ValueError:
        return None


def _parse_pressure(raw: str) -> tuple[int, int] | None:
    normalized = raw.strip().replace(" ", "").replace("\\", "/")
    if "/" not in normalized:
        return None
    parts = normalized.split("/", maxsplit=1)
    if len(parts) != 2:
        return None
    try:
        s, d = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not (70 <= s <= 260 and 40 <= d <= 160):
        return None
    return s, d


def _safe_number(v: float | None) -> str:
    if v is None:
        return "—"
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return str(round(v, 2)).replace(".", ",")


def _round_calories(value: float) -> int:
    return int(round(value / 10) * 10)


def _normalize_goal(goal_text: str | None) -> str:
    goal = (goal_text or "").strip().lower()
    mapping = {
        "набрать мышечную массу": "muscle_gain",
        "набор мышечной массы": "muscle_gain",
        "похудеть": "fat_loss",
        "снизить вес": "fat_loss",
        "снижение веса": "fat_loss",
        "поддерживать форму": "maintenance",
        "поддержание формы": "maintenance",
        "удержать форму": "maintenance",
        "улучшить форму": "general_fitness",
        "общая физическая форма": "general_fitness",
        "улучшить здоровье": "general_fitness",
        "подтянуть тело": "general_fitness",
        "улучшить выносливость": "general_fitness",
        "начать тренироваться с нуля": "general_fitness",
    }
    return mapping.get(goal, "general_fitness")


def _calculate_goal_calories(tdee_value: float, goal_type: str) -> int:
    if goal_type == "muscle_gain":
        return _round_calories(tdee_value * 1.1)
    if goal_type == "fat_loss":
        return _round_calories(tdee_value * 0.85)
    return _round_calories(tdee_value)


def _goal_macros(weight_kg: float, target_calories: int, goal_type: str) -> dict[str, int]:
    if goal_type == "muscle_gain":
        protein = weight_kg * 1.8
        fat = weight_kg * 0.9
    elif goal_type == "fat_loss":
        protein = weight_kg * 2.0
        fat = weight_kg * 0.8
    else:
        protein = weight_kg * 1.6
        fat = weight_kg * 0.9

    protein_cals = protein * 4
    fat_cals = fat * 9
    carbs = (target_calories - protein_cals - fat_cals) / 4
    if carbs < 0:
        logger.warning("Calculated negative carbs, fallback to 30g: goal=%s target_calories=%s", goal_type, target_calories)
        carbs = 30.0

    return {
        "protein_g": int(round(protein)),
        "fat_g": int(round(fat)),
        "carbs_g": int(round(carbs)),
    }


def _client_data_block(profile: dict, goal_text: str) -> list[str]:
    return [
        "👤 <b>Данные клиента</b>",
        f"{escape(str(profile.get('full_name') or 'Клиент'))}, {profile.get('age') or '—'} лет",
        f"Пол: {_sex_label(profile.get('sex')) if profile.get('sex') else '—'}",
        f"Рост: {_safe_number(profile.get('height_cm'))} см",
        f"Вес: {_safe_number(profile.get('weight_kg'))} кг",
        f"Цель: {goal_text or '—'}",
    ]


def _goal_explanation_block(goal_type: str) -> list[str]:
    return get_goal_explanation(goal_type).split("\n")


def _metrics_interpretation_block(payload: dict) -> list[str]:
    lines = [
        "⚖️ <b>Ваша отправная точка</b>",
        f"ИМТ: {round(payload['bmi'], 2):.2f} — {payload['bmi_status'].lower()}",
        f"Тип телосложения: {payload['body_type']}.",
        f"Соотношение талии и бёдер: {round(payload['whr'], 2):.2f}.",
        "",
        "<b>Что это значит:</b>",
        "Это стартовая картина по телосложению и текущему состоянию. "
        "Дальше фокус — не на «идеальных цифрах», а на стабильном плане под вашу цель.",
    ]
    if payload.get("whr_status"):
        lines.extend(
            [
                "",
                f"Тип жироотложения: {payload['whr_status']}.",
                "<b>Что это значит:</b>",
                "Жир может распределяться неравномерно — это нормально. "
                "Локально «сжечь» жир в одной зоне нельзя, работает только системный подход.",
            ]
        )
    return lines


def _calories_block(payload: dict, goal_type: str, target_calories: int) -> list[str]:
    goal_data = GOAL_TYPE_TEXTS[goal_type]
    lines = [
        "🔥 <b>Энергия на день</b>",
        get_metric_explanation("calories", str(target_calories)).replace("🔥 ", ""),
        "",
        "<b>Объяснение:</b>",
        "Это примерная точка отсчёта. От неё зависит, будет ли вес расти, снижаться или стоять на месте.",
        "",
        goal_data["calories_details"],
    ]
    if goal_type in {"muscle_gain", "fat_loss"}:
        lines.extend(["", f"Ориентир: {target_calories} ккал/сутки."])
    elif goal_type == "maintenance":
        lines.extend(["", f"Ориентир: {target_calories} ккал/сутки."])
    else:
        lines.extend(["", f"Стартовый ориентир: {target_calories} ккал/сутки."])
    lines.extend(["", goal_data["calories_hint"]])
    return lines


def _macros_block(macros: dict[str, int], goal_type: str) -> list[str]:
    goal_data = GOAL_TYPE_TEXTS[goal_type]
    return [
        "🍽️ <b>Белки, жиры и углеводы</b>",
        f"Белки: {macros['protein_g']} г",
        f"Жиры: {macros['fat_g']} г",
        f"Углеводы: {macros['carbs_g']} г",
        "",
        "<b>Объяснение простым языком:</b>",
        "Белок — материал для мышц и восстановления.",
        "Жиры — гормоны, здоровье кожи, нервной системы и общее самочувствие.",
        "Углеводы — энергия для тренировок, шагов и повседневной активности.",
        "",
        goal_data["macros_hint"],
    ]


def _attention_block(goal_type: str) -> list[str]:
    return ["📌 <b>На что обратить внимание</b>", *[f"• {item}" for item in GOAL_TYPE_TEXTS[goal_type]["attention_items"]]]


def _trainer_discussion_block(goal_type: str) -> list[str]:
    common_items = [
        "какой темп результата для вас безопасен;",
        "сколько тренировок в неделю реально выдерживать;",
        "какие упражнения подходят под ваш уровень;",
        "есть ли ограничения по здоровью, суставам, спине, давлению;",
        "как скорректировать питание под ваш режим жизни;",
        "как отслеживать прогресс без паники и крайностей;",
    ]
    items = [*common_items, *GOAL_TYPE_TEXTS[goal_type]["trainer_extra"]]
    return ["💬 <b>Что стоит обсудить с тренером</b>", *[f"• {item}" for item in items]]


def _pain_point_block(goal_type: str) -> list[str]:
    return ["🧠 <b>Частая ошибка</b>", GOAL_TYPE_TEXTS[goal_type]["pain_point"]]


def _cta_block() -> list[str]:
    return [
        "🤝 <b>Хотите точнее?</b>",
        "Этот отчёт — стартовая карта, а не персональная программа.",
        "Чтобы цифры стали понятным планом действий, напишите Лене.",
        "",
        "Она поможет:",
        "• разобрать вашу цель;",
        "• учесть ограничения;",
        "• подобрать безопасную нагрузку;",
        "• настроить питание без крайностей;",
        "• понять, что делать именно вам.",
        "",
        "💬 <b>Написать Лене</b>",
    ]


def _disclaimer_block(profile: dict) -> list[str]:
    lines = [
        "⚠️ <b>Важно</b>",
        "Бот не ставит диагнозы и не заменяет врача. Расчёты являются ориентиром.",
        "Если есть заболевания, боли, ограничения, беременность, восстановление после травм или операции — "
        "нагрузку и питание нужно согласовывать со специалистом.",
    ]
    if profile.get("health_notes"):
        lines.extend(["", f"Ограничения, которые вы указали: {profile['health_notes']}"])
    return lines


def _normalize_sex(sex_text: str) -> str:
    normalized = (sex_text or "").strip().lower()
    if normalized in {"female", "женщина", "жен", "женский", "♀️ женщина"}:
        return "female"
    if normalized in {"male", "мужчина", "муж", "мужской", "👨 мужчина"}:
        return "male"
    raise ValueError("Unknown sex")


def _sex_label(sex_value: str | None) -> str:
    return "Женщина" if sex_value == "female" else "Мужчина"


async def _user_context(message: Message) -> tuple[Database, int]:
    db = Database()
    uid = db.upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    return db, uid


def _ask_number(field: str) -> str:
    return get_question_text(field)


async def _start_questionnaire(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(QuickDiagnosticsStates.waiting_for_name)
    await message.answer(
        "Сейчас я задам несколько вопросов, чтобы собрать первичные данные и подготовить фитнес-отчёт. "
        "Это не медицинский диагноз, а предварительная оценка для дальнейшей работы с тренером."
    )
    await message.answer(get_question_text("name"))


@router.message(F.text == BUTTON_DIAGNOSTICS)
async def diagnostics_entry(message: Message, state: FSMContext) -> None:
    db = Database()
    profile = db.get_latest_profile_or_none(message.from_user.id)
    if not profile:
        await _start_questionnaire(message, state)
        return
    await state.clear()
    await message.answer(
        "Вы уже проходили фитнес-диагностику. Что хотите сделать?",
        reply_markup=get_existing_profile_actions_keyboard(),
    )


@router.message(F.text == BUTTON_VIEW_RESULTS)
async def show_prev_results(message: Message) -> None:
    await message.answer("Открываю сохранённые результаты.", reply_markup=get_post_diagnostics_keyboard())


@router.message(F.text == BUTTON_RETAKE)
async def retake_diagnostics(message: Message, state: FSMContext) -> None:
    await _start_questionnaire(message, state)


@router.message(F.text == BUTTON_RESULT_UPDATE)
async def update_diagnostics(message: Message, state: FSMContext) -> None:
    await state.set_state(QuickDiagnosticsStates.waiting_for_update_confirmation)
    await message.answer(
        "Вы хотите обновить данные? Старый отчёт останется в истории, но актуальные данные будут заменены.",
        reply_markup=_two_col_keyboard(["Да, обновить", "Отмена"]),
    )


@router.message(QuickDiagnosticsStates.waiting_for_update_confirmation)
async def update_confirmation(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt == "Да, обновить":
        await _start_questionnaire(message, state)
        return
    await state.clear()
    await message.answer("Окей, оставила текущие данные.", reply_markup=get_post_diagnostics_keyboard())


@router.message(QuickDiagnosticsStates.waiting_for_name)
async def q_name(message: Message, state: FSMContext) -> None:
    full_name = (message.text or "").strip()
    if len(full_name) < 2:
        await message.answer(get_input_error_text("text_required"))
        return
    await state.update_data(full_name=full_name)
    await state.set_state(QuickDiagnosticsStates.waiting_for_sex)
    await message.answer(get_question_text("sex"), reply_markup=_two_col_keyboard([BUTTON_SEX_WOMAN, BUTTON_SEX_MAN]))


@router.message(QuickDiagnosticsStates.waiting_for_sex)
async def q_sex(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt not in {BUTTON_SEX_WOMAN, BUTTON_SEX_MAN, "♀️ Женщина", "👨 Мужчина"}:
        await message.answer(get_input_error_text("choice_button"))
        return
    await state.update_data(sex=_normalize_sex(txt))
    await state.set_state(QuickDiagnosticsStates.waiting_for_age)
    await message.answer(_ask_number("age"), reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BUTTON_HOME_MENU)]], resize_keyboard=True))


def _validate_number(message_text: str | None, lo: float, hi: float) -> float | None:
    value = _to_float(message_text)
    if value is None:
        return None
    if not (lo <= value <= hi):
        return -1
    return value


@router.message(QuickDiagnosticsStates.waiting_for_age)
async def q_age(message: Message, state: FSMContext) -> None:
    value = _validate_number(message.text, 12, 90)
    if value is None:
        await message.answer(get_input_error_text("number"))
        return
    if value == -1:
        await message.answer(get_input_error_text("age_format"))
        return
    await state.update_data(age=int(value))
    await state.set_state(QuickDiagnosticsStates.waiting_for_height)
    await message.answer(_ask_number("height"))


@router.message(QuickDiagnosticsStates.waiting_for_height)
async def q_height(message: Message, state: FSMContext) -> None:
    value = _validate_number(message.text, 120, 230)
    if value is None:
        await message.answer(get_input_error_text("number"))
        return
    if value == -1:
        await message.answer(get_input_error_text("height_format"))
        return
    if value < 135 or value > 215:
        await message.answer("Проверьте, пожалуйста, рост — значение выглядит необычно.")
    await state.update_data(height_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_weight)
    await message.answer(_ask_number("weight"))


@router.message(QuickDiagnosticsStates.waiting_for_weight)
async def q_weight(message: Message, state: FSMContext) -> None:
    value = _validate_number(message.text, 30, 250)
    if value is None:
        await message.answer(get_input_error_text("number"))
        return
    if value == -1:
        await message.answer(get_input_error_text("weight_format"))
        return
    if value < 40 or value > 180:
        await message.answer("Проверьте, пожалуйста, вес — значение выглядит необычно.")
    await state.update_data(weight_kg=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_waist)
    await message.answer(_ask_number("waist"))


@router.message(QuickDiagnosticsStates.waiting_for_waist)
async def q_waist(message: Message, state: FSMContext) -> None:
    value = _validate_number(message.text, 40, 200)
    if value is None:
        await message.answer(get_input_error_text("number"))
        return
    if value == -1:
        await message.answer(get_input_error_text("waist_format"))
        return
    await state.update_data(waist_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_hips)
    await message.answer(_ask_number("hips"))


@router.message(QuickDiagnosticsStates.waiting_for_hips)
async def q_hips(message: Message, state: FSMContext) -> None:
    value = _validate_number(message.text, 40, 220)
    if value is None:
        await message.answer(get_input_error_text("number"))
        return
    if value == -1:
        await message.answer(get_input_error_text("hips_format"))
        return
    data = await state.get_data()
    if value < float(data["waist_cm"]):
        await state.update_data(pending_hips=value)
        await state.set_state(QuickDiagnosticsStates.waiting_for_hips_confirmation)
        await message.answer(
            "Проверьте обхват бёдер. Обычно он больше обхвата талии. Оставить как есть?",
            reply_markup=_two_col_keyboard([BUTTON_KEEP, BUTTON_REENTER]),
        )
        return
    await state.update_data(hips_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_chest)
    await message.answer(_ask_number("chest"))


@router.message(QuickDiagnosticsStates.waiting_for_hips_confirmation)
async def q_hips_confirm(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt == BUTTON_KEEP:
        data = await state.get_data()
        await state.update_data(hips_cm=data.get("pending_hips"))
        await state.set_state(QuickDiagnosticsStates.waiting_for_chest)
        await message.answer(_ask_number("chest"))
        return
    await state.set_state(QuickDiagnosticsStates.waiting_for_hips)
    await message.answer(_ask_number("hips"))


@router.message(QuickDiagnosticsStates.waiting_for_chest)
async def q_chest(message: Message, state: FSMContext) -> None:
    value = _validate_number(message.text, 40, 200)
    if value is None:
        await message.answer(get_input_error_text("number"))
        return
    if value == -1:
        await message.answer(get_input_error_text("number"))
        return
    await state.update_data(chest_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_wrist)
    await message.answer(_ask_number("wrist"))


@router.message(QuickDiagnosticsStates.waiting_for_wrist)
async def q_wrist(message: Message, state: FSMContext) -> None:
    value = _validate_number(message.text, 10, 30)
    if value is None:
        await message.answer(get_input_error_text("number"))
        return
    if value == -1:
        await message.answer(get_input_error_text("number"))
        return
    await state.update_data(wrist_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_sitting_height)
    await message.answer(
        _ask_number("sitting"),
        reply_markup=_two_col_keyboard([BUTTON_SKIP_SITTING, BUTTON_HOME_MENU]),
    )


@router.message(QuickDiagnosticsStates.waiting_for_sitting_height)
async def q_sitting(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt == BUTTON_SKIP_SITTING:
        await state.update_data(sitting_height_cm=None)
    else:
        value = _validate_number(txt, 50, 150)
        if value is None:
            await message.answer(get_input_error_text("number"))
            return
        if value == -1:
            await message.answer(get_input_error_text("number"))
            return
        await state.update_data(sitting_height_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_goal)
    await message.answer(get_question_text("goal"), reply_markup=_single_col_keyboard(GOALS + [BUTTON_HOME_MENU]))


@router.message(QuickDiagnosticsStates.waiting_for_goal)
async def q_goal(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt not in GOALS:
        await message.answer(get_input_error_text("choice_button"))
        return
    await state.update_data(goal=txt)
    await state.set_state(QuickDiagnosticsStates.waiting_for_activity)
    await message.answer(get_question_text("activity"), reply_markup=_single_col_keyboard(ACTIVITY_OPTIONS + [BUTTON_HOME_MENU]))


@router.message(QuickDiagnosticsStates.waiting_for_activity)
async def q_activity(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt not in ACTIVITY_OPTIONS:
        await message.answer(get_input_error_text("choice_button"))
        return
    await state.update_data(activity_level=txt)
    await state.set_state(QuickDiagnosticsStates.waiting_for_workouts)
    await message.answer(get_question_text("workouts"), reply_markup=_two_col_keyboard(WORKOUT_OPTIONS + [BUTTON_HOME_MENU]))


@router.message(QuickDiagnosticsStates.waiting_for_workouts)
async def q_workouts(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt not in WORKOUT_OPTIONS:
        await message.answer(get_input_error_text("choice_button"))
        return
    await state.update_data(workouts_per_week=txt)
    await state.set_state(QuickDiagnosticsStates.waiting_for_health_limits)
    await message.answer(get_question_text("health_limits"), reply_markup=_two_col_keyboard(HEALTH_LIMIT_OPTIONS + [BUTTON_HOME_MENU]))


@router.message(QuickDiagnosticsStates.waiting_for_health_limits)
async def q_limits(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt not in HEALTH_LIMIT_OPTIONS:
        await message.answer(get_input_error_text("choice_button"))
        return
    await state.update_data(health_limit_flag=txt)
    if txt == "Да":
        await state.set_state(QuickDiagnosticsStates.waiting_for_health_details)
        await message.answer(get_question_text("health_details"))
        return
    await state.update_data(health_notes="—")
    await state.set_state(QuickDiagnosticsStates.waiting_for_pressure)
    await message.answer(
        get_question_text("pressure"),
        reply_markup=_two_col_keyboard([BUTTON_SKIP_PRESSURE, BUTTON_HOME_MENU]),
    )


@router.message(QuickDiagnosticsStates.waiting_for_health_details)
async def q_limits_details(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if len(txt) < 2:
        await message.answer(get_input_error_text("text_required"))
        return
    await state.update_data(health_notes=txt)
    await state.set_state(QuickDiagnosticsStates.waiting_for_pressure)
    await message.answer(
        get_question_text("pressure"),
        reply_markup=_two_col_keyboard([BUTTON_SKIP_PRESSURE, BUTTON_HOME_MENU]),
    )


@router.message(QuickDiagnosticsStates.waiting_for_pressure)
async def q_pressure(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt == BUTTON_SKIP_PRESSURE:
        await state.update_data(pressure_text=None)
    else:
        pressure = _parse_pressure(txt)
        if pressure is None:
            await message.answer(get_input_error_text("pressure_format"))
            return
        await state.update_data(pressure_text=f"{pressure[0]}/{pressure[1]}")

    data = await state.get_data()
    if data.get("sex") == "female":
        await state.set_state(QuickDiagnosticsStates.waiting_for_pregnancy)
        await message.answer(get_question_text("pregnancy"), reply_markup=_two_col_keyboard(PREGNANCY_OPTIONS + [BUTTON_HOME_MENU]))
        return
    await state.update_data(pregnancy_status="Не применимо")
    await state.set_state(QuickDiagnosticsStates.waiting_for_consultation)
    await message.answer(
        get_question_text("consultation"),
        reply_markup=_two_col_keyboard([BUTTON_CONSULT_YES, BUTTON_CONSULT_NO]),
    )


@router.message(QuickDiagnosticsStates.waiting_for_pregnancy)
async def q_pregnancy(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt not in PREGNANCY_OPTIONS:
        await message.answer(get_input_error_text("choice_button"))
        return
    await state.update_data(pregnancy_status=txt)
    await state.set_state(QuickDiagnosticsStates.waiting_for_consultation)
    await message.answer(
        get_question_text("consultation"),
        reply_markup=_two_col_keyboard([BUTTON_CONSULT_YES, BUTTON_CONSULT_NO]),
    )


@router.message(QuickDiagnosticsStates.waiting_for_consultation)
async def q_consult(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt not in {BUTTON_CONSULT_YES, BUTTON_CONSULT_NO}:
        await message.answer(get_input_error_text("choice_button"))
        return

    wants_consultation = txt == BUTTON_CONSULT_YES
    await state.update_data(wants_consultation=wants_consultation)

    if wants_consultation:
        await message.answer(
            "Откройте direct по кнопке ниже и напишите ваш вопрос.",
            reply_markup=get_instagram_dm_keyboard(),
        )

    await _finish_diagnostics(message, state)


def _calculate_payload(profile: dict) -> dict:
    body_bmi = bmi(profile["height_cm"], profile["weight_kg"])
    body_type = somatotype(profile["sex"], profile["wrist_cm"])
    chest_idx = chest_index(profile["chest_cm"], profile["height_cm"])
    limb_idx = limb_index(profile["height_cm"], profile.get("sitting_height_cm"))
    body_whr = whr(profile["waist_cm"], profile["hips_cm"])
    ideal = ideal_weight_by_body_type(profile["height_cm"], profile["sex"], body_type)

    sex_coeff = 1.0 if profile["sex"] == "мужчина" else 0.9
    bmr_value = round(sex_coeff * profile["weight_kg"] * 24 * 0.95, 2)
    tdc_value = tdc(bmr_value, ACTIVITY_COEFFS[profile["activity_level"]])
    macros = bju_distribution(tdc_value=tdc_value, protein_share=0.2, fat_share=0.3)

    return {
        "bmi": body_bmi,
        "bmi_status": bmi_interpretation(body_bmi, int(profile["age"])),
        "body_type": body_type,
        "chest_index": chest_idx,
        "chest_index_status": chest_index_interpretation(chest_idx, profile["sex"]),
        "limb_index": limb_idx,
        "limb_index_status": limb_index_interpretation(limb_idx),
        "ideal_weight": ideal,
        "whr": body_whr,
        "whr_status": whr_interpretation(body_whr, profile["sex"]),
        "bmr": bmr_value,
        "tdc": tdc_value,
        "macros": macros,
    }


def _ideal_weight_text(ideal_weight: float | tuple[float, float, float]) -> str:
    if isinstance(ideal_weight, tuple):
        return f"{_safe_number(ideal_weight[0])}–{_safe_number(ideal_weight[2])} кг"
    return f"{_safe_number(ideal_weight)} кг"


def _build_report_text(profile: dict, payload: dict) -> str:
    goal_text = profile.get("goal") or "—"
    goal_type = _normalize_goal(goal_text)
    target_calories = _calculate_goal_calories(payload["tdc"], goal_type)
    macros = _goal_macros(profile["weight_kg"], target_calories, goal_type)

    blocks = [
        _client_data_block(profile, goal_text),
        _goal_explanation_block(goal_type),
        _metrics_interpretation_block(payload),
        _calories_block(payload, goal_type, target_calories),
        _macros_block(macros, goal_type),
        _attention_block(goal_type),
        _trainer_discussion_block(goal_type),
        _pain_point_block(goal_type),
        _cta_block(),
        _disclaimer_block(profile),
    ]
    parts = []
    for block in blocks:
        parts.append("\n".join(block))
    return get_final_report_text(profile, {
        "goal_block": parts[1],
        "metrics_block": parts[2],
        "calories_block": parts[3],
        "macros_block": parts[4],
        "attention_block": parts[5] + "\n\n" + parts[6],
        "pain_point_block": parts[7],
    })


def _build_admin_report(message: Message, profile: dict, payload: dict) -> str:
    username = f"@{message.from_user.username}" if message.from_user.username else "—"
    return (
        "🧪 Новая фитнес-диагностика\n\n"
        "Пользователь:\n"
        f"Имя: {profile.get('full_name') or '—'}\n"
        f"Telegram: {username}\n"
        f"User ID: {message.from_user.id}\n\n"
        "Данные:\n"
        f"Пол: {_sex_label(profile.get('sex')) if profile.get('sex') else '—'}\n"
        f"Возраст: {profile.get('age') or '—'}\n"
        f"Рост/вес: {_safe_number(profile.get('height_cm'))} / {_safe_number(profile.get('weight_kg'))}\n"
        f"Талия/бёдра: {_safe_number(profile.get('waist_cm'))} / {_safe_number(profile.get('hips_cm'))}\n"
        f"Грудь: {_safe_number(profile.get('chest_cm'))}\n"
        f"Запястье: {_safe_number(profile.get('wrist_cm'))}\n"
        f"Цель: {profile.get('goal') or '—'}\n"
        f"Активность: {profile.get('activity_level') or '—'}\n"
        f"Ограничения: {profile.get('health_notes') or '—'}\n\n"
        "Расчёты:\n"
        f"ИМТ: {_safe_number(payload['bmi'])}\n"
        f"Категория: {payload['bmi_status']}\n"
        f"Ориентир по весу: {_ideal_weight_text(payload['ideal_weight'])}\n"
        f"WHR: {_safe_number(payload['whr'])}\n"
        f"Тип жироотложения: {payload['whr_status']}\n"
        f"Тип телосложения: {payload['body_type']}\n\n"
        "Контакт:\n"
        "Пользователь может написать Лене: @Al0PBEDA"
    )


async def _finish_diagnostics(message: Message, state: FSMContext) -> None:
    raw = await state.get_data()
    profile = {
        "full_name": raw.get("full_name"),
        "sex": raw.get("sex"),
        "age": raw.get("age"),
        "height_cm": raw.get("height_cm"),
        "weight_kg": raw.get("weight_kg"),
        "waist_cm": raw.get("waist_cm"),
        "hips_cm": raw.get("hips_cm"),
        "chest_cm": raw.get("chest_cm"),
        "wrist_cm": raw.get("wrist_cm"),
        "sitting_height_cm": raw.get("sitting_height_cm"),
        "goal": raw.get("goal"),
        "activity_level": raw.get("activity_level"),
        "workouts_per_week": raw.get("workouts_per_week"),
        "health_limit_flag": raw.get("health_limit_flag"),
        "health_notes": raw.get("health_notes"),
        "pressure_text": raw.get("pressure_text"),
        "pregnancy_status": raw.get("pregnancy_status"),
        "wants_consultation": raw.get("wants_consultation"),
    }
    try:
        payload = _calculate_payload(profile)
    except ValueError as exc:
        if "Unknown sex" in str(exc):
            logger.warning("Unknown sex value in diagnostics profile: %r", profile.get("sex"))
            await state.set_state(QuickDiagnosticsStates.waiting_for_sex)
            await message.answer(
                "Не удалось определить пол. Пожалуйста, выберите пол ещё раз.",
                reply_markup=_two_col_keyboard([BUTTON_SEX_WOMAN, BUTTON_SEX_MAN]),
            )
            return
        raise
    await message.answer(get_intermediate_processing_text())
    report_text = _build_report_text(profile, payload)

    db, user_id = await _user_context(message)
    db.upsert_diagnostic_profile(
        {
            "user_id": user_id,
            "telegram_id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
        },
        {
            **profile,
            "latest_body_metrics_payload": payload,
            "latest_calories_payload": {
                "bmr": payload["bmr"],
                "tdc": payload["tdc"],
                "macros": payload["macros"],
            },
            "latest_report_text": report_text,
        },
    )
    db.save_calculation_history(user_id, "unified_diagnostics", payload)

    await message.answer(report_text, reply_markup=get_contact_trainer_keyboard())
    await message.answer("Данные сохранены. Меню результатов:", reply_markup=get_post_diagnostics_keyboard())
    await state.clear()

    admin_text = _build_admin_report(message, profile, payload)
    try:
        await message.bot.send_message(load_settings().admin_id, admin_text)
    except Exception:
        pass


@router.message(F.text == BUTTON_RESULT_MY_DATA)
async def show_my_data(message: Message) -> None:
    db = Database()
    profile = db.get_latest_profile_or_none(message.from_user.id)
    if not profile:
        await message.answer("Данные пока не заполнены. Нажмите «🧪 Фитнес-диагностика».", reply_markup=get_main_menu_keyboard())
        return

    text = (
        "👤 Ваши данные:\n"
        f"Имя: {profile.get('full_name') or '—'}\n"
        f"Пол: {_sex_label(profile.get('sex')) if profile.get('sex') else '—'}\n"
        f"Возраст: {profile.get('age') or '—'}\n"
        f"Рост: {_safe_number(profile.get('height_cm'))}\n"
        f"Вес: {_safe_number(profile.get('weight_kg'))}\n"
        f"Талия: {_safe_number(profile.get('waist_cm'))}\n"
        f"Бёдра: {_safe_number(profile.get('hips_cm'))}\n"
        f"Грудь: {_safe_number(profile.get('chest_cm'))}\n"
        f"Запястье: {_safe_number(profile.get('wrist_cm'))}\n"
        f"Рост сидя: {_safe_number(profile.get('sitting_height_cm'))}\n"
        f"Цель: {profile.get('goal') or '—'}\n"
        f"Активность: {profile.get('activity_level') or '—'}\n"
        f"Тренировок в неделю: {profile.get('workouts_per_week') or '—'}\n"
        f"Ограничения/здоровье: {profile.get('health_notes') or '—'}\n"
        f"Давление: {profile.get('pressure_text') or '—'}\n"
        f"Беременность: {profile.get('pregnancy_status') or '—'}"
    )
    await message.answer(text, reply_markup=get_post_diagnostics_keyboard())


@router.message(F.text == BUTTON_RESULT_REPORT)
async def show_final_report(message: Message) -> None:
    db = Database()
    profile = db.get_latest_profile_or_none(message.from_user.id)
    if not profile:
        await message.answer("Нет сохранённой диагностики. Нажмите «🧪 Фитнес-диагностика».", reply_markup=get_main_menu_keyboard())
        return
    report_text = profile.get("latest_report_text")
    if not report_text:
        payload = _calculate_payload(profile)
        report_text = _build_report_text(profile, payload)
        db.update_diagnostic_profile_fields(message.from_user.id, {"latest_report_text": report_text})

    await message.answer(report_text, reply_markup=get_contact_trainer_keyboard())
    await message.answer("Меню результатов:", reply_markup=get_post_diagnostics_keyboard())
