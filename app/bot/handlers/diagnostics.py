"""Unified fitness diagnostics flow and result views."""

from __future__ import annotations

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
    get_existing_profile_actions_keyboard,
    get_main_menu_keyboard,
    get_post_diagnostics_keyboard,
)
from app.bot.states import QuickDiagnosticsStates
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

GOALS = [
    "Похудеть",
    "Улучшить здоровье",
    "Начать тренироваться с нуля",
    "Подтянуть тело",
    "Набрать мышечную массу",
    "Улучшить выносливость",
    "Другое",
]
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


def _normalize_sex(sex_text: str) -> str:
    return "женщина" if sex_text == BUTTON_SEX_WOMAN else "мужчина"


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
    prompts = {
        "age": "Введите возраст. Например: 34",
        "height": "Введите рост в сантиметрах. Например: 168",
        "weight": "Введите вес в килограммах. Например: 64",
        "waist": "Введите обхват талии в сантиметрах. Например: 72",
        "hips": "Введите обхват бёдер в сантиметрах. Например: 98",
        "chest": "Введите обхват грудной клетки в сантиметрах. Например: 92",
        "wrist": "Введите обхват запястья в сантиметрах. Например: 16",
        "sitting": "Введите рост сидя в сантиметрах. Например: 90",
    }
    return prompts[field]


async def _start_questionnaire(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(QuickDiagnosticsStates.waiting_for_name)
    await message.answer(
        "Сейчас я задам несколько вопросов, чтобы собрать первичные данные и подготовить фитнес-отчёт. "
        "Это не медицинский диагноз, а предварительная оценка для дальнейшей работы с тренером."
    )
    await message.answer("Как вас зовут?")


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
        await message.answer("Введите имя текстом. Например: Анна")
        return
    await state.update_data(full_name=full_name)
    await state.set_state(QuickDiagnosticsStates.waiting_for_sex)
    await message.answer("Выберите пол:", reply_markup=_two_col_keyboard([BUTTON_SEX_WOMAN, BUTTON_SEX_MAN]))


@router.message(QuickDiagnosticsStates.waiting_for_sex)
async def q_sex(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt not in {BUTTON_SEX_WOMAN, BUTTON_SEX_MAN}:
        await message.answer("Пожалуйста, выберите вариант кнопкой.")
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
        await message.answer("Не получилось распознать значение. Введите только число, например: 34")
        return
    if value == -1:
        await message.answer("Похоже, значение введено с ошибкой. Проверьте и введите ещё раз.")
        return
    await state.update_data(age=int(value))
    await state.set_state(QuickDiagnosticsStates.waiting_for_height)
    await message.answer(_ask_number("height"))


@router.message(QuickDiagnosticsStates.waiting_for_height)
async def q_height(message: Message, state: FSMContext) -> None:
    value = _validate_number(message.text, 120, 230)
    if value is None:
        await message.answer("Не получилось распознать значение. Введите только число, например: 168")
        return
    if value == -1:
        await message.answer("Похоже, значение введено с ошибкой. Проверьте и введите ещё раз.")
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
        await message.answer("Не получилось распознать значение. Введите только число, например: 64")
        return
    if value == -1:
        await message.answer("Похоже, значение введено с ошибкой. Проверьте и введите ещё раз.")
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
        await message.answer("Не получилось распознать значение. Введите только число, например: 72")
        return
    if value == -1:
        await message.answer("Похоже, значение введено с ошибкой. Проверьте и введите ещё раз.")
        return
    await state.update_data(waist_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_hips)
    await message.answer(_ask_number("hips"))


@router.message(QuickDiagnosticsStates.waiting_for_hips)
async def q_hips(message: Message, state: FSMContext) -> None:
    value = _validate_number(message.text, 40, 220)
    if value is None:
        await message.answer("Не получилось распознать значение. Введите только число, например: 98")
        return
    if value == -1:
        await message.answer("Похоже, значение введено с ошибкой. Проверьте и введите ещё раз.")
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
        await message.answer("Не получилось распознать значение. Введите только число, например: 92")
        return
    if value == -1:
        await message.answer("Похоже, значение введено с ошибкой. Проверьте и введите ещё раз.")
        return
    await state.update_data(chest_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_wrist)
    await message.answer(_ask_number("wrist"))


@router.message(QuickDiagnosticsStates.waiting_for_wrist)
async def q_wrist(message: Message, state: FSMContext) -> None:
    value = _validate_number(message.text, 10, 30)
    if value is None:
        await message.answer("Не получилось распознать значение. Введите только число, например: 16")
        return
    if value == -1:
        await message.answer("Похоже, значение введено с ошибкой. Проверьте и введите ещё раз.")
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
            await message.answer("Не получилось распознать значение. Введите только число, например: 90")
            return
        if value == -1:
            await message.answer("Похоже, значение введено с ошибкой. Проверьте и введите ещё раз.")
            return
        await state.update_data(sitting_height_cm=value)
    await state.set_state(QuickDiagnosticsStates.waiting_for_goal)
    await message.answer("Выберите цель:", reply_markup=_single_col_keyboard(GOALS + [BUTTON_HOME_MENU]))


@router.message(QuickDiagnosticsStates.waiting_for_goal)
async def q_goal(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt not in GOALS:
        await message.answer("Пожалуйста, выберите цель кнопкой.")
        return
    await state.update_data(goal=txt)
    await state.set_state(QuickDiagnosticsStates.waiting_for_activity)
    await message.answer("Выберите уровень активности:", reply_markup=_single_col_keyboard(ACTIVITY_OPTIONS + [BUTTON_HOME_MENU]))


@router.message(QuickDiagnosticsStates.waiting_for_activity)
async def q_activity(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt not in ACTIVITY_OPTIONS:
        await message.answer("Пожалуйста, выберите вариант кнопкой.")
        return
    await state.update_data(activity_level=txt)
    await state.set_state(QuickDiagnosticsStates.waiting_for_workouts)
    await message.answer("Сколько тренировок в неделю?", reply_markup=_two_col_keyboard(WORKOUT_OPTIONS + [BUTTON_HOME_MENU]))


@router.message(QuickDiagnosticsStates.waiting_for_workouts)
async def q_workouts(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt not in WORKOUT_OPTIONS:
        await message.answer("Пожалуйста, выберите вариант кнопкой.")
        return
    await state.update_data(workouts_per_week=txt)
    await state.set_state(QuickDiagnosticsStates.waiting_for_health_limits)
    await message.answer("Есть ли ограничения по здоровью?", reply_markup=_two_col_keyboard(HEALTH_LIMIT_OPTIONS + [BUTTON_HOME_MENU]))


@router.message(QuickDiagnosticsStates.waiting_for_health_limits)
async def q_limits(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt not in HEALTH_LIMIT_OPTIONS:
        await message.answer("Пожалуйста, выберите вариант кнопкой.")
        return
    await state.update_data(health_limit_flag=txt)
    if txt == "Да":
        await state.set_state(QuickDiagnosticsStates.waiting_for_health_details)
        await message.answer("Коротко опишите ограничения по здоровью текстом.")
        return
    await state.update_data(health_notes="—")
    await state.set_state(QuickDiagnosticsStates.waiting_for_pressure)
    await message.answer(
        "Если знаете, введите давление в формате 120/80",
        reply_markup=_two_col_keyboard([BUTTON_SKIP_PRESSURE, BUTTON_HOME_MENU]),
    )


@router.message(QuickDiagnosticsStates.waiting_for_health_details)
async def q_limits_details(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if len(txt) < 2:
        await message.answer("Введите короткое описание ограничений текстом.")
        return
    await state.update_data(health_notes=txt)
    await state.set_state(QuickDiagnosticsStates.waiting_for_pressure)
    await message.answer(
        "Если знаете, введите давление в формате 120/80",
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
            await message.answer("Не получилось распознать значение. Пример: 120/80")
            return
        await state.update_data(pressure_text=f"{pressure[0]}/{pressure[1]}")

    data = await state.get_data()
    if data.get("sex") == "женщина":
        await state.set_state(QuickDiagnosticsStates.waiting_for_pregnancy)
        await message.answer("Беременность?", reply_markup=_two_col_keyboard(PREGNANCY_OPTIONS + [BUTTON_HOME_MENU]))
        return
    await state.update_data(pregnancy_status="Не применимо")
    await state.set_state(QuickDiagnosticsStates.waiting_for_consultation)
    await message.answer(
        "Хотите бесплатную консультацию / задать вопрос тренеру?",
        reply_markup=_single_col_keyboard([BUTTON_CONSULT_YES, BUTTON_CONSULT_NO, BUTTON_HOME_MENU]),
    )


@router.message(QuickDiagnosticsStates.waiting_for_pregnancy)
async def q_pregnancy(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt not in PREGNANCY_OPTIONS:
        await message.answer("Пожалуйста, выберите вариант кнопкой.")
        return
    await state.update_data(pregnancy_status=txt)
    await state.set_state(QuickDiagnosticsStates.waiting_for_consultation)
    await message.answer(
        "Хотите бесплатную консультацию / задать вопрос тренеру?",
        reply_markup=_single_col_keyboard([BUTTON_CONSULT_YES, BUTTON_CONSULT_NO, BUTTON_HOME_MENU]),
    )


@router.message(QuickDiagnosticsStates.waiting_for_consultation)
async def q_consult(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if txt not in {BUTTON_CONSULT_YES, BUTTON_CONSULT_NO}:
        await message.answer("Пожалуйста, выберите вариант кнопкой.")
        return
    await state.update_data(wants_consultation=txt == BUTTON_CONSULT_YES)
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
    lines = [
        "📊 <b>Итоговый фитнес-отчёт</b>",
        "",
        "👤 <b>Ваши данные:</b>",
        f"Имя: {profile.get('full_name') or '—'}",
        f"Пол: {profile.get('sex') or '—'}",
        f"Возраст: {profile.get('age') or '—'}",
        f"Рост: {_safe_number(profile.get('height_cm'))} см",
        f"Вес: {_safe_number(profile.get('weight_kg'))} кг",
        f"Цель: {profile.get('goal') or '—'}",
        "",
        "🧮 <b>Расчёты:</b>",
        f"ИМТ: {_safe_number(payload['bmi'])}",
        f"Категория ИМТ: {payload['bmi_status']}",
        f"Ориентир по весу: {_ideal_weight_text(payload['ideal_weight'])}",
        f"Тип телосложения: {payload['body_type']}",
        f"Соотношение талия/бёдра: {_safe_number(payload['whr'])}",
        f"Тип жироотложения: {payload['whr_status']}",
        f"Калории: {_safe_number(payload['tdc'])} ккал/сутки",
        (
            "БЖУ: "
            f"Б {_safe_number(payload['macros']['protein_g'])} г / "
            f"Ж {_safe_number(payload['macros']['fat_g'])} г / "
            f"У {_safe_number(payload['macros']['carbs_g'])} г"
        ),
        "",
        "⚠️ <b>Ограничения:</b>",
        f"{profile.get('health_notes') or 'Не указаны'}",
        "",
        "📌 <b>Предварительный вывод:</b>",
        "• Показатели дают стартовую картину для безопасного начала тренировок.",
        "• Для результата важно синхронизировать нагрузку, питание и восстановление.",
        "• При ограничениях по здоровью нагрузку повышайте только постепенно.",
        "",
        "💬 <b>Что обсудить с тренером:</b>",
        "• цель;",
        "• ограничения по здоровью;",
        "• безопасный уровень нагрузки;",
        "• питание;",
        "• частоту тренировок;",
        "• индивидуальный план.",
        "",
        "⚠️ <b>Важно:</b>",
        "Это предварительная оценка. Бот не ставит диагноз и не заменяет врача или тренера.",
        "",
        "Если хотите разобрать свою ситуацию точнее — напишите Лене. У каждого человека разные цели, ограничения и стартовый уровень.",
    ]
    return "\n".join(lines)


def _build_admin_report(message: Message, profile: dict, payload: dict) -> str:
    username = f"@{message.from_user.username}" if message.from_user.username else "—"
    return (
        "🧪 Новая фитнес-диагностика\n\n"
        "Пользователь:\n"
        f"Имя: {profile.get('full_name') or '—'}\n"
        f"Telegram: {username}\n"
        f"User ID: {message.from_user.id}\n\n"
        "Данные:\n"
        f"Пол: {profile.get('sex') or '—'}\n"
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
    payload = _calculate_payload(profile)
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

    await message.answer("Данные сохранены. Теперь можно посмотреть итоговый отчёт.", reply_markup=get_post_diagnostics_keyboard())
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
        f"Пол: {profile.get('sex') or '—'}\n"
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
