"""
Tests for Phase 1 — File Ingestion System.
"""
import pytest
import pandas as pd
from pathlib import Path

from backend.utils.file_handler import FileIngestionEngine, IngestionResult
from backend.utils.encoding_detector import detect_encoding, verify_encoding


class TestFileIngestionEngine:

    def test_ingest_csv_success(self, sample_csv_file):
        engine = FileIngestionEngine()
        result = engine.ingest(str(sample_csv_file))

        assert result.success is True
        assert "Sheet1" in result.sheet_names
        assert isinstance(result.primary_df, pd.DataFrame)
        assert len(result.primary_df) == 5
        assert result.total_rows == 5

    def test_ingest_excel_success(self, sample_excel_file):
        engine = FileIngestionEngine()
        result = engine.ingest(str(sample_excel_file))

        assert result.success is True
        assert "Toxicology" in result.sheet_names
        assert "Summary" in result.sheet_names
        assert result.metadata["sheet_count"] == 2

    def test_ingest_nonexistent_file(self):
        engine = FileIngestionEngine()
        result = engine.ingest("/nonexistent/path/file.csv")

        assert result.success is False
        assert len(result.errors) > 0
        assert result.primary_df is None

    def test_ingest_unsupported_extension(self, tmp_path):
        bad_file = tmp_path / "data.txt"
        bad_file.write_text("hello")
        engine = FileIngestionEngine()
        result = engine.ingest(str(bad_file))

        assert result.success is False
        assert any("Unsupported" in e for e in result.errors)

    def test_metadata_populated(self, sample_csv_file):
        engine = FileIngestionEngine()
        result = engine.ingest(str(sample_csv_file))

        assert result.metadata["total_rows"] == 5
        assert result.metadata["total_cols"] == 8
        assert result.metadata["file_size_bytes"] > 0

    def test_column_names_stripped(self, tmp_path):
        """Ensure leading/trailing whitespace is stripped from column names."""
        df = pd.DataFrame({"  col_a  ": [1, 2], " col_b": [3, 4]})
        path = tmp_path / "whitespace.csv"
        df.to_csv(path, index=False)

        engine = FileIngestionEngine()
        result = engine.ingest(str(path))

        assert result.success is True
        cols = list(result.primary_df.columns)
        assert "col_a" in cols
        assert "col_b" in cols


class TestEncodingDetection:

    def test_utf8_file(self, tmp_path):
        path = tmp_path / "utf8.csv"
        path.write_text("a,b\n1,2\n", encoding="utf-8")
        enc = detect_encoding(str(path))
        assert enc.lower().replace("-", "") in ("utf8", "ascii")

    def test_latin1_file(self, tmp_path):
        path = tmp_path / "latin1.csv"
        path.write_bytes("name,value\nAcetäl,100\n".encode("latin-1"))
        enc = detect_encoding(str(path))
        # chardet may return 'ISO-8859-1' or 'latin-1' or similar
        assert enc is not None

    def test_nonexistent_file_returns_utf8(self):
        enc = detect_encoding("/no/such/file.csv")
        assert enc == "utf-8"

    def test_verify_encoding_valid(self, tmp_path):
        path = tmp_path / "valid.csv"
        path.write_text("hello world", encoding="utf-8")
        assert verify_encoding(str(path), "utf-8") is True

    def test_verify_encoding_invalid(self, tmp_path):
        path = tmp_path / "latin.csv"
        path.write_bytes(b"\xff\xfe")
        assert verify_encoding(str(path), "ascii") is False
