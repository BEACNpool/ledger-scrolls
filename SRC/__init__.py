# src/__init__.py

__version__ = "0.1.0-dev"  # change when you feel ready
__all__ = ["viewer", "cli", "ui"]

# Optional: make the most useful things directly importable
from .viewer import get_scrolls, reconstruct, fetch_registry_datum
