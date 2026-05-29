import re
import logging
from typing import Optional, Dict, Any
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors
import pubchempy as pcp

from backend.database.manager import DatabaseManager

logger = logging.getLogger("sdo.backend.normalization.identifier_service")

class ChemicalIdentifierService:
    """
    The SINGLE SOURCE OF TRUTH for chemical identity resolution.
    Deterministic, Cache-First, PubChem API resolver, with RDKit validation.
    """
    def __init__(self):
        self.db_manager = DatabaseManager()

    def detect_type(self, identifier: str) -> str:
        """
        Detects if identifier is a CID, CAS, SMILES, InChI, InChIKey, or Name.
        """
        identifier = str(identifier).strip()
        if not identifier:
            return "name"
            
        if identifier.isdigit():
            return "cid"
            
        if re.match(r'^\d{2,7}-\d{2}-\d$', identifier):
            return "cas"
            
        if identifier.upper().startswith("INCHI="):
            return "inchi"
            
        if re.match(r'^[A-Z]{14}-[A-Z]{10}-[A-Z0-9]$', identifier):
            return "inchikey"
            
        # Try parsing as SMILES to be sure
        try:
            mol = Chem.MolFromSmiles(identifier)
            if mol is not None:
                return "smiles"
        except Exception:
            pass
            
        return "name"

    def resolve(self, identifier: str, id_type: str = None, skip_online: bool = False) -> Dict[str, Any]:
        """
        Resolves an input identifier to a standardized identity object:
        1. Input Type Detection
        2. Local SQLite Cache Lookup
        3. PubChem Resolution (only if cache miss)
        4. RDKit Validation
        5. Canonical SMILES Standardization
        6. InChIKey/InChI/Formula Generation (locally via RDKit)
        7. Save to SQLite
        8. Return standard identity object
        """
        if not identifier or not isinstance(identifier, str) or not identifier.strip():
            return {
                "input_name": str(identifier),
                "canonical_smiles": "",
                "inchi": "",
                "inchikey": "",
                "molecular_formula": "",
                "cid": "",
                "source": "error",
                "status": "empty_identifier"
            }

        identifier = identifier.strip()
        if not id_type:
            id_type = self.detect_type(identifier)

        logger.info(f"Resolving '{identifier}' (Type: {id_type})")

        # Step 2: Local SQLite Cache Lookup
        db_hit = self.db_manager.get_compound_by_identifier(identifier)
        
        # If structure input, standardize first and check cache using canonical_smiles or inchikey
        local_canonical = None
        local_inchikey = None
        if id_type in ("smiles", "inchi"):
            try:
                if id_type == "smiles":
                    mol = Chem.MolFromSmiles(identifier)
                else:
                    mol = Chem.MolFromInchi(identifier)
                if mol:
                    local_canonical = Chem.MolToSmiles(mol, isomericSmiles=True, canonical=True)
                    local_inchikey = Chem.InchiToInchiKey(Chem.MolToInchi(mol))
            except Exception:
                pass
                
        if not db_hit and local_canonical:
            db_hit = self.db_manager.get_compound_by_identifier(local_canonical)
        if not db_hit and local_inchikey:
            db_hit = self.db_manager.get_compound_by_identifier(local_inchikey)

        if db_hit and db_hit.get("compound"):
            comp = db_hit["compound"]
            # Ensure we generate complete fields locally if they are missing
            canonical_smiles = comp.canonical_smiles
            inchi = ""
            inchikey = comp.inchi_key or ""
            formula = comp.molecular_formula or ""
            
            if canonical_smiles:
                try:
                    mol = Chem.MolFromSmiles(canonical_smiles)
                    if mol:
                        if not inchikey:
                            inchikey = Chem.InchiToInchiKey(Chem.MolToInchi(mol))
                        if not formula:
                            formula = rdMolDescriptors.CalcMolFormula(mol)
                        inchi = Chem.MolToInchi(mol)
                except Exception:
                    pass

            return {
                "input_name": identifier,
                "canonical_smiles": canonical_smiles or "",
                "inchi": inchi,
                "inchikey": inchikey,
                "molecular_formula": formula,
                "cid": comp.pubchem_cid or "",
                "source": "cache",
                "status": "success"
            }

        # Structure of standard result
        resolved_smiles = None
        cid = ""
        resolved_name = identifier

        # Step 3: PubChem Resolution
        if id_type in ("smiles", "inchi"):
            # Attempt offline/local parsing first for structural inputs
            try:
                if id_type == "smiles":
                    mol = Chem.MolFromSmiles(identifier)
                else:
                    mol = Chem.MolFromInchi(identifier)
                if mol:
                    resolved_smiles = Chem.MolToSmiles(mol, isomericSmiles=True, canonical=True)
            except Exception:
                pass

        if not resolved_smiles and not skip_online:
            try:
                comp_list = []
                if id_type == "cid":
                    comp_list = [pcp.Compound.from_cid(int(identifier))]
                elif id_type == "inchi":
                    comp_list = pcp.get_compounds(identifier, 'inchi')
                elif id_type == "inchikey":
                    comp_list = pcp.get_compounds(identifier, 'inchikey')
                elif id_type == "smiles":
                    comp_list = pcp.get_compounds(identifier, 'smiles')
                else: # "name" or "cas"
                    comp_list = pcp.get_compounds(identifier, 'name')

                if comp_list and comp_list[0]:
                    pcp_comp = comp_list[0]
                    resolved_smiles = pcp_comp.isomeric_smiles or pcp_comp.canonical_smiles or pcp_comp.smiles
                    cid = str(pcp_comp.cid) if pcp_comp.cid else ""
                    resolved_name = pcp_comp.synonyms[0] if pcp_comp.synonyms else (pcp_comp.iupac_name or identifier)
            except Exception as e:
                logger.error(f"PubChem API resolution failed for {identifier}: {e}")

        # Step 4: RDKit Validation
        if not resolved_smiles:
            status = "invalid_structure" if id_type in ("smiles", "inchi") else "not_found"
            return {
                "input_name": identifier,
                "canonical_smiles": "",
                "inchi": "",
                "inchikey": "",
                "molecular_formula": "",
                "cid": "",
                "source": "failed",
                "status": status
            }

        try:
            mol = Chem.MolFromSmiles(resolved_smiles)
        except Exception:
            mol = None

        if not mol:
            return {
                "input_name": identifier,
                "canonical_smiles": "",
                "inchi": "",
                "inchikey": "",
                "molecular_formula": "",
                "cid": "",
                "source": "failed",
                "status": "invalid_structure"
            }

        # Step 5 & 6: Standardization and offline InChI/InChIKey/Formula Generation
        canonical_smiles = Chem.MolToSmiles(mol, isomericSmiles=True, canonical=True)
        inchi = Chem.MolToInchi(mol)
        inchikey = Chem.InchiToInchiKey(inchi) if inchi else ""
        molecular_formula = rdMolDescriptors.CalcMolFormula(mol)

        # Step 7: Save to SQLite cache
        compound_data = {
            "compound_name": resolved_name,
            "canonical_smiles": canonical_smiles,
            "inchi_key": inchikey,
            "pubchem_cid": cid or None,
            "molecular_formula": molecular_formula,
            "cas_number": identifier if id_type == "cas" else None
        }

        try:
            self.db_manager.save_compound(compound_data)
        except Exception as e:
            logger.error(f"Failed to cache resolved compound '{identifier}' to SQLite: {e}")

        return {
            "input_name": identifier,
            "canonical_smiles": canonical_smiles,
            "inchi": inchi,
            "inchikey": inchikey,
            "molecular_formula": molecular_formula,
            "cid": cid,
            "source": "pubchem" if cid else "local_rdkit",
            "status": "success"
        }
