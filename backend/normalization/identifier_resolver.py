import pubchempy as pcp
import re
import time

class IdentifierResolver:
    """
    Resolves various chemical identifiers to SMILES using PubChem.
    Supports Names, CIDs, and CAS numbers.
    """
    
    def resolve_to_smiles(self, identifier, id_type=None):
        """
        Main entry point to resolve an identifier to SMILES.
        If id_type is None, it tries to auto-detect.
        """
        if not identifier:
            return None
            
        if not id_type:
            id_type = self.detect_type(identifier)
            
        try:
            if id_type == "cid":
                compound = pcp.Compound.from_cid(int(identifier))
                return compound.smiles
            
            # For names and CAS (PubChem treats CAS as a name search)
            compounds = pcp.get_compounds(identifier, 'name')
            if compounds:
                return compounds[0].smiles
                
        except Exception:
            # Fallback for CAS specifically if name search fails
            if id_type == "cas":
                try:
                    # Some CAS numbers are indexed differently
                    compounds = pcp.get_compounds(identifier, 'name')
                    if compounds:
                        return compounds[0].isomeric_smiles
                except:
                    pass
        
        return None

    def detect_type(self, identifier):
        """
        Detects if identifier is a CID, CAS, SMILES, or Name.
        """
        identifier = str(identifier).strip()
        
        # CID: Only digits
        if identifier.isdigit():
            return "cid"
            
        # CAS: digits-digits-digit
        if re.match(r'^\d{2,7}-\d{2}-\d$', identifier):
            return "cas"
            
        # SMILES: Simple heuristic (contains common SMILES chars but not spaces)
        # This is a bit loose but works for basic disambiguation from names
        if re.match(r'^[A-Za-z0-9@\+\-\[\]\(\)\\\/=#%]+$', identifier):
            if any(char in identifier for char in "=@#[]()"):
                return "smiles"
                
        return "name"

    def get_metadata(self, identifier):
        """
        Fetches compound name and basic info from PubChem.
        """
        try:
            compounds = pcp.get_compounds(identifier, 'name')
            if compounds:
                c = compounds[0]
                return {
                    "name": c.synonyms[0] if c.synonyms else identifier,
                    "cid": c.cid
                }
        except:
            pass
        return {"name": identifier, "cid": None}
