"""FSM states for diagnostics flow."""

from aiogram.fsm.state import State, StatesGroup


class QuickDiagnosticsStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_sex = State()
    waiting_for_age = State()
    waiting_for_height = State()
    waiting_for_weight = State()
    waiting_for_waist = State()
    waiting_for_hips = State()
    waiting_for_hips_confirmation = State()
    waiting_for_chest = State()
    waiting_for_wrist = State()
    waiting_for_sitting_height = State()
    waiting_for_goal = State()
    waiting_for_activity = State()
    waiting_for_workouts = State()
    waiting_for_health_limits = State()
    waiting_for_health_details = State()
    waiting_for_pressure = State()
    waiting_for_pregnancy = State()
    waiting_for_consultation = State()
    waiting_for_update_confirmation = State()


class BodyCalculatorsStates(StatesGroup):
    waiting_for_missing = State()


class CaloriesStates(StatesGroup):
    waiting_for_activity = State()
    waiting_for_meals = State()
    waiting_for_known_fat = State()


class CaliperStates(StatesGroup):
    waiting_for_start = State()
    waiting_for_fold = State()


class FlexibilityStates(StatesGroup):
    waiting_for_test_1 = State()
    waiting_for_test_2 = State()


class ContraindicationsStates(StatesGroup):
    waiting_for_answer = State()
    waiting_for_pressure = State()
