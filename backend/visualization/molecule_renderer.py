import os
import sqlite3
import time
from typing import Optional, Tuple
import logging

try:
    from rdkit import Chem
    from rdkit.Chem.Draw import rdMolDraw2D
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

logger = logging.getLogger("sdo.backend.visualization.molecule_renderer")

DB_PATH = "sutrix_science.db"

def init_svg_cache():
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

# Call cache initialization immediately on module load
init_svg_cache()

def get_cached_svg(smiles: str, width: int = 250, height: int = 200) -> Optional[str]:
    """Retrieve a cached SVG from SQLite."""
    if not smiles:
        return None
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT svg_string FROM molecule_svg_cache WHERE canonical_smiles = ? AND width = ? AND height = ?",
                (smiles.strip(), width, height)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
    except Exception as e:
        logger.error(f"Failed to read from molecule_svg_cache: {e}")
    return None

def cache_svg(smiles: str, svg_string: str, width: int = 250, height: int = 200):
    """Store a generated SVG in the SQLite cache."""
    if not smiles or not svg_string:
        return
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO molecule_svg_cache (canonical_smiles, width, height, svg_string, render_timestamp) VALUES (?, ?, ?, ?, ?)",
                (smiles.strip(), width, height, svg_string, time.time())
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to cache SVG: {e}")

def generate_mol_svg_core(smiles: str, size: Tuple[int, int] = (250, 200)) -> str:
    """Generates a raw molecular SVG locally using RDKit."""
    if not RDKIT_AVAILABLE or not smiles:
        return ""
    try:
        mol = Chem.MolFromSmiles(smiles.strip())
        if mol is None:
            return ""
        
        drawer = rdMolDraw2D.MolDraw2DSVG(size[0], size[1])
        
        # Premium aesthetics configuration
        draw_opt = drawer.drawOptions()
        draw_opt.clearBackground = True
        draw_opt.backgroundColour = (1, 1, 1, 0)  # transparent background
        draw_opt.bondLineWidth = 2
        draw_opt.addStereoAnnotation = True
        
        # Prepare molecule
        mc = rdMolDraw2D.PrepareMolForDrawing(mol)
        drawer.DrawMolecule(mc)
        drawer.FinishDrawing()
        
        svg = drawer.GetDrawingText()
        if svg.startswith("<?xml"):
            idx = svg.find("<svg")
            if idx != -1:
                svg = svg[idx:]
        return svg
    except Exception as e:
        logger.error(f"RDKit core drawing failed for '{smiles}': {e}")
        return ""

def get_molecule_svg(smiles: str, width: int = 250, height: int = 200, use_cache: bool = True) -> Tuple[str, bool]:
    """
    Get molecular SVG either from the persistent cache or by rendering it live.
    Returns a tuple of (svg_string, cache_hit_boolean).
    """
    if not smiles:
        return "", False
    
    smiles = smiles.strip()
    
    if use_cache:
        cached = get_cached_svg(smiles, width, height)
        if cached:
            return cached, True
            
    # Generate live
    svg = generate_mol_svg_core(smiles, (width, height))
    if svg and use_cache:
        cache_svg(smiles, svg, width, height)
        
    return svg, False

def get_svg_cache_statistics() -> dict:
    """Returns statistical metrics of the persistent SVG cache."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM molecule_svg_cache")
            total_cached = cursor.fetchone()[0]
            return {
                "total_cached": total_cached
            }
    except Exception:
        return {"total_cached": 0}
