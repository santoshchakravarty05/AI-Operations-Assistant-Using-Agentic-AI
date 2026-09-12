"""Small, defensive helpers for accessing the project's local JSON data."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class DataStoreError(Exception):
    """Raised when local support data cannot be read or saved safely."""


def load_records(filename: str) -> list[dict[str, Any]]:
    """Load a JSON list from the data directory."""
    path = DATA_DIR / filename
    try:
        with path.open(encoding="utf-8") as file:
            records = json.load(file)
    except FileNotFoundError as error:
        raise DataStoreError(f"Required data file is missing: {filename}") from error
    except json.JSONDecodeError as error:
        raise DataStoreError(f"Data file contains invalid JSON: {filename}") from error
    except OSError as error:
        raise DataStoreError(f"Could not read data file: {filename}") from error

    if not isinstance(records, list):
        raise DataStoreError(f"Data file must contain a JSON list: {filename}")
    return records


def save_records(filename: str, records: list[dict[str, Any]]) -> None:
    """Atomically replace a JSON data file to avoid a partially written ticket list."""
    destination = DATA_DIR / filename
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=DATA_DIR, delete=False
        ) as temp_file:
            json.dump(records, temp_file, indent=2)
            temp_file.write("\n")
            temp_path = Path(temp_file.name)
        os.replace(temp_path, destination)
    except OSError as error:
        raise DataStoreError(f"Could not save data file: {filename}") from error
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
