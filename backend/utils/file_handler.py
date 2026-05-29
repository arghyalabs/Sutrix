"""
File ingestion engine for CSV and Excel uploads.

Handles validation, encoding detection, and multi-sheet Excel support.
All public results are returned as IngestionResult dataclasses so
callers never have to catch exceptions from this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from backend.utils.config import config
from backend.utils.encoding_detector import detect_encoding
from backend.utils.logger import setup_logger

logger = setup_logger("sdo.ingestion")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class IngestionResult:
    """Outcome of a single file ingestion attempt."""
    success: bool
    file_path: str
    sheet_names: List[str]
    dataframes: Dict[str, pd.DataFrame]
    encoding: str
    errors: List[str]
    metadata: dict = field(default_factory=dict)

    # Convenience helpers ---------------------------------------------------

    @property
    def primary_df(self) -> Optional[pd.DataFrame]:
        """Return the first (or only) dataframe, or None on failure."""
        if not self.success or not self.sheet_names:
            return None
        return self.dataframes[self.sheet_names[0]]

    @property
    def total_rows(self) -> int:
        return self.metadata.get("total_rows", 0)

    @property
    def total_cols(self) -> int:
        return self.metadata.get("total_cols", 0)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class FileIngestionEngine:
    """Validates and ingests CSV / Excel files into pandas DataFrames."""

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xlsm", ".xls"}

    def __init__(
        self,
        upload_dir: str = None,
        max_file_size_mb: int = None,
    ) -> None:
        self.upload_dir = Path(upload_dir or config.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size_mb = max_file_size_mb or config.max_file_size_mb

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self, file_path: str, file_bytes: Optional[bytes] = None, **kwargs) -> IngestionResult:
        """
        Main entry point. Validates then ingests a file (from local disk or memory stream).

        Args:
            file_path: Absolute or relative path/filename of the file.
            file_bytes: Optional raw bytes of the file to load completely in memory.
            **kwargs: Passed through to pandas read functions.

        Returns:
            IngestionResult (check `.success` before using `.dataframes`).
        """
        path = Path(file_path)
        logger.info("Ingesting file: %s (in-memory: %s)", path.name, file_bytes is not None)

        # 1. Validate
        is_valid, errors = self._validate_file(path, file_bytes)
        if not is_valid:
            logger.warning("Validation failed for %s: %s", path.name, errors)
            return IngestionResult(
                success=False,
                file_path=str(path),
                sheet_names=[],
                dataframes={},
                encoding="",
                errors=errors,
            )

        # 2. Ingest
        try:
            suffix = path.suffix.lower()
            if suffix == ".csv":
                dataframes, encoding = self._ingest_csv(path, file_bytes, **kwargs)
            else:
                dataframes, encoding = self._ingest_excel(path, file_bytes, **kwargs)

            metadata = self._build_metadata(path, dataframes, file_bytes)
            logger.info(
                "Ingested '%s' — %d rows across %d sheet(s)",
                path.name,
                metadata["total_rows"],
                len(dataframes),
            )
            return IngestionResult(
                success=True,
                file_path=str(path),
                sheet_names=list(dataframes.keys()),
                dataframes=dataframes,
                encoding=encoding,
                errors=[],
                metadata=metadata,
            )

        except Exception as exc:  # noqa: BLE001
            logger.error("Ingestion error for %s: %s", path.name, exc, exc_info=True)
            return IngestionResult(
                success=False,
                file_path=str(path),
                sheet_names=[],
                dataframes={},
                encoding="",
                errors=[f"Ingestion failed: {exc}"],
            )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_file(self, path: Path, file_bytes: Optional[bytes] = None) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        if file_bytes is None:
            if not path.exists():
                errors.append(f"File not found: {path}")
                return False, errors
            size_mb = path.stat().st_size / (1024 * 1024)
        else:
            size_mb = len(file_bytes) / (1024 * 1024)

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            errors.append(
                f"Unsupported file type '{path.suffix}'. "
                f"Supported: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )

        if size_mb > self.max_file_size_mb:
            errors.append(
                f"File too large: {size_mb:.1f} MB "
                f"(maximum: {self.max_file_size_mb} MB)"
            )

        # Skip the redundant 1-row pre-read — real read happens right after validation.
        # Any corruption will surface there with a clear error message.

        return len(errors) == 0, errors

    # ------------------------------------------------------------------
    # CSV ingestion
    # ------------------------------------------------------------------

    def _ingest_csv(
        self, path: Path, file_bytes: Optional[bytes] = None, **kwargs
    ) -> Tuple[Dict[str, pd.DataFrame], str]:
        import io
        if file_bytes is not None:
            chunk = file_bytes[:1000]
            encoding = "utf-8"
            for enc in ["utf-8", "latin1", "cp1252"]:
                try:
                    chunk.decode(enc)
                    encoding = enc
                    break
                except UnicodeDecodeError:
                    continue
            
            defaults = {
                "encoding": encoding,
                "low_memory": False,
            }
            defaults.update(kwargs)
            df = pd.read_csv(io.BytesIO(file_bytes), **defaults)
        else:
            encoding = kwargs.pop("encoding", None) or detect_encoding(str(path))
            defaults = {
                "encoding": encoding,
                "low_memory": False,
            }
            defaults.update(kwargs)
            df = pd.read_csv(path, **defaults)
            
        df = self._clean_dataframe(df)
        logger.debug("CSV '%s': %d rows × %d cols", path.name, *df.shape)
        return {"Sheet1": df}, encoding

    # ------------------------------------------------------------------
    # Excel ingestion
    # ------------------------------------------------------------------

    def _ingest_excel(
        self, path: Path, file_bytes: Optional[bytes] = None, **kwargs
    ) -> Tuple[Dict[str, pd.DataFrame], str]:
        import io
        if file_bytes is not None:
            xl = pd.ExcelFile(io.BytesIO(file_bytes))
        else:
            xl = pd.ExcelFile(path)
            
        dataframes: Dict[str, pd.DataFrame] = {}
        for sheet in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=sheet, **kwargs)
            df = self._clean_dataframe(df)
            dataframes[sheet] = df
            logger.debug(
                "Excel '%s' / sheet '%s': %d rows × %d cols",
                path.name, sheet, *df.shape
            )

        return dataframes, "binary"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Strip leading/trailing whitespace from string columns and headers."""
        # Vectorized column header strip
        df.columns = [str(c).strip() for c in df.columns]
        # Vectorized string column strip (10-100x faster than apply+lambda)
        str_cols = df.select_dtypes(include="object").columns
        for col in str_cols:
            df[col] = df[col].str.strip()
        return df

    @staticmethod
    def _build_metadata(
        path: Path, dataframes: Dict[str, pd.DataFrame], file_bytes: Optional[bytes] = None
    ) -> dict:
        if file_bytes is not None:
            size_bytes = len(file_bytes)
        else:
            size_bytes = path.stat().st_size
            
        return {
            "filename": path.name,
            "file_size_bytes": size_bytes,
            "file_size_mb": round(size_bytes / (1024 * 1024), 3),
            "sheet_count": len(dataframes),
            "total_rows": sum(df.shape[0] for df in dataframes.values()),
            "total_cols": sum(df.shape[1] for df in dataframes.values()),
            "sheets": {
                name: {"rows": df.shape[0], "cols": df.shape[1]}
                for name, df in dataframes.items()
            },
        }
