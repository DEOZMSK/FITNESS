"""FSM states for quick diagnostics flow."""

from aiogram.fsm.state import State, StatesGroup


class QuickDiagnosticsStates(StatesGroup):
    """Quick diagnostics states."""

    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_gender = State()
    waiting_for_height = State()
    waiting_for_weight = State()
    waiting_for_waist = State()
    waiting_for_hips = State()
    waiting_for_chest = State()
    waiting_for_wrist = State()
    waiting_for_sitting_height = State()
    waiting_for_goal = State()
    waiting_for_health = State()
