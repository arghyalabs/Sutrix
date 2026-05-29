from .smiles_cleaner import SMILESCleaner
from .identifier_resolver import IdentifierResolver
import logging

logger = logging.getLogger(__name__)

class CompoundNormalizer:
    """
    Orchestrates the compound normalization process for the Sutrix platform.
    Converts any input (Name, SMILES, CID, CAS) into a standardized set of identifiers.
    """
    
    def __init__(self):
        self.cleaner = SMILESCleaner()
        self.resolver = IdentifierResolver()

    def normalize(self, input_value):
        """
        Normalize a compound input into a standard format.
        
        Args:
            input_value: String (Name, SMILES, CID, or CAS)
            
        Returns:
            Dictionary with standardized identifiers or None if failed.
        """
        if not input_value:
            return None
            
        input_value = str(input_value).strip()
        input_type = self.resolver.detect_type(input_value)
        
        logger.info(f"Normalizing {input_value} (Detected type: {input_type})")
        
        # 1. Get SMILES
        smiles = None
        if input_type == "smiles":
            smiles = input_value
        else:
            smiles = self.resolver.resolve_to_smiles(input_value, input_type)
            
        if not smiles:
            logger.warning(f"Could not resolve {input_value} to SMILES")
            return None
            
        # 2. Clean and Canonicalize SMILES
        canonical_smiles = self.cleaner.clean(smiles)
        if not canonical_smiles:
            logger.warning(f"Failed to canonicalize SMILES for {input_value}")
            return None
            
        # 3. Generate InChI and InChIKey
        inchi, inchikey = self.cleaner.get_inchi_data(canonical_smiles)
        
        # 4. Get Molecular Formula
        formula = self.cleaner.get_formula(canonical_smiles)
        
        # 5. Get preferred Name (from PubChem if possible)
        metadata = self.resolver.get_metadata(input_value)
        
        return {
            "input_value": input_value,
            "compound_name": metadata.get("name"),
            "canonical_smiles": canonical_smiles,
            "inchi": inchi,
            "inchikey": inchikey,
            "molecular_formula": formula
        }

    def batch_normalize(self, input_list):
        """
        Normalize a list of compounds.
        """
        results = []
        for item in input_list:
            norm = self.normalize(item)
            if norm:
                results.append(norm)
        return results
