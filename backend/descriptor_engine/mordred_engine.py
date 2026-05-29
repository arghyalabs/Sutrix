import logging
import math
import concurrent.futures
from typing import Dict, Any

logger = logging.getLogger("sdo.backend.descriptors.mordred")

try:
    from rdkit import Chem
    import numpy
    # NumPy 2.x compatibility monkeypatch for old mordred library
    if not hasattr(numpy, "product"):
        numpy.product = numpy.prod

    import collections
    import collections.abc
    # Python 3.10+ compatibility monkeypatches for old mordred library
    collections.MutableMapping = collections.abc.MutableMapping
    collections.Iterable = collections.abc.Iterable
    collections.Sequence = collections.abc.Sequence
    collections.Mapping = collections.abc.Mapping
    collections.Callable = collections.abc.Callable
    collections.MutableSequence = collections.abc.MutableSequence

    from mordred import Calculator, descriptors  # type: ignore[import-untyped]
    MORDRED_AVAILABLE = True
except Exception as e:
    logger.warning(f"Failed to import mordred: {e}")
    MORDRED_AVAILABLE = False


class MordredEngine:
    """
    Optional Mordred engine for extended QSAR-ready descriptor calculation.
    Covers topological, constitutional, autocorrelation, and geometric.
    """
    def __init__(self, timeout_seconds: int = 15):
        self.timeout_seconds = timeout_seconds
        self.calc = None
        
        if MORDRED_AVAILABLE:
            try:
                # Initialize calculator with all descriptors
                # Note: ignore_3D=False enables geometric descriptors (requires 3D coords)
                self.calc = Calculator(descriptors, ignore_3D=False)
            except Exception as e:
                logger.error(f"Failed to initialize Mordred Calculator: {e}")
                self.calc = None
        else:
            logger.info("Mordred is not installed. Extended descriptors disabled.")

    def _clean_value(self, val: Any) -> Any:
        """Cleans NaNs, exceptions, and invalid types returned by Mordred."""
        from mordred.error import MissingValueBase
        if isinstance(val, MissingValueBase) or val is None:
            return None
            
        if isinstance(val, float):
            if math.isnan(val) or math.isinf(val):
                return None
            return val
            
        if isinstance(val, (int, str)):
            return val
            
        try:
            f_val = float(val)
            if math.isnan(f_val) or math.isinf(f_val):
                return None
            return f_val
        except (ValueError, TypeError):
            return None

    def _compute_sync(self, mol: Chem.Mol, selected_descriptors: list = None) -> Dict[str, Any]:
        """Synchronous wrapper for computing and cleaning descriptors."""
        if not self.calc:
            return {}
            
        # If geometric descriptors are requested, mordred expects 3D coordinates.
        # Ensure we have them, or gracefully fallback.
        if not mol.GetNumConformers():
            from rdkit.Chem import AllChem
            # Generate temporary 3D coords for geometric descriptors
            # Use a copy to avoid mutating the original
            mol_copy = Chem.Mol(mol)
            mol_copy = Chem.AddHs(mol_copy)
            try:
                AllChem.EmbedMolecule(mol_copy, randomSeed=42)
                AllChem.MMFFOptimizeMolecule(mol_copy)
            except Exception:
                pass
            raw_res = self.calc(mol_copy)
        else:
            raw_res = self.calc(mol)
            
        # Clean results into dictionary
        result_dict = {}
        for desc, val in zip(self.calc.descriptors, raw_res):
            desc_name = str(desc)
            if selected_descriptors is not None and desc_name not in selected_descriptors:
                continue
            clean_val = self._clean_value(val)
            result_dict[desc_name] = clean_val
            
        return result_dict

    def calculate(self, mol: Chem.Mol, selected_descriptors: list = None) -> Dict[str, Any]:
        """
        Calculates Mordred descriptors with timeout protection.
        """
        if not MORDRED_AVAILABLE or not self.calc:
            return {"success": False, "error": "MORDRED_NOT_AVAILABLE", "data": {}}
            
        if not mol:
            return {"success": False, "error": "INVALID_MOLECULE", "data": {}}

        try:
            # Timeout protection via ThreadPoolExecutor
            # Threads won't be killed immediately if they hang, but the orchestrator won't block
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._compute_sync, mol, selected_descriptors)
                data = future.result(timeout=self.timeout_seconds)
                
            return {"success": True, "data": data}
            
        except concurrent.futures.TimeoutError:
            logger.warning("Mordred calculation timed out. Molecule too complex.")
            return {"success": False, "error": "CALCULATION_TIMEOUT", "data": {}}
        except Exception as e:
            logger.error(f"Mordred calculation error: {e}")
            return {"success": False, "error": f"MORDRED_ERROR: {str(e)}", "data": {}}
