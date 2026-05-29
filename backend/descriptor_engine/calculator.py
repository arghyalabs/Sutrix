import logging
from typing import Dict, Any

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
    from rdkit.Chem import rdMolDescriptors
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

logger = logging.getLogger("sdo.backend.descriptors")

class LocalDescriptorEngine:
    """Calculates molecular descriptors locally using RDKit."""
    
    def __init__(self):
        if not RDKIT_AVAILABLE:
            logger.warning("RDKit is not available. Local descriptor calculation is disabled.")

    def calculate_from_smiles(self, smiles: str, mode: str = "fast", save_debug: bool = False) -> Dict[str, Any]:
        if not RDKIT_AVAILABLE or not smiles:
            return {"success": False, "error": "RDKit not available or SMILES empty"}
            
        try:
            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                return {"success": False, "error": "Invalid SMILES"}

            # Calculate fast mode (lightweight descriptors)
            data = {
                "MolecularWeight": Descriptors.ExactMolWt(mol),
                "MolecularFormula": rdMolDescriptors.CalcMolFormula(mol),
                "CanonicalSMILES": Chem.MolToSmiles(mol, isomericSmiles=False),
                "IsomericSMILES": Chem.MolToSmiles(mol, isomericSmiles=True),
                "XLogP": Descriptors.MolLogP(mol),
                "TPSA": Descriptors.TPSA(mol),
                "HBondDonorCount": Descriptors.NumHDonors(mol),
                "HBondAcceptorCount": Descriptors.NumHAcceptors(mol),
                "MolWt": Descriptors.ExactMolWt(mol),
                "LogP": Descriptors.MolLogP(mol),
                "HBA": Descriptors.NumHAcceptors(mol),
                "HBD": Descriptors.NumHDonors(mol),
                "RotatableBonds": Descriptors.NumRotatableBonds(mol),
                "RingCount": Descriptors.RingCount(mol),
                "HeavyAtomCount": Descriptors.HeavyAtomCount(mol),
                "FractionCSP3": Descriptors.FractionCSP3(mol)
            }
            
            try:
                data["InChIKey"] = Chem.MolToInchiKey(mol)
            except Exception:
                pass
                
            # --- DEBUG VERIFICATION START ---
            if save_debug:
                if not hasattr(self, 'all_descriptors_list'):
                    self.all_descriptors_list = []
                    
                canon_smiles = data.get("CanonicalSMILES", smiles)
                desc_count = len(data)
                desc_names = list(data.keys())
                
                self.all_descriptors_list.append(data)
                
                import pandas as pd
                import os
                
                df = pd.DataFrame(self.all_descriptors_list)
                df_shape = df.shape
                
                logger.info(f"CALCULATOR DEBUG: canonical_smiles='{canon_smiles}' | descriptor count={desc_count} | dataframe shape={df_shape}")
                logger.debug(f"CALCULATOR DEBUG: descriptor names={desc_names}")
                
                # Verify descriptors
                is_empty = df.empty
                rows_exist = df_shape[0] > 0
                cols_populated = df.notna().sum().sum() > 0
                
                string_cols = ["MolecularFormula", "CanonicalSMILES", "IsomericSMILES", "InChIKey"]
                numeric_cols = [c for c in df.columns if c not in string_cols]
                numeric_types_ok = True
                for col in numeric_cols:
                    if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                        numeric_types_ok = False
                        
                logger.info(f"VERIFY CALCULATOR: rows exist={rows_exist}, no empty dataframe={not is_empty}, columns are populated={cols_populated}, descriptors are numeric={numeric_types_ok}")
                
                os.makedirs("outputs", exist_ok=True)
                try:
                    df.to_excel("outputs/debug_descriptor_table.xlsx", index=False)
                except Exception:
                    df.to_csv("outputs/debug_descriptor_table.xlsx", index=False)
            # --- DEBUG VERIFICATION END ---
                
            return {"success": True, "data": data}
        except Exception as e:
            logger.error(f"RDKit calculation error for {smiles}: {e}")
            return {"success": False, "error": f"CALCULATION_FAILED: {str(e)}"}
