"""Vercel FastAPI entry point; development still uses server.app:app."""
# Serialized models import these dynamically; make the serving dependency closure explicit.
import sklearn  # noqa: F401
import shap  # noqa: F401
from server.app import app

__all__ = ['app']
