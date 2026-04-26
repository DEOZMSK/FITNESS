"""Unified diagnostics handlers based on a single user profile."""

from __future__ import annotations

import logging
import math

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.keyboards import (
    BUTTON_BODY_CALC,
    BUTTON_CALIPER,
    BUTTON_CALORIES,
    BUTTON_CONTRAINDICATIONS,
    BUTTON_DIAGNOSTICS,
    BUTTON_FINAL_REPORT,
    BUTTON_FLEXIBILITY,
    BUTTON_HOME_MENU,
    BUTTON_PROFILE_START,
    BUTTON_SKIP,
    get_contact_trainer_keyboard,
    get_diagnostics_menu_keyboard,
    get_main_menu_keyboard,
    get_scenario_skip_keyboard,
)
from app.bot.states import (
    CaliperStates,
    CaloriesStates,
    ContraindicationsStates,
    FlexibilityStates,
    QuickDiagnosticsStates,
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
from app.calculators.caliper import coach_caliper_estimate
from app.calculators.calories import bju_distribution, bmr, fat_index, per_meal, tdc
from app.calculators.flexibility import passive_shoulder_test, shoulder_girdle_test, total_flexibility_score
from app.db import Database
from app.services import send_diagnostics_summary

router = Router(name=__name__)
logger = logging.getLogger(__name__)

ACTIVITY_OPTIONS = {
    "Низкая активность": "1.2",
    "Лёгкая активность": "1.3",
    "Лёгкая активность + тренировки": "1.4",
    "Средняя активность": "1.5",
    "Тяжёлая активность": "1.6",
    "Очень тяжёлая активность": "1.7",
}


def _to_number(raw: str) -> float | None:
    try:
        return float(raw.strip().replace(",", "."))
    except ValueError:
        return None


def _valid(v: float | None, lo: float, hi: float) -> bool:
    return v is not None and lo <= v <= hi


def _normalize_sex(sex: str | None) -> str | None:
    if sex is None:
        return None
    sex_key = sex.strip().lower()
    male_values = {"м", "муж", "male", "man", "мужчина"}
    female_values = {"ж", "жен", "female", "woman", "женщина"}
    if sex_key in male_values:
        return "мужчина"
    if sex_key in female_values:
        return "женщина"
    return None


def _is_skip_text(raw_text: str | None) -> bool:
    return (raw_text or "").strip().lower() == BUTTON_SKIP.lower()


async def _user_context(message: Message) -> tuple[Database, int]:
    db = Database()
    uid = db.upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    return db, uid


async def show_diagnostics_menu_message(message: Message) -> None:
    await message.answer("🧪 Фитнес-диагностика\nВыберите раздел:", reply_markup=get_diagnostics_menu_keyboard())


@router.message(F.text == BUTTON_DIAGNOSTICS)
async def diagnostics_menu(message: Message) -> None:
    await show_diagnostics_menu_message(message)


@router.message(F.text == BUTTON_PROFILE_START)
async def start_profile(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(QuickDiagnosticsStates.waiting_for_name)
    await message.answer("🚀 Начать / обновить данные\nШаг 1/13: Ваше имя?")


@router.message(QuickDiagnosticsStates.waiting_for_name)
async def q_name(message: Message, state: FSMContext) -> None:
    await state.update_data(full_name=(message.text or "").strip())
    await state.set_state(QuickDiagnosticsStates.waiting_for_sex)
    await message.answer("Шаг 2/13: Пол (мужчина/женщина).")


@router.message(QuickDiagnosticsStates.waiting_for_sex)
async def q_sex(message: Message, state: FSMContext) -> None:
    normalized_sex = _normalize_sex(message.text)
    if normalized_sex is None:
        await message.answer("Не понял пол. Напишите: мужчина или женщина.")
        return
    await state.update_data(sex=normalized_sex)
    await state.set_state(QuickDiagnosticsStates.waiting_for_age)
    await message.answer("Шаг 3/13: Возраст (12–90).")


@router.message(QuickDiagnosticsStates.waiting_for_age)
async def q_age(message: Message, state: FSMContext) -> None:
    v = _to_number(message.text or "")
    if not _valid(v, 12, 90):
        await message.answer("Возраст: 12–90.")
        return
    await state.update_data(age=int(v))
    await state.set_state(QuickDiagnosticsStates.waiting_for_height)
    await message.answer("Шаг 4/13: Рост (120–230 см).")


@router.message(QuickDiagnosticsStates.waiting_for_height)
async def q_height(message: Message, state: FSMContext) -> None:
    v = _to_number(message.text or "")
    if not _valid(v, 120, 230):
        await message.answer("Рост: 120–230 см.")
        return
    await state.update_data(height_cm=v)
    await state.set_state(QuickDiagnosticsStates.waiting_for_weight)
    await message.answer("Шаг 5/13: Вес (30–250 кг).")


@router.message(QuickDiagnosticsStates.waiting_for_weight)
async def q_weight(message: Message, state: FSMContext) -> None:
    v = _to_number(message.text or "")
    if not _valid(v, 30, 250):
        await message.answer("Вес: 30–250 кг.")
        return
    await state.update_data(weight_kg=v)
    await state.set_state(QuickDiagnosticsStates.waiting_for_waist)
    await message.answer("Шаг 6/13: Талия (40–200 см).")


@router.message(QuickDiagnosticsStates.waiting_for_waist)
async def q_waist(message: Message, state: FSMContext) -> None:
    v = _to_number(message.text or "")
    if not _valid(v, 40, 200):
        await message.answer("Талия: 40–200 см.")
        return
    await state.update_data(waist_cm=v)
    await state.set_state(QuickDiagnosticsStates.waiting_for_hips)
    await message.answer("Шаг 7/13: Бёдра (40–220 см).")


@router.message(QuickDiagnosticsStates.waiting_for_hips)
async def q_hips(message: Message, state: FSMContext) -> None:
    v = _to_number(message.text or "")
    if not _valid(v, 40, 220):
        await message.answer("Бёдра: 40–220 см.")
        return
    d = await state.get_data()
    if v < float(d["waist_cm"]):
        await state.update_data(pending_hips=v)
        await state.set_state(QuickDiagnosticsStates.waiting_for_hips_confirmation)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Оставить", callback_data="hips:keep"), InlineKeyboardButton(text="✏️ Ввести заново", callback_data="hips:retry")]])
        await message.answer("Проверьте обхват бёдер. Обычно он больше обхвата талии. Оставить как есть?", reply_markup=kb)
        return
    await state.update_data(hips_cm=v)
    await state.set_state(QuickDiagnosticsStates.waiting_for_chest)
    await message.answer("Шаг 8/13: Грудная клетка (40–200 см).")


@router.callback_query(QuickDiagnosticsStates.waiting_for_hips_confirmation, F.data.in_({"hips:keep", "hips:retry"}))
async def hips_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data == "hips:retry":
        await state.set_state(QuickDiagnosticsStates.waiting_for_hips)
        await callback.message.answer("Введите бёдра снова.")
    else:
        data = await state.get_data()
        await state.update_data(hips_cm=data.get("pending_hips"))
        await state.set_state(QuickDiagnosticsStates.waiting_for_chest)
        await callback.message.answer("Шаг 8/13: Грудная клетка (40–200 см).")
    await callback.answer()


@router.message(QuickDiagnosticsStates.waiting_for_chest)
async def q_chest(message: Message, state: FSMContext) -> None:
    v = _to_number(message.text or "")
    if not _valid(v, 40, 200):
        await message.answer("Грудь: 40–200 см.")
        return
    await state.update_data(chest_cm=v)
    await state.set_state(QuickDiagnosticsStates.waiting_for_wrist)
    await message.answer("Шаг 9/13: Запястье (10–30 см).")


@router.message(QuickDiagnosticsStates.waiting_for_wrist)
async def q_wrist(message: Message, state: FSMContext) -> None:
    v = _to_number(message.text or "")
    if not _valid(v, 10, 30):
        await message.answer("Запястье: 10–30 см.")
        return
    await state.update_data(wrist_cm=v)
    await state.set_state(QuickDiagnosticsStates.waiting_for_goal)
    await message.answer("Шаг 10/13: Ваша цель?")


@router.message(QuickDiagnosticsStates.waiting_for_goal)
async def q_goal(message: Message, state: FSMContext) -> None:
    await state.update_data(goal=(message.text or "").strip())
    await state.set_state(QuickDiagnosticsStates.waiting_for_health)
    await message.answer("Шаг 11/13: Ограничения/здоровье одним текстом.")


@router.message(QuickDiagnosticsStates.waiting_for_health)
async def q_health(message: Message, state: FSMContext) -> None:
    await state.update_data(health_notes=(message.text or "").strip())
    await state.set_state(QuickDiagnosticsStates.waiting_for_sitting_height)
    await message.answer("Шаг 12/13: Рост сидя (50–150) или Пропустить.", reply_markup=get_scenario_skip_keyboard())


@router.message(QuickDiagnosticsStates.waiting_for_sitting_height, F.text.func(_is_skip_text))
async def q_sitting_skip(message: Message, state: FSMContext) -> None:
    await state.update_data(sitting_height_cm=None)
    await state.set_state(QuickDiagnosticsStates.waiting_for_known_fat)
    await message.answer("Шаг 13/13: Известный % жира (3–70) или Пропустить.", reply_markup=get_scenario_skip_keyboard())


@router.message(QuickDiagnosticsStates.waiting_for_sitting_height)
async def q_sitting(message: Message, state: FSMContext) -> None:
    v = _to_number(message.text or "")
    if not _valid(v, 50, 150):
        await message.answer("Рост сидя: 50–150 или Пропустить.")
        return
    await state.update_data(sitting_height_cm=v)
    await state.set_state(QuickDiagnosticsStates.waiting_for_known_fat)
    await message.answer("Шаг 13/13: Известный % жира (3–70) или Пропустить.", reply_markup=get_scenario_skip_keyboard())


@router.message(QuickDiagnosticsStates.waiting_for_known_fat, F.text.func(_is_skip_text))
async def q_fat_skip(message: Message, state: FSMContext) -> None:
    await state.update_data(known_fat_percent=None)
    await _finish_profile(message, state)


@router.message(QuickDiagnosticsStates.waiting_for_known_fat)
async def q_fat(message: Message, state: FSMContext) -> None:
    v = _to_number(message.text or "")
    if not _valid(v, 3, 70):
        await message.answer("% жира: 3–70 или Пропустить.")
        return
    await state.update_data(known_fat_percent=v)
    await _finish_profile(message, state)


async def _calculate_body(profile: dict) -> dict:
    b = bmi(profile["height_cm"], profile["weight_kg"])
    s = somatotype(profile["sex"], profile["wrist_cm"])
    c = chest_index(profile["chest_cm"], profile["height_cm"])
    li = limb_index(profile["height_cm"], profile.get("sitting_height_cm"))
    w = whr(profile["waist_cm"], profile["hips_cm"])
    ideal = ideal_weight_by_body_type(profile["height_cm"], profile["sex"], s)
    return {
        "bmi": b,
        "bmi_status": bmi_interpretation(b, int(profile["age"])),
        "somatotype_wrist": s,
        "chest_index": c,
        "chest_index_status": chest_index_interpretation(c, profile["sex"]),
        "limb_index": li,
        "limb_index_status": limb_index_interpretation(li),
        "ideal_weight": ideal,
        "whr": w,
        "whr_status": whr_interpretation(w, profile["sex"]),
    }


async def _finish_profile(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    db, user_id = await _user_context(message)
    profile = {**data}
    db.upsert_diagnostic_profile(
        {
            "user_id": user_id,
            "telegram_id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
        },
        profile,
    )
    body_payload = await _calculate_body(profile)
    db.save_calculation_history(user_id, "body_metrics", body_payload)
    db.update_diagnostic_profile_fields(message.from_user.id, {"latest_body_metrics_payload": body_payload})
    text = f"✅ Профиль обновлён.\nИМТ: {body_payload['bmi']} ({body_payload['bmi_status']})."
    await message.answer(text, reply_markup=get_diagnostics_menu_keyboard())
    try:
        await send_diagnostics_summary(
            bot=message.bot,
            user_id=user_id,
            lead_id=user_id,
            payload={"profile": profile, "body": body_payload},
            title="Новый/обновлённый профиль диагностики",
            lead_type="diagnosis",
            telegram_user_id=message.from_user.id,
            telegram_username=message.from_user.username,
        )
    except Exception:
        pass
    await state.clear()


@router.message(F.text == BUTTON_BODY_CALC)
async def run_body_calc(message: Message) -> None:
    db, user_id = await _user_context(message)
    profile = db.get_latest_profile_or_none(message.from_user.id)
    required = ["sex", "age", "height_cm", "weight_kg", "waist_cm", "hips_cm", "chest_cm", "wrist_cm"]
    missing = [x for x in required if profile is None or profile.get(x) in (None, "")]
    if missing:
        await message.answer("Недостаточно данных профиля. Нажмите «🚀 Начать / обновить данные».")
        return
    body = await _calculate_body(profile)
    db.save_calculation_history(user_id, "body_metrics", body)
    db.update_diagnostic_profile_fields(message.from_user.id, {"latest_body_metrics_payload": body})
    ideal = body["ideal_weight"]
    ideal_text = f"{ideal} кг" if not isinstance(ideal, tuple) else f"{ideal[0]}–{ideal[2]} кг"
    limb_text = "не рассчитывался" if body["limb_index"] is None else f"{body['limb_index']} ({body['limb_index_status']})"
    await message.answer(
        "🧮 Калькуляторы тела\n\n"
        f"ИМТ: {body['bmi']}\nКатегория: {body['bmi_status']}\n"
        f"По запястью: {body['somatotype_wrist']}\nПо грудной клетке: {body['chest_index_status']}\nПо длине конечностей: {limb_text}\n"
        f"Идеальный вес: {ideal_text}\nWHR: {body['whr']}\nТип жироотложения: {body['whr_status']}\n\n"
        "⚠️ Это предварительная оценка, не медицинский диагноз.",
        reply_markup=get_diagnostics_menu_keyboard(),
    )


@router.message(F.text == BUTTON_CALORIES)
async def start_calories(message: Message, state: FSMContext) -> None:
    db, _ = await _user_context(message)
    profile = db.get_latest_profile_or_none(message.from_user.id)
    if not profile:
        await message.answer("Сначала заполните профиль: «🚀 Начать / обновить данные».")
        return
    req = ["sex", "age", "height_cm", "weight_kg", "goal"]
    miss = [x for x in req if profile.get(x) in (None, "")]
    if miss:
        await message.answer("В профиле не хватает базовых полей. Обновите данные.")
        return
    await state.update_data(profile=profile)
    if not profile.get("activity_level"):
        await state.set_state(CaloriesStates.waiting_for_activity)
        await message.answer("Выберите активность:\n" + "\n".join(ACTIVITY_OPTIONS.keys()))
        return
    if not profile.get("meals_count"):
        await state.set_state(CaloriesStates.waiting_for_meals)
        await message.answer("Сколько приёмов пищи в день? (1–8)")
        return
    await _finish_calories(message, state, profile)


@router.message(CaloriesStates.waiting_for_activity)
async def calories_activity(message: Message, state: FSMContext) -> None:
    if (message.text or "").strip() not in ACTIVITY_OPTIONS:
        await message.answer("Выберите вариант из списка активности.")
        return
    data = await state.get_data()
    profile = data["profile"]
    profile["activity_level"] = ACTIVITY_OPTIONS[message.text.strip()]
    await state.update_data(profile=profile)
    if not profile.get("meals_count"):
        await state.set_state(CaloriesStates.waiting_for_meals)
        await message.answer("Сколько приёмов пищи в день? (1–8)")
        return
    await _finish_calories(message, state, profile)


@router.message(CaloriesStates.waiting_for_meals)
async def calories_meals(message: Message, state: FSMContext) -> None:
    v = _to_number(message.text or "")
    if not _valid(v, 1, 8):
        await message.answer("Количество приёмов пищи: 1–8.")
        return
    data = await state.get_data()
    profile = data["profile"]
    profile["meals_count"] = int(v)
    await _finish_calories(message, state, profile)


async def _finish_calories(message: Message, state: FSMContext, profile: dict) -> None:
    db, user_id = await _user_context(message)
    known_fat = profile.get("known_fat_percent")
    normalized_sex = _normalize_sex(profile.get("sex"))
    if normalized_sex is None:
        logger.warning("Calories aborted due to invalid sex in profile. user_id=%s sex=%r", message.from_user.id, profile.get("sex"))
        await state.clear()
        await message.answer(
            "В профиле некорректно указан пол. Пожалуйста, заново заполните шаг с полом: «🚀 Начать / обновить данные».",
            reply_markup=get_diagnostics_menu_keyboard(),
        )
        return
    use_fat = 0.95 if known_fat is None else fat_index(float(known_fat), normalized_sex)
    bmr_value = round((1.0 if normalized_sex == "мужчина" else 0.9) * float(profile["weight_kg"]) * 24 * use_fat, 2)
    tdc_value = tdc(bmr_value, str(profile["activity_level"]))
    macros = bju_distribution(tdc_value=tdc_value)
    meals = int(profile.get("meals_count") or 4)
    meal = per_meal(macros, meals)
    payload = {"bmr": bmr_value, "tdc": tdc_value, "macros": macros, "per_meal": meal, "meals_count": meals}
    db.save_calculation_history(user_id, "calories", payload)
    db.update_diagnostic_profile_fields(message.from_user.id, {"activity_level": profile.get("activity_level"), "meals_count": meals, "latest_calories_payload": payload})
    note = "\nРасчёт ориентировочный, потому что % жира не указан." if known_fat is None else ""
    await message.answer(
        "🔥 Калории и БЖУ\n"
        f"BMR: {bmr_value} ккал\nСуточный расход: {tdc_value} ккал\n"
        f"Белки: {macros['protein_g']} г, Жиры: {macros['fat_g']} г, Углеводы: {macros['carbs_g']} г\n"
        f"На {meals} приёма: Б {meal['protein_g']} / Ж {meal['fat_g']} / У {meal['carbs_g']} г.{note}",
        reply_markup=get_diagnostics_menu_keyboard(),
    )
    await state.clear()


@router.message(F.text == BUTTON_CALIPER)
async def caliper_start(message: Message, state: FSMContext) -> None:
    db, _ = await _user_context(message)
    profile = db.get_latest_profile_or_none(message.from_user.id)
    normalized_sex = _normalize_sex(profile.get("sex") if profile else None)
    if not profile or normalized_sex is None or not profile.get("height_cm") or not profile.get("weight_kg"):
        logger.info(
            "Caliper start rejected due to incomplete profile. user_id=%s has_profile=%s sex=%r height=%r weight=%r",
            message.from_user.id,
            bool(profile),
            profile.get("sex") if profile else None,
            profile.get("height_cm") if profile else None,
            profile.get("weight_kg") if profile else None,
        )
        await message.answer("Для калипера нужен профиль с полом/ростом/весом.")
        return
    profile["sex"] = normalized_sex
    await state.update_data(profile=profile, folds={})
    await state.set_state(CaliperStates.waiting_for_start)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Продолжить", callback_data="caliper:go"), InlineKeyboardButton(text="Назад", callback_data="caliper:back")]])
    await message.answer("Для этого расчёта нужны замеры складок. При неточных замерах результат будет неточным.", reply_markup=kb)


@router.callback_query(CaliperStates.waiting_for_start, F.data.in_({"caliper:go", "caliper:back"}))
async def caliper_go(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data == "caliper:back":
        await state.clear()
        await callback.message.answer("Окей, возвращаю в меню.", reply_markup=get_diagnostics_menu_keyboard())
    else:
        await state.update_data(fields=["forearm", "arm_front", "arm_back", "scapula", "abdomen", "thigh", "calf"])
        await state.set_state(CaliperStates.waiting_for_fold)
        await callback.message.answer("Введите складку forearm (1–100 мм).")
    await callback.answer()


@router.message(CaliperStates.waiting_for_fold)
async def caliper_fold(message: Message, state: FSMContext) -> None:
    v = _to_number(message.text or "")
    if not _valid(v, 1, 100):
        await message.answer("Введите значение 1–100 мм.")
        return
    data = await state.get_data()
    fields = data.get("fields") or []
    folds = data.get("folds") or {}
    profile = data.get("profile") or {}
    if not fields:
        logger.warning("Caliper fold state has empty fields. user_id=%s folds_len=%s", message.from_user.id, len(folds))
        await state.clear()
        await message.answer("Сценарий калипера сбился. Давайте начнём заново.", reply_markup=get_diagnostics_menu_keyboard())
        return
    if len(folds) >= len(fields):
        logger.warning(
            "Caliper fold index overflow prevented. user_id=%s folds_len=%s fields_len=%s",
            message.from_user.id,
            len(folds),
            len(fields),
        )
        await state.clear()
        await message.answer("Похоже, замеры уже заполнены. Запустите калипер ещё раз из меню.", reply_markup=get_diagnostics_menu_keyboard())
        return
    field = fields[len(folds)]
    folds[field] = v
    normalized_sex = _normalize_sex(profile.get("sex"))
    if normalized_sex is None:
        logger.warning("Caliper aborted due to invalid sex in profile. user_id=%s sex=%r", message.from_user.id, profile.get("sex"))
        await state.clear()
        await message.answer(
            "Не удалось определить пол в профиле. Пожалуйста, обновите профиль и выберите пол заново.",
            reply_markup=get_diagnostics_menu_keyboard(),
        )
        return
    male = normalized_sex == "мужчина"
    if len(folds) == len(fields):
        if male and "chest" not in folds:
            folds["chest"] = 10.0
        try:
            result = coach_caliper_estimate(
                sex=normalized_sex,
                age=int(profile.get("age") or 30),
                height_cm=float(profile["height_cm"]),
                weight_kg=float(profile["weight_kg"]),
                **folds,
            )
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Caliper estimate failed. user_id=%s sex=%r age=%r has_height=%s has_weight=%s folds_keys=%s error=%s",
                message.from_user.id,
                profile.get("sex"),
                profile.get("age"),
                bool(profile.get("height_cm")),
                bool(profile.get("weight_kg")),
                sorted(folds.keys()),
                exc,
            )
            await state.clear()
            await message.answer(
                "Не удалось посчитать калипер из-за неполных данных профиля. Обновите профиль и попробуйте снова.",
                reply_markup=get_diagnostics_menu_keyboard(),
            )
            return
        db, user_id = await _user_context(message)
        db.save_calculation_history(user_id, "caliper", result)
        db.update_diagnostic_profile_fields(message.from_user.id, {"caliper_payload": result, "known_fat_percent": result["fat_percent"]})
        await state.clear()
        await message.answer(f"📏 Калипер\n% жира: {result['fat_percent']}\nLBM: {result['lbm_kg']} кг\nСтатус: {result['fat_percent_status']}", reply_markup=get_diagnostics_menu_keyboard())
        return
    await state.update_data(folds=folds)
    await message.answer(f"Введите складку {fields[len(folds)]} (1–100 мм).")


@router.message(F.text == BUTTON_FLEXIBILITY)
async def flexibility_start(message: Message, state: FSMContext) -> None:
    await state.set_state(FlexibilityStates.waiting_for_test_1)
    await message.answer("Тест 1: Ладони касаются / Пальцы касаются / До 3 см / > 4 см")


@router.message(FlexibilityStates.waiting_for_test_1)
async def flex_test_1(message: Message, state: FSMContext) -> None:
    res = shoulder_girdle_test((message.text or "").strip())
    if res["points"] == 0:
        await message.answer("Введите один из вариантов теста 1.")
        return
    await state.update_data(test1=res)
    await state.set_state(FlexibilityStates.waiting_for_test_2)
    await message.answer("Тест 2: расстояние между кистями (см).")


@router.message(FlexibilityStates.waiting_for_test_2)
async def flex_test_2(message: Message, state: FSMContext) -> None:
    v = _to_number(message.text or "")
    if v is None or v <= 0:
        await message.answer("Введите расстояние в см.")
        return
    t2 = passive_shoulder_test(v)
    data = await state.get_data()
    score = total_flexibility_score(int(data["test1"]["points"]), int(t2["points"]))
    payload = {"test1": data["test1"], "test2": t2, "total": score}
    db, user_id = await _user_context(message)
    db.save_calculation_history(user_id, "flexibility", payload)
    db.update_diagnostic_profile_fields(message.from_user.id, {"flexibility_payload": payload})
    await state.clear()
    await message.answer(f"🧍 Гибкость\nИтог: {score['total_points']} баллов — {score['label']}", reply_markup=get_diagnostics_menu_keyboard())


QUESTIONS = [
    "Есть ли серьёзные заболевания сердца или изменения ЭКГ?",
    "Был ли недавно инфаркт, стенокардия, серьёзная аритмия?",
    "Есть ли тромбоз, тромбофлебит или эмболия?",
    "Есть ли острые инфекции?",
    "Есть ли нарушения ОДА/ревматоидные/мышечно-скелетные проблемы?",
    "Давление выше 150/100?",
    "Есть ли беременность во второй половине или осложнённая беременность?",
]


@router.message(F.text == BUTTON_CONTRAINDICATIONS)
async def contraindications_start(message: Message, state: FSMContext) -> None:
    await state.update_data(i=0, answers=[])
    await state.set_state(ContraindicationsStates.waiting_for_answer)
    await message.answer(f"🛡 Противопоказания\n{QUESTIONS[0]}\nОтвет: да/нет")


@router.message(ContraindicationsStates.waiting_for_answer)
async def contraindications_answer(message: Message, state: FSMContext) -> None:
    ans = (message.text or "").strip().lower()
    if ans not in {"да", "нет"}:
        await message.answer("Ответьте «да» или «нет».")
        return
    data = await state.get_data()
    i = int(data.get("i", 0))
    answers = data.get("answers") or []
    if i < 0 or i >= len(QUESTIONS):
        logger.warning("Contraindications state index is invalid. user_id=%s i=%s answers_len=%s", message.from_user.id, i, len(answers))
        await state.clear()
        await message.answer(
            "Сценарий опроса сбился. Запустите раздел «Противопоказания» ещё раз.",
            reply_markup=get_diagnostics_menu_keyboard(),
        )
        return
    answers.append({"q": QUESTIONS[i], "a": ans})
    i += 1
    if i >= len(QUESTIONS):
        flagged = any(x["a"] == "да" for x in answers)
        payload = {"answers": answers, "flagged": flagged}
        db, _ = await _user_context(message)
        db.update_diagnostic_profile_fields(message.from_user.id, {"contraindications_payload": payload})
        await state.clear()
        text = (
            "По вашим ответам сейчас не стоит проходить тестирование без разрешения врача."
            if flagged
            else "Критичных стоп-факторов по анкете не отмечено."
        )
        await message.answer(text, reply_markup=get_diagnostics_menu_keyboard())
        return
    await state.update_data(i=i, answers=answers)
    await message.answer(f"{QUESTIONS[i]}\nОтвет: да/нет")


@router.message(F.text == BUTTON_FINAL_REPORT)
async def final_report(message: Message) -> None:
    db, _ = await _user_context(message)
    p = db.get_latest_profile_or_none(message.from_user.id)
    if not p:
        await message.answer("Нет профиля. Нажмите «🚀 Начать / обновить данные».")
        return
    body = p.get("latest_body_metrics_payload") or "Не рассчитывались"
    cal = p.get("latest_calories_payload") or "Не рассчитывались"
    caliper = p.get("caliper_payload") or "Не рассчитывался"
    flex = p.get("flexibility_payload") or "Не проходилась"
    contra = p.get("contraindications_payload") or "Не проходились"
    await message.answer(
        "📊 Итоговый отчёт\n"
        f"👤 {p.get('full_name')}, {p.get('age')} лет, {p.get('sex')}, {p.get('height_cm')} см/{p.get('weight_kg')} кг\n"
        f"Цель: {p.get('goal')}\n\n"
        f"🧮 Тело: {body}\n\n🔥 Калории и БЖУ: {cal}\n\n📏 Состав тела: {caliper}\n\n🧍 Гибкость: {flex}\n\n🛡 Противопоказания: {contra}\n\n"
        "Если хотите разобрать ситуацию точнее — напишите Лене.",
        reply_markup=get_contact_trainer_keyboard(),
    )
