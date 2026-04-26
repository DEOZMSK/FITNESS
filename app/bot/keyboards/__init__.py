"""Keyboards package."""

from .contact_cta import CONTACT_TRAINER_TEXT, CONTACT_TRAINER_URL, get_contact_trainer_keyboard
from .main_menu import (
    BUTTON_ABOUT,
    BUTTON_CONTACT,
    BUTTON_DIAGNOSTICS,
    BUTTON_RESULTS,
    get_diagnostics_menu_keyboard,
    get_main_menu_keyboard,
)
from .navigation import (
    BUTTON_BACK,
    BUTTON_CANCEL,
    BUTTON_HOME_MENU,
    BUTTON_SKIP,
    get_scenario_nav_keyboard,
    get_scenario_skip_keyboard,
)

__all__ = (
    "get_contact_trainer_keyboard",
    "CONTACT_TRAINER_URL",
    "CONTACT_TRAINER_TEXT",
    "BUTTON_ABOUT",
    "BUTTON_BACK",
    "BUTTON_CANCEL",
    "BUTTON_CONTACT",
    "BUTTON_DIAGNOSTICS",
    "BUTTON_HOME_MENU",
    "BUTTON_RESULTS",
    "BUTTON_SKIP",
    "get_diagnostics_menu_keyboard",
    "get_main_menu_keyboard",
    "get_scenario_nav_keyboard",
    "get_scenario_skip_keyboard",
)
