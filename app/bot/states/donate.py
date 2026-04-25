"""FSM states for donation flow."""

from aiogram.fsm.state import State, StatesGroup


class DonateStates(StatesGroup):
    """Donation flow states."""

    waiting_for_amount = State()
