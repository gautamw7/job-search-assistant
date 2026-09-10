"""Compat shim - use app.infra.json_store instead."""
from app.infra.json_store import *
from app.infra.json_store import load_json, save_json

__all__ = ["load_json", "save_json"]
