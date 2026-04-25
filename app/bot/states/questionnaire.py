"""FSM states for full questionnaire flow."""

from aiogram.fsm.state import State, StatesGroup


class FullQuestionnaireStates(StatesGroup):
    """Full questionnaire states."""

    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_gender = State()
    waiting_for_height = State()
    waiting_for_weight = State()
    waiting_for_city = State()
    waiting_for_occupation = State()

    waiting_for_chronic_conditions = State()
    waiting_for_injuries = State()
    waiting_for_surgeries = State()
    waiting_for_medications = State()
    waiting_for_sleep_hours = State()
    waiting_for_stress_level = State()

    waiting_for_experience = State()
    waiting_for_activity_level = State()
    waiting_for_workouts_per_week = State()
    waiting_for_equipment = State()
    waiting_for_goal = State()
