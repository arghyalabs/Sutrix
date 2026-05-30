"""
Descriptor Coverage Engine - classifies descriptor columns into scientific families.
All outputs must be JSON-serializable.
"""
import logging
from typing import Dict, Any, List
import pandas as pd

logger = logging.getLogger("sdo.core.descriptor_coverage_engine")

# ---------------------------------------------------------------------------
# Family keyword patterns (case-insensitive substring match)
# ---------------------------------------------------------------------------
FAMILY_PATTERNS: Dict[str, List[str]] = {
    "Constitutional": [
        "MW", "MolWt", "HeavyAtom", "RingCount", "NumRings", "BondCount",
        "FractionCSP3", "MolMR", "NumHeteroatoms", "NumAtoms",
    ],
    "Physicochemical": [
        "LogP", "MolLogP", "TPSA", "HBA", "HBD", "HBAcceptor", "HBDonor",
        "RotatableBonds", "NumRotatable", "LabuteASA", "MolMR",
    ],
    "Topological": [
        "BalabanJ", "BertzCT", "Chi", "Kappa", "HallKierAlpha", "Ipc",
        "EState", "SlogP", "SMR", "VSA", "MaxEStateIndex",
    ],
    "Electronic": [
        "PEOE", "GasteigerCharge", "MaxEE", "MinEE", "MaxAbsEE", "MinAbsEE", "qed",
    ],
    "Geometrical": [
        "Asphericity", "Eccentricity", "InertialShapeFactor", "PMI",
        "RadiusOfGyration", "SpherocityIndex", "NPR",
    ],
    "Autocorrelation": [
        "MATS", "GATS", "ATSC", "AATSC", "MORAN", "GEARY", "Moran", "Geary",
    ],
    "WHIM": [
        "WHIM", "W1u", "W2u", "P1u", "P2u", "K1", "K2", "K3",
    ],
    "GETAWAY": [
        "GETAWAY", "HATS", "H0u", "H1u", "Rcon",
    ],
    "BCUT": [
        "BCUT", "BCUTc", "BCUTdv", "BCUTare",
    ],
    "Fingerprint": [
        "Morgan", "ECFP", "FCFP", "MACCS", "AtomPair",
        "TopologicalTorsion", "RDKFingerprint",
    ],
    "Fragment": [
        "fr_", "NumAliphatic", "NumAromatic", "NumSaturated",
    ],
    "Surface Area": [
        "ASA", "SASA", "LabuteASA", "SlogP_VSA", "SMR_VSA", "PEOE_VSA",
    ],
}

# ---------------------------------------------------------------------------
# Missing-family guidance
# ---------------------------------------------------------------------------
MISSING_FAMILY_INFO: Dict[str, Dict[str, str]] = {
    "WHIM": {
        "importance": "High",
        "reason": (
            "3D shape descriptors capturing molecular geometry. "
            "Essential for 3D-QSAR."
        ),
        "how_to_generate": "Use Mordred with mordred.WHIM descriptors.",
    },
    "GETAWAY": {
        "importance": "Medium",
        "reason": "Graph-theoretical 3D descriptors encoding atomic environment.",
        "how_to_generate": "Use Mordred: Calculator([GETAWAY])",
    },
    "BCUT": {
        "importance": "Medium",
        "reason": "Eigenvalue-based descriptors capturing atomic property distributions.",
        "how_to_generate": "Use RDKit or Mordred.",
    },
    "Autocorrelation": {
        "importance": "High",
        "reason": (
            "Moran/Geary autocorrelation encodes property distribution "
            "along the molecular graph."
        ),
        "how_to_generate": "Mordred: Calculator([Autocorrelation])",
    },
    "Fingerprint": {
        "importance": "Critical",
        "reason": (
            "Morgan fingerprints are essential for similarity-based QSAR, "
            "applicability domain, and scaffold hopping."
        ),
        "how_to_generate": (
            "from rdkit.Chem import AllChem; "
            "fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)"
        ),
    },
    "Geometrical": {
        "importance": "Medium",
        "reason": (
            "3D shape properties required for 3D-QSAR workflows. "
            "Need 3D conformer generation first."
        ),
        "how_to_generate": (
            "AllChem.EmbedMolecule(mol); then RDKit 3D descriptors."
        ),
    },
}


class DescriptorCoverageEngine:
    """
    Classifies descriptor columns into scientific families, reports coverage,
    and recommends missing descriptor sets.
    """

    @staticmethod
    def _col_matches_family(col: str, patterns: List[str]) -> bool:
        """Return True if col contains any pattern (case-insensitive)."""
        col_lower = col.lower()
        for pat in patterns:
            if pat.lower() in col_lower:
                return True
        return False

    @staticmethod
    def classify_columns(descriptor_cols: List[str]) -> Dict[str, Any]:
        """
        Classify descriptor columns into scientific families.

        Parameters
        ----------
        descriptor_cols : list[str]
            All descriptor column names from the dataset.

        Returns
        -------
        dict with family breakdown, coverage stats, and recommendations.
        """
        if not descriptor_cols:
            return {
                "families": [],
                "overall_coverage_pct": 0.0,
                "missing_families": list(FAMILY_PATTERNS.keys()),
                "generated_descriptors": [],
                "uncategorized": [],
                "missing_descriptor_recommendations": [],
            }

        # Build per-column family assignment (first match wins for "generated" list)
        column_to_families: Dict[str, List[str]] = {col: [] for col in descriptor_cols}

        for family_name, patterns in FAMILY_PATTERNS.items():
            for col in descriptor_cols:
                if DescriptorCoverageEngine._col_matches_family(col, patterns):
                    column_to_families[col].append(family_name)

        # Collect columns belonging to at least one family
        generated_descriptors: List[str] = [
            col for col, fams in column_to_families.items() if fams
        ]
        uncategorized: List[str] = [
            col for col, fams in column_to_families.items() if not fams
        ]

        # Build per-family stats
        families_present: Dict[str, List[str]] = {fam: [] for fam in FAMILY_PATTERNS}
        for col, fams in column_to_families.items():
            for fam in fams:
                families_present[fam].append(col)

        families_result: List[Dict[str, Any]] = []
        present_family_names: List[str] = []
        missing_family_names: List[str] = []

        for fam_name, patterns in FAMILY_PATTERNS.items():
            cols_in_family = families_present[fam_name]
            n_present = len(cols_in_family)
            n_patterns = len(patterns)
            pct = round(float(n_present) / max(n_patterns, 1) * 100.0, 1)

            if n_present == 0:
                status = "MISSING"
                missing_family_names.append(fam_name)
            elif pct >= 70.0:
                status = "GOOD"
                present_family_names.append(fam_name)
            else:
                status = "PARTIAL"
                present_family_names.append(fam_name)

            families_result.append({
                "name": fam_name,
                "present": int(n_present),
                "total_patterns": int(n_patterns),
                "coverage_pct": pct,
                "columns": sorted(cols_in_family),
                "status": status,
            })

        # Overall coverage = fraction of families that are present (non-MISSING)
        n_total_families = len(FAMILY_PATTERNS)
        n_present_families = len(present_family_names)
        overall_coverage_pct = round(
            float(n_present_families) / max(n_total_families, 1) * 100.0, 1
        )

        # Build recommendations for missing / partial families
        recommendations: List[Dict[str, Any]] = []
        for fam_name in missing_family_names:
            if fam_name in MISSING_FAMILY_INFO:
                info = MISSING_FAMILY_INFO[fam_name]
                recommendations.append({
                    "name": fam_name,
                    "family": fam_name,
                    "importance": info["importance"],
                    "reason": info["reason"],
                    "how_to_generate": info["how_to_generate"],
                })

        return {
            "families": families_result,
            "overall_coverage_pct": overall_coverage_pct,
            "missing_families": missing_family_names,
            "generated_descriptors": sorted(generated_descriptors),
            "uncategorized": sorted(uncategorized),
            "missing_descriptor_recommendations": recommendations,
        }
