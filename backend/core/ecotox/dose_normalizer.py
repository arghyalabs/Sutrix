import re
from typing import Dict, Any, Optional

class DoseNormalizer:
    """
    Standardizes concentration units and doses.
    Supports conversions across molar (mM, uM, nM) and mass concentration (mg/L, ug/L, ppm).
    """

    CONVERSION_FACTORS = {
        "mg/l": 1.0,
        "µg/l": 1e-3,
        "ug/l": 1e-3,
        "ng/l": 1e-6,
        "ppm": 1.0,
        "ppb": 1e-3
    }

    @staticmethod
    def convert_concentration(value: float, from_unit: str, to_unit: str, mw: float = None) -> float:
        """
        Converts concentration values between units.
        Utilizes molecular weight (MW) for mass <-> molar calculations.
        """
        if value is None:
            return None
            
        from_u = from_unit.lower().strip()
        to_u = to_unit.lower().strip()
        
        if from_u == to_u:
            return value

        # 1. Mass to Mass conversions (e.g. ug/L -> mg/L)
        if from_u in DoseNormalizer.CONVERSION_FACTORS and to_u in DoseNormalizer.CONVERSION_FACTORS:
            factor_from = DoseNormalizer.CONVERSION_FACTORS[from_u]
            factor_to = DoseNormalizer.CONVERSION_FACTORS[to_u]
            return value * (factor_from / factor_to)

        # 2. Molar to Molar conversions (e.g. uM -> mM)
        molar_scales = {"mol/l": 1.0, "m": 1.0, "mm": 1e-3, "µm": 1e-6, "um": 1e-6, "nm": 1e-9}
        if from_u in molar_scales and to_u in molar_scales:
            scale_from = molar_scales[from_u]
            scale_to = molar_scales[to_u]
            return value * (scale_from / scale_to)

        # 3. Molar <-> Mass conversions (requires Molecular Weight)
        if mw and mw > 0:
            # Step A: Convert from_unit to Moles/L
            val_moles = None
            if from_u in molar_scales:
                val_moles = value * molar_scales[from_u]
            elif from_u in DoseNormalizer.CONVERSION_FACTORS:
                # mass in mg/L
                val_mg = value * DoseNormalizer.CONVERSION_FACTORS[from_u]
                val_moles = (val_mg / 1000.0) / mw # mg/L -> g/L -> mol/L
                
            if val_moles is None:
                return value

            # Step B: Convert Moles/L to to_unit
            if to_u in molar_scales:
                return val_moles / molar_scales[to_u]
            elif to_u in DoseNormalizer.CONVERSION_FACTORS:
                val_mg = (val_moles * mw) * 1000.0 # mol/L -> g/L -> mg/L
                return val_mg / DoseNormalizer.CONVERSION_FACTORS[to_u]

        return value

    @staticmethod
    def normalize_dose(value: float, unit: str) -> Dict[str, Any]:
        """
        Normalizes a dose cell to structural systems.
        Returns standardized values e.g. {"standardized_value": 0.05, "standardized_unit": "mg/L"}
        """
        u_clean = unit.lower().strip() if unit else ""
        
        # Default target standardized unit is mg/L for aquatic and mg/kg/day for mammalian
        std_unit = "mg/L"
        std_val = value
        
        if u_clean in ["ug/l", "µg/l"]:
            std_val = value * 1e-3
            std_unit = "mg/L"
        elif u_clean in ["ng/l"]:
            std_val = value * 1e-6
            std_unit = "mg/L"
        elif u_clean in ["ppm"]:
            std_val = value
            std_unit = "mg/L"
        elif u_clean in ["ppb"]:
            std_val = value * 1e-3
            std_unit = "mg/L"
        elif u_clean in ["mg/kg/day", "mg/kg/d", "mg/kg bw/day"]:
            std_val = value
            std_unit = "mg/kg/day"
        elif u_clean in ["mg/kg"]:
            std_val = value
            std_unit = "mg/kg"
            
        return {
            "standardized_value": std_val,
            "standardized_unit": std_unit,
            "original_value": value,
            "original_unit": unit
        }

    @staticmethod
    def infer_environmental_unit(species: str) -> str:
        """
        Infers the default standard environmental testing unit based on the species' trophic ecosystem.
        """
        s_lower = species.lower().strip() if species else ""
        if s_lower in ["fish", "daphnia", "algae", "bacteria"]:
            return "mg/L"  # Aquatic testing standard
        elif s_lower in ["rat", "mouse", "rabbit", "dog", "primate"]:
            return "mg/kg/day"  # Terrestrial/Mammalian standard
        return "mg/L"
