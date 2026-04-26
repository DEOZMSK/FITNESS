"""Keyboards package."""

from .main_menu import (
    BUTTON_ABOUT,
    BUTTON_CONTACT,
    BUTTON_DIAGNOSTICS,
    BUTTON_RESULTS,
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
    "BUTTON_ABOUT",
    "BUTTON_BACK",
    "BUTTON_CANCEL",
    "BUTTON_CONTACT",
    "BUTTON_DIAGNOSTICS",
    "BUTTON_HOME_MENU",
    "BUTTON_RESULTS",
    "BUTTON_SKIP",
    "get_main_menu_keyboard",
    "get_scenario_nav_keyboard",
    "get_scenario_skip_keyboard",
)
