import os
import hashlib
import time
import sqlite3
import logging
from typing import List, Dict, Any, Tuple, Optional

try:
    from rdkit import Chem
    from rdkit.Chem.Draw import rdMolDraw2D
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

logger = logging.getLogger("sdo.backend.visualization.render_manager")

# Directories and DB paths
DB_PATH = "sutrix_science.db"
DISK_CACHE_DIR = os.path.join("backend", "cache", "mol_svg_cache")

class RenderManager:
    """
    Manages the progressive visual render pipeline, timing estimations,
    and a dual-layer persistent cache (SQLite database + flat-file disk cache).
    """
    def __init__(self):
        # Guarantee disk cache directory exists
        os.makedirs(DISK_CACHE_DIR, exist_ok=True)
        self.init_db_cache()

    def init_db_cache(self):
        """Initializes the persistent molecule image cache table in SQLite."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS molecule_svg_cache (
                        canonical_smiles TEXT NOT NULL,
                        width INTEGER NOT NULL,
                        height INTEGER NOT NULL,
                        svg_string TEXT NOT NULL,
                        render_timestamp REAL NOT NULL,
                        PRIMARY KEY (canonical_smiles, width, height)
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize molecule_svg_cache table: {e}")

    def _get_disk_cache_path(self, smiles: str, width: int, height: int) -> str:
        """Gets a deterministic hash-based file path for the disk cache."""
        hash_input = f"{smiles.strip()}_{width}_{height}".encode('utf-8')
        file_hash = hashlib.sha256(hash_input).hexdigest()
        return os.path.join(DISK_CACHE_DIR, f"{file_hash}.svg")

    def get_svg(self, smiles: str, width: int = 250, height: int = 200, use_cache: bool = True) -> Tuple[str, bool]:
        """
        Retrieves a cached SVG using a dual-layer strategy:
        1. Quick check on flat disk cache (fastest file read).
        2. Fallback check in SQLite cache.
        Returns a tuple of (svg_string, cache_hit_boolean).
        """
        if not smiles or not isinstance(smiles, str):
            return "", False

        smiles = smiles.strip()
        
        if not use_cache:
            svg = self.generate_svg_raw(smiles, width, height)
            return svg, False

        # Layer 1: Disk Cache Lookup
        disk_path = self._get_disk_cache_path(smiles, width, height)
        if os.path.exists(disk_path):
            try:
                with open(disk_path, 'r', encoding='utf-8') as f:
                    return f.read(), True
            except Exception as e:
                logger.warning(f"Failed to read disk cache for {smiles}: {e}")

        # Layer 2: SQLite Cache Lookup
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT svg_string FROM molecule_svg_cache WHERE canonical_smiles = ? AND width = ? AND height = ?",
                    (smiles, width, height)
                )
                row = cursor.fetchone()
                if row:
                    svg_str = row[0]
                    # Back-populate to disk cache for future ultra-fast access
                    try:
                        with open(disk_path, 'w', encoding='utf-8') as f:
                            f.write(svg_str)
                    except Exception as de:
                        logger.warning(f"Failed to write to disk cache on recovery: {de}")
                    return svg_str, True
        except Exception as e:
            logger.error(f"Failed to query SQLite cache: {e}")

        return "", False

    def cache_svg(self, smiles: str, svg_string: str, width: int = 250, height: int = 200):
        """Saves a generated SVG to both the SQLite cache and flat-file disk cache."""
        if not smiles or not svg_string:
            return
        
        # ── 2GB LOW-STORAGE FAILSAFE ─────────────────────────────────
        try:
            import shutil
            total, used, free = shutil.disk_usage(".")
            if free < 2 * 1024 * 1024 * 1024:  # 2 GB
                logger.warning("Low disk space detected (<2GB). Skipping SVG cache writes to prevent disk exhaustion.")
                return
        except Exception:
            pass

        smiles = smiles.strip()
        
        # Save to Disk Cache
        disk_path = self._get_disk_cache_path(smiles, width, height)
        try:
            with open(disk_path, 'w', encoding='utf-8') as f:
                f.write(svg_string)
        except Exception as e:
            logger.error(f"Failed to save SVG to disk cache: {e}")

        # Save to SQLite Cache
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO molecule_svg_cache (canonical_smiles, width, height, svg_string, render_timestamp) VALUES (?, ?, ?, ?, ?)",
                    (smiles, width, height, svg_string, time.time())
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to cache SVG to SQLite: {e}")

    def generate_svg_raw(self, smiles: str, width: int = 250, height: int = 200) -> str:
        """Generates a premium high-resolution 2D RDKit SVG drawing."""
        if not RDKIT_AVAILABLE or not smiles:
            return ""
        try:
            mol = Chem.MolFromSmiles(smiles.strip())
            if mol is None:
                return ""
            
            drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
            
            # Professional cheminformatics aesthetics
            options = drawer.drawOptions()
            options.clearBackground = True
            options.backgroundColour = (1, 1, 1, 0)  # Transparent
            options.bondLineWidth = 2.0
            options.annotationFontScale = 0.8
            options.addStereoAnnotation = True
            
            mc = rdMolDraw2D.PrepareMolForDrawing(mol)
            drawer.DrawMolecule(mc)
            drawer.FinishDrawing()
            
            svg = drawer.GetDrawingText()
            # Clean all XML declarations/namespaces and DOCTYPE wrappers so it starts purely with <svg
            idx = svg.find("<svg")
            if idx != -1:
                svg = svg[idx:]
            return svg
        except Exception as e:
            logger.error(f"RDKit raw draw error for '{smiles}': {e}")
            return ""

    def process_render_queue_batch(self, missing_items: List[Dict[str, Any]], batch_size: int = 6, width: int = 200, height: int = 120) -> int:
        """
        Processes a small batch of missing SVG compounds from the render queue,
        drawing and writing them directly to the persistent caches.
        Returns the number of compounds rendered in this batch.
        """
        processed_count = 0
        batch = missing_items[:batch_size]
        
        for item in batch:
            smiles = item.get("smiles")
            if smiles:
                svg = self.generate_svg_raw(smiles, width, height)
                if svg:
                    self.cache_svg(smiles, svg, width, height)
                    processed_count += 1
        return processed_count

    def get_cache_statistics(self) -> dict:
        """Fetch file and database counts for visual reporting."""
        db_count = 0
        disk_count = 0
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT count(*) FROM molecule_svg_cache")
                db_count = cursor.fetchone()[0]
        except Exception:
            pass
            
        try:
            if os.path.exists(DISK_CACHE_DIR):
                disk_count = len([f for f in os.listdir(DISK_CACHE_DIR) if f.endswith(".svg")])
        except Exception:
            pass

        return {
            "db_cached": db_count,
            "disk_cached": disk_count,
            "total_cached": max(db_count, disk_count)
        }
