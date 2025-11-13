"""Custom exceptions for the data layer pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class DataLayerError(Exception):
    """Base exception for all data-layer specific errors."""


class IFCLoadError(DataLayerError):
    """Raised when an IFC file cannot be opened."""

    def __init__(self, path: str | Path, original: Optional[BaseException] = None) -> None:
        self.path = Path(path)
        self.original = original
        message = f"Failed to load IFC file: {self.path}"
        if original is not None:
            message = f"{message} ({original})"
        super().__init__(message)


class ExtractionError(DataLayerError):
    """Raised when an error occurs during data extraction."""

    def __init__(self, element_id: Optional[str] = None, message: str = "") -> None:
        details = f"Element {element_id}: {message}" if element_id else message or "Extraction failed"
        super().__init__(details)

