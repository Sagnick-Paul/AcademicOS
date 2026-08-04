"""Version 1 API surface.

The :data:`api_router` is the single object that ``app.main`` mounts
under ``settings.API_V1_PREFIX``. Individual endpoint modules attach
themselves to it; this package itself does not import them so that
``import app.api.v1`` is side-effect free.
"""
from __future__ import annotations

from fastapi import APIRouter


api_router = APIRouter()
