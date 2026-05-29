"""
Unit normalisation and conversion for scientific measurements.

Supports mass, concentration, dose, and dose-rate units commonly
encountered in toxicology, proteomics, and environmental chemistry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from backend.utils.logger import setup_logger

logger = setup_logger("sdo.unit_converter")


# ---------------------------------------------------------------------------
# Unit definition
# ---------------------------------------------------------------------------

@dataclass
class UnitDefinition:
    """A single unit with its category and conversion factor to the base unit."""
    name: str
    category: str           # 'mass' | 'concentration' | 'dose' | 'dose_rate'
    base_unit: str          # canonical base unit for this category
    conversion_factor: float  # multiply value by this to get base-unit value
    aliases: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Always include the canonical name in aliases for lookup
        if self.name.lower() not in [a.lower() for a in self.aliases]:
            self.aliases.insert(0, self.name)


# ---------------------------------------------------------------------------
# Unit registry
# ---------------------------------------------------------------------------

_UNIT_REGISTRY: List[UnitDefinition] = [
    # ── Mass (base: mg) ─────────────────────────────────────────────────────
    UnitDefinition("mg",  "mass", "mg", 1.0,
                   ["mg", "milligram", "milligrams"]),
    UnitDefinition("g",   "mass", "mg", 1_000.0,
                   ["g", "gram", "grams"]),
    UnitDefinition("kg",  "mass", "mg", 1_000_000.0,
                   ["kg", "kilogram", "kilograms"]),
    UnitDefinition("ug",  "mass", "mg", 0.001,
                   ["ug", "µg", "microgram", "micrograms"]),
    UnitDefinition("ng",  "mass", "mg", 1e-6,
                   ["ng", "nanogram", "nanograms"]),

    # ── Concentration in water (base: mg/L) ──────────────────────────────────
    UnitDefinition("mg/L",  "concentration", "mg/L", 1.0,
                   ["mg/L", "mg/l", "milligram per liter", "milligrams per litre"]),
    UnitDefinition("ug/L",  "concentration", "mg/L", 0.001,
                   ["ug/L", "ug/l", "µg/L", "microgram per liter"]),
    UnitDefinition("ng/L",  "concentration", "mg/L", 1e-6,
                   ["ng/L", "ng/l", "nanogram per liter"]),
    UnitDefinition("g/L",   "concentration", "mg/L", 1_000.0,
                   ["g/L", "g/l", "gram per liter"]),
    UnitDefinition("ppm",   "concentration", "mg/L", 1.0,
                   ["ppm", "parts per million"]),
    UnitDefinition("ppb",   "concentration", "mg/L", 0.001,
                   ["ppb", "parts per billion"]),
    UnitDefinition("ppt",   "concentration", "mg/L", 1e-6,
                   ["ppt", "parts per trillion"]),
    UnitDefinition("mol/L", "concentration", "mg/L", None,      # type: ignore[arg-type]
                   ["mol/L", "mol/l", "M", "molar"]),  # MW-dependent, flagged separately

    # ── Dose (base: mg/kg) ───────────────────────────────────────────────────
    UnitDefinition("mg/kg",  "dose", "mg/kg", 1.0,
                   ["mg/kg", "milligram per kilogram", "mg kg-1"]),
    UnitDefinition("g/kg",   "dose", "mg/kg", 1_000.0,
                   ["g/kg", "gram per kilogram"]),
    UnitDefinition("ug/kg",  "dose", "mg/kg", 0.001,
                   ["ug/kg", "µg/kg", "microgram per kilogram"]),
    UnitDefinition("ng/kg",  "dose", "mg/kg", 1e-6,
                   ["ng/kg", "nanogram per kilogram"]),

    # ── Dose rate (base: mg/kg/day) ──────────────────────────────────────────
    UnitDefinition("mg/kg/day",  "dose_rate", "mg/kg/day", 1.0,
                   ["mg/kg/day", "mg/kg/d", "mg kg-1 d-1",
                    "milligram per kilogram per day"]),
    UnitDefinition("g/kg/day",   "dose_rate", "mg/kg/day", 1_000.0,
                   ["g/kg/day", "g/kg/d"]),
    UnitDefinition("ug/kg/day",  "dose_rate", "mg/kg/day", 0.001,
                   ["ug/kg/day", "ug/kg/d", "µg/kg/day"]),
    UnitDefinition("ng/kg/day",  "dose_rate", "mg/kg/day", 1e-6,
                   ["ng/kg/day", "ng/kg/d"]),

    # ── Air concentration (base: mg/m3) ─────────────────────────────────────
    UnitDefinition("mg/m3",  "air_concentration", "mg/m3", 1.0,
                   ["mg/m3", "mg/m³", "milligram per cubic meter"]),
    UnitDefinition("ug/m3",  "air_concentration", "mg/m3", 0.001,
                   ["ug/m3", "µg/m3", "microgram per cubic meter"]),
    UnitDefinition("ppmv",   "air_concentration", "mg/m3", None,   # type: ignore[arg-type]
                   ["ppmv", "ppm (v/v)"]),   # MW-dependent
]


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------

class UnitConverter:
    """Normalises and converts scientific units."""

    def __init__(self) -> None:
        # alias (lowercase, stripped) → UnitDefinition
        self._alias_index: Dict[str, UnitDefinition] = {}
        self._build_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def normalize_unit(self, unit_str: str) -> Optional[str]:
        """
        Return the canonical unit name for a given unit string, or None
        if unrecognised.
        """
        key = self._key(unit_str)
        defn = self._alias_index.get(key)
        return defn.name if defn else None

    def get_category(self, unit_str: str) -> Optional[str]:
        """Return the measurement category ('mass', 'dose', etc.) or None."""
        key = self._key(unit_str)
        defn = self._alias_index.get(key)
        return defn.category if defn else None

    def convert(self, value: float, from_unit: str, to_unit: str) -> Optional[float]:
        """
        Convert a numeric value between two compatible units.

        Returns None if units are incompatible or unrecognised.
        """
        from_defn = self._alias_index.get(self._key(from_unit))
        to_defn = self._alias_index.get(self._key(to_unit))

        if from_defn is None:
            logger.warning("Unknown source unit: '%s'", from_unit)
            return None
        if to_defn is None:
            logger.warning("Unknown target unit: '%s'", to_unit)
            return None
        if from_defn.category != to_defn.category:
            logger.warning(
                "Incompatible categories: '%s' (%s) vs '%s' (%s)",
                from_unit, from_defn.category,
                to_unit, to_defn.category,
            )
            return None
        if from_defn.conversion_factor is None or to_defn.conversion_factor is None:
            logger.warning(
                "Unit '%s' or '%s' requires molecular weight for conversion — skipped.",
                from_unit, to_unit,
            )
            return None

        base_value = value * from_defn.conversion_factor
        return base_value / to_defn.conversion_factor

    def validate_unit_consistency(
        self, units: List[str]
    ) -> Dict:
        """
        Report on unit consistency across a dataset column.

        Returns a dict with:
            is_consistent   bool
            unique_units    list of canonical unit names found
            unit_counts     {canonical_name: count}
            unrecognised    list of raw unit strings not in the registry
            missing_count   number of None/empty entries
        """
        canonical: List[Optional[str]] = []
        unrecognised: List[str] = []

        for u in units:
            if u is None or (isinstance(u, str) and not u.strip()):
                canonical.append(None)
            else:
                norm = self.normalize_unit(str(u))
                if norm is None:
                    unrecognised.append(str(u))
                canonical.append(norm)

        non_none = [c for c in canonical if c is not None]
        unique = list(set(non_none))
        counts = {u: non_none.count(u) for u in unique}

        return {
            "is_consistent": len(unique) <= 1,
            "unique_units": unique,
            "unit_counts": counts,
            "unrecognised": list(set(unrecognised)),
            "missing_count": canonical.count(None),
        }

    def list_units(self, category: Optional[str] = None) -> List[str]:
        """List canonical unit names, optionally filtered by category."""
        return [
            defn.name
            for defn in _UNIT_REGISTRY
            if category is None or defn.category == category
        ]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_index(self) -> None:
        for defn in _UNIT_REGISTRY:
            for alias in defn.aliases:
                key = self._key(alias)
                if key not in self._alias_index:
                    self._alias_index[key] = defn
        logger.debug(
            "Unit index built: %d aliases across %d units",
            len(self._alias_index),
            len(_UNIT_REGISTRY),
        )

    @staticmethod
    def _key(unit_str: str) -> str:
        """Normalise a unit string for index lookup."""
        return unit_str.strip().lower().replace(" ", "")
