"""
Encoding detection for uploaded files.
"""
from pathlib import Path
from typing import Optional

import chardet

from backend.utils.logger import setup_logger

logger = setup_logger("sdo.encoding")

# Fallback chain when chardet is uncertain
_FALLBACK_ENCODINGS = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]


def detect_encoding(file_path: str, sample_bytes: int = 10_000) -> str:
    """
    Detect the character encoding of a file.

    Reads up to `sample_bytes` from the file and uses chardet to guess
    the encoding.  Falls back to 'utf-8' if detection confidence is low.

    Args:
        file_path: Path to the file.
        sample_bytes: Number of bytes to sample.

    Returns:
        Detected encoding string (e.g. 'utf-8', 'latin-1').
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning("File not found for encoding detection: %s", file_path)
        return "utf-8"

    try:
        with open(path, "rb") as fh:
            raw = fh.read(sample_bytes)

        result = chardet.detect(raw)
        encoding: Optional[str] = result.get("encoding")
        confidence: float = result.get("confidence", 0.0)

        if encoding and confidence >= 0.7:
            logger.debug(
                "Detected encoding '%s' (confidence %.2f) for %s",
                encoding, confidence, path.name
            )
            return encoding

        # Low-confidence — try fallback
        for enc in _FALLBACK_ENCODINGS:
            try:
                raw.decode(enc)
                logger.debug(
                    "Falling back to encoding '%s' for %s (chardet confidence %.2f)",
                    enc, path.name, confidence
                )
                return enc
            except (UnicodeDecodeError, LookupError):
                continue

    except OSError as exc:
        logger.error("Could not read file for encoding detection: %s — %s", file_path, exc)

    return "utf-8"


def verify_encoding(file_path: str, encoding: str) -> bool:
    """
    Verify that a file can be decoded with the given encoding.

    Args:
        file_path: Path to the file.
        encoding: Encoding to verify.

    Returns:
        True if the file is readable with the given encoding.
    """
    try:
        with open(file_path, "r", encoding=encoding, errors="strict") as fh:
            fh.read(1024)
        return True
    except (UnicodeDecodeError, LookupError, OSError):
        return False
