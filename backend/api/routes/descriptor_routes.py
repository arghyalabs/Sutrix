from fastapi import APIRouter
from typing import Dict, List
import logging
from rdkit.Chem import Descriptors

logger = logging.getLogger("sdo.backend.api.descriptor_routes")

router = APIRouter()

@router.get("/api/descriptors", response_model=Dict[str, List[str]])
def list_descriptors():
    """
    Returns a dictionary with arrays of available RDKit and Mordred descriptor names.
    """
    rdkit_descs = [name for name, _ in Descriptors._descList]
    mordred_descs = []
    try:
        from mordred import Calculator, descriptors
        calc = Calculator(descriptors, ignore_3D=False)
        mordred_descs = [str(d) for d in calc.descriptors]
    except Exception as e:
        logger.warning(f"Failed to load mordred descriptors for list: {e}")
        # Return an empty list if Mordred is not available
        mordred_descs = []
        
    return {
        "rdkit": rdkit_descs,
        "mordred": mordred_descs
    }
