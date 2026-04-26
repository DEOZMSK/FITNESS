"""Handlers package and router registry."""

from aiogram import Router

from .about import router as about_router
from .diagnostics import router as diagnostics_router
from .results import router as results_router
from .start import router as start_router

router = Router(name=__name__)
router.include_router(start_router)
router.include_router(about_router)
router.include_router(diagnostics_router)
router.include_router(results_router)

__all__ = ("router",)
