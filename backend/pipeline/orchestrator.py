import os
import pandas as pd
import logging
from typing import List, Dict, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

from backend.database.manager import DatabaseManager
from backend.database.session import init_db
from backend.descriptor_engine.rdkit_engine import RDKitEngine

logger = logging.getLogger("sdo.backend.orchestrator")

# Module level variables to cache the engines per process/thread (Windows-safe pickling)
_worker_rdkit_engine = None

def init_worker():
    global _worker_rdkit_engine
    # Set worker process priority lower than interactive threads to ensure
    # the operating system keeps the mouse, keyboard, and browser 100% responsive.
    try:
        import os
        import psutil
        import sys
        
        p = psutil.Process(os.getpid())
        if sys.platform == 'win32':
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        else:
            p.nice(10) # Safe Unix nice value
    except Exception as priority_err:
        logger.warning(f"Could not adjust worker process priority: {priority_err}")

    if _worker_rdkit_engine is None:
        from backend.descriptor_engine.rdkit_engine import RDKitEngine
        _worker_rdkit_engine = RDKitEngine()

def calculate_descriptors_worker(smiles: str, include_mordred: bool, mode: str = "fast") -> Dict[str, Any]:
    global _worker_rdkit_engine
    if _worker_rdkit_engine is None:
        from backend.descriptor_engine.rdkit_engine import RDKitEngine
        _worker_rdkit_engine = RDKitEngine()
    try:
        res = _worker_rdkit_engine.calculate_from_smiles(smiles, include_mordred=include_mordred, mode=mode)
        return {
            "smiles": smiles,
            "success": res.get("success", False),
            "data": res.get("data", {}),
            "error": res.get("error", "")
        }
    except Exception as e:
        return {
            "smiles": smiles,
            "success": False,
            "data": {},
            "error": str(e)
        }

class AsyncEnrichmentOrchestrator:
    """Orchestrates high-volume API enrichment and local calculation backed by a centralized database."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.local_engine = RDKitEngine()
        
    def initialize(self):
        """Initialize the database schema synchronously."""
        init_db()
        
    def _find_column_by_mapping(self, mappings: dict, target: str) -> str:
        for user_col, var_type in mappings.items():
            if var_type == target:
                return user_col
        return None

    def process_identifiers(self, identifiers: List[str], id_type: str, progress_callback=None, include_mordred: bool = False) -> Dict[str, Any]:
        """Process a list of identifiers concurrently using a synchronous ThreadPoolExecutor."""
        results = {}
        completed = 0
        
        # Concurrently process lookups and fetches using standard ThreadPoolExecutor
        max_workers = min(2, len(identifiers)) if len(identifiers) > 0 else 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ident = {
                executor.submit(self._process_single, ident, id_type, include_mordred): ident
                for ident in identifiers
            }
            
            for future in as_completed(future_to_ident):
                ident = future_to_ident[future]
                try:
                    res_ident, res = future.result()
                    results[res_ident] = res
                except Exception as e:
                    logger.error(f"Thread exception in process_identifiers for {ident}: {e}")
                    results[ident] = {"success": False, "error": f"THREAD_EXCEPTION: {e}"}
                    
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(identifiers), id_type)
                    
        return results

    def _map_to_db_schema(self, api_data: dict, id_type: str, original_ident: str) -> tuple:
        """Map raw API/local data to normalized database tables."""
        
        def safe_get(keys, cast_type=None):
            for k in keys:
                val = api_data.get(k)
                if val is not None:
                    try:
                        return cast_type(val) if cast_type else val
                    except (ValueError, TypeError):
                        pass
            return None

        compound_data = {
            "compound_name": original_ident if id_type == "name" else api_data.get("IUPACName"),
            "canonical_smiles": api_data.get("canonical_smiles") or api_data.get("CanonicalSMILES"),
            "inchi_key": api_data.get("InChIKey"),
            "pubchem_cid": str(api_data.get("CID")) if api_data.get("CID") else None,
            "molecular_formula": api_data.get("MolecularFormula"),
            "molecular_weight": safe_get(["MolecularWeight", "MolWt"], float)
        }
        
        descriptor_data = {
            "logp": safe_get(["XLogP", "LogP"], float),
            "tpsa": safe_get(["TPSA"], float),
            "h_bond_donors": safe_get(["HBondDonorCount", "HBD"], int),
            "h_bond_acceptors": safe_get(["HBondAcceptorCount", "HBA"], int),
            "molecular_descriptors_json": api_data
        }
        
        enrichment_data = {
            "pubchem_data": api_data,
            "fetch_status": "SUCCESS"
        }
        
        return compound_data, descriptor_data, enrichment_data

    def _process_single(self, identifier: str, id_type: str, include_mordred: bool = False, offline_selected_descriptors: list = None) -> Tuple[str, Any]:
        """Process a single identifier synchronously:
        1. Resolve identity using ChemicalIdentifierService
        2. Calculate descriptors locally using RDKit/Mordred
        3. Save descriptors to SQLite
        """
        if not identifier or not isinstance(identifier, str) or not identifier.strip():
            return identifier, {"success": False, "error": "EMPTY_IDENTIFIER"}

        identifier = identifier.strip()

        from backend.normalization.identifier_service import ChemicalIdentifierService
        service = ChemicalIdentifierService()

        # Step 1: Deterministic Identity Resolution (Cache-First + PubChem API resolution)
        id_res = service.resolve(identifier, id_type)

        if id_res.get("status") != "success" or not id_res.get("canonical_smiles"):
            error_msg = id_res.get("status") or "Identity resolution failed"
            self.db_manager.log_failed_fetch(identifier, id_type or "unknown", "IdentityResolutionService", error_msg)
            return identifier, {"success": False, "error": f"RESOLUTION_FAILED: {error_msg}"}

        resolved_smiles = id_res["canonical_smiles"]

        # Step 2: Descriptor generation happens ONLY locally via RDKit/Mordred
        local_res = self.local_engine.calculate_from_smiles(resolved_smiles, include_mordred=include_mordred)

        if local_res.get("success"):
            combined_data = {}
            # Keep local RDKit descriptors as the absolute source of truth
            combined_data.update(local_res["data"])

            # Map identity details from id_res
            combined_data["canonical_smiles"] = resolved_smiles
            combined_data["CanonicalSMILES"] = resolved_smiles
            combined_data["InChIKey"] = id_res.get("inchikey") or ""
            combined_data["InChI"] = id_res.get("inchi") or ""
            combined_data["MolecularFormula"] = id_res.get("molecular_formula") or ""
            combined_data["CID"] = id_res.get("cid") or ""
            combined_data["IUPACName"] = id_res.get("input_name") or ""

            # Save descriptor data to SQLite
            c_data, d_data, e_data = self._map_to_db_schema(combined_data, id_type, identifier)
            try:
                self.db_manager.save_compound(c_data, d_data, e_data)
            except Exception as e:
                logger.error(f"Error saving compound descriptors to SQLite: {e}")

            return identifier, {"success": True, "data": combined_data, "source": "local_rdkit"}
        else:
            error_msg = local_res.get("error", "Local descriptor calculation failed")
            self.db_manager.log_failed_fetch(identifier, "smiles", "Local Descriptor Engine", error_msg)
            return identifier, {"success": False, "error": f"DESCRIPTOR_CALCULATION_FAILED: {error_msg}"}


        


            

    def enrich_dataframe(self, 
                         df: pd.DataFrame, 
                         mappings: Dict[str, str], 
                         selected_descriptors: List[str], 
                         api_properties: List[str] = None,
                         progress_callback=None, 
                         include_mordred: bool = False,
                         offline_selected_descriptors: List[str] = None,
                         mode: str = "fast") -> Tuple[pd.DataFrame, List[dict]]:
        """Synchronous chemical enrichment pipeline supporting two-phase parallel calculations."""
        
        self.initialize()
        
        if selected_descriptors is None:
            selected_descriptors = []
        if offline_selected_descriptors is None:
            offline_selected_descriptors = []
            
        enriched_df = df.copy()
        audit_logs = []
        
        smiles_col = self._find_column_by_mapping(mappings, 'canonical_smiles') or self._find_column_by_mapping(mappings, 'smiles')
        name_col = self._find_column_by_mapping(mappings, 'chemical_id') or self._find_column_by_mapping(mappings, 'chemical_name')
        
        # Initialize columns
        for desc in selected_descriptors:
            if desc not in enriched_df.columns:
                enriched_df[desc] = None
        if 'PubChem_Error' not in enriched_df.columns:
            enriched_df['PubChem_Error'] = None
            
        # Extract unique valid identifiers
        unique_smiles = []
        if smiles_col and smiles_col in enriched_df.columns:
            mask = enriched_df[smiles_col].notna() & (enriched_df[smiles_col].astype(str).str.strip() != "")
            unique_smiles = enriched_df.loc[mask, smiles_col].astype(str).str.strip().unique().tolist()
            
        unique_names = []
        if name_col and name_col in enriched_df.columns:
            if smiles_col and smiles_col in enriched_df.columns:
                no_smiles = enriched_df[smiles_col].isna() | (enriched_df[smiles_col].astype(str).str.strip() == "")
                valid_name = enriched_df[name_col].notna() & (enriched_df[name_col].astype(str).str.strip() != "")
                unique_names = enriched_df.loc[no_smiles & valid_name, name_col].astype(str).str.strip().unique().tolist()
            else:
                valid_name = enriched_df[name_col].notna() & (enriched_df[name_col].astype(str).str.strip() != "")
                unique_names = enriched_df.loc[valid_name, name_col].astype(str).str.strip().unique().tolist()

        total_unique = len(unique_smiles) + len(unique_names)
        
        if progress_callback and total_unique > 0:
            progress_callback(0, total_unique)

        # ─── PHASE 1: Throttled Online Identity Resolution (Safe & Slow) ───
        from backend.normalization.identifier_service import ChemicalIdentifierService
        import os
        service = ChemicalIdentifierService()
        
        all_unique_idents = []
        if unique_smiles:
            all_unique_idents.extend([(uid, "smiles") for uid in unique_smiles])
        if unique_names:
            all_unique_idents.extend([(uid, "name") for uid in unique_names])
            
        resolution_results = []
        has_smiles_count = 0
        missing_smiles_count = 0
        
        def _resolve_and_log(ident, id_type):
            id_res = service.resolve(ident, id_type)
            canon_smiles = id_res.get("canonical_smiles")
            inchikey = id_res.get("inchikey")
            status = id_res.get("status", "unknown")
            error_msg = id_res.get("error", "No canonical smiles generated") if not canon_smiles else ""
            
            logger.info(f"DEBUG NORM: Input='{ident}' | Type='{id_type}' | CanonicalSMILES='{canon_smiles}' | InChIKey='{inchikey}'")
            
            return {
                "original compound": ident,
                "canonical_smiles": canon_smiles,
                "inchikey": inchikey,
                "resolution status": status,
                "error message": error_msg,
                "id_type": id_type,
                "id_res": id_res
            }
            
        if all_unique_idents:
            logger.info(f"Starting Phase 1 (Throttled Online Identity Resolution) for {len(all_unique_idents)} unique compounds...")
            max_workers = min(2, len(all_unique_idents))
            completed_count = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(_resolve_and_log, ident, id_type): (ident, id_type)
                    for ident, id_type in all_unique_idents
                }
                for future in as_completed(futures):
                    ident, id_type = futures[future]
                    try:
                        resolution_results.append(future.result())
                    except Exception as e:
                        logger.error(f"Thread exception in identity resolution pass for {ident}: {e}")
                    completed_count += 1
                    if progress_callback:
                        progress_val = int(completed_count / len(all_unique_idents) * total_unique * 0.4)
                        progress_callback(min(progress_val, total_unique), total_unique)
            
        resolved_compounds = {}
        smiles_to_id_res = {}
        for res in resolution_results:
            original_ident = res["original compound"]
            id_res = res["id_res"]
            resolved_compounds[original_ident] = id_res
            
            cs = id_res.get("canonical_smiles")
            if cs:
                id_res["id_type"] = res["id_type"]
                if cs not in smiles_to_id_res:
                    smiles_to_id_res[cs] = id_res
            
        for res in resolution_results:
            if res["canonical_smiles"]:
                has_smiles_count += 1
            else:
                missing_smiles_count += 1
                
        total_compounds = len(resolution_results)
        logger.info(f"VALIDATION COUNT: total compounds={total_compounds}, compounds with canonical_smiles={has_smiles_count}, compounds without canonical_smiles={missing_smiles_count}")
        
        # EXPORT DEBUG FILE
        os.makedirs("outputs", exist_ok=True)
        debug_df = pd.DataFrame(resolution_results)
        if "id_res" in debug_df.columns:
            debug_df = debug_df.drop(columns=["id_res"])
        try:
            debug_df.to_excel("outputs/debug_canonical_smiles.xlsx", index=False)
        except ModuleNotFoundError:
            debug_df.to_csv("outputs/debug_canonical_smiles.xlsx", index=False)
            logger.warning("openpyxl missing, saved excel as CSV format with .xlsx extension")
        
        if missing_smiles_count > 0:
            logger.error(f"WARNING: {missing_smiles_count} compounds failed to generate canonical_smiles.")
            audit_logs.append({
                "issue": "Canonical SMILES Generation Failed",
                "details": f"{missing_smiles_count} compounds lack canonical SMILES. Check outputs/debug_canonical_smiles.xlsx for details."
            })
        # ─── END PHASE 1 ───

        # ─── PHASE 2: Parallelized Offline QSAR Calculation (Maximum CPU Speed) ───
        all_resolved_smiles = list(smiles_to_id_res.keys())
        cached_results = {}
        smiles_to_calculate = []
        
        for smiles in all_resolved_smiles:
            db_hit = self.db_manager.get_compound_by_identifier(smiles)
            if db_hit and db_hit.get("descriptor") and db_hit["descriptor"].molecular_descriptors_json:
                cached_desc = db_hit["descriptor"].molecular_descriptors_json
                # Check if it has RDKit descriptors
                has_rdkit = "MolWt" in cached_desc or "MolLogP" in cached_desc
                # Check if it has Mordred descriptors if requested
                has_mordred = "ABC" in cached_desc if include_mordred else True
                
                if has_rdkit and has_mordred:
                    logger.info(f"CACHE HIT: Compound {smiles} fully cached in SQLite database.")
                    cached_results[smiles] = cached_desc
                    continue
            
            # Cache miss
            smiles_to_calculate.append(smiles)
            
        logger.info(f"Cache lookup summary: {len(cached_results)} hits, {len(smiles_to_calculate)} misses.")
        
        calculated_results = {}
        if smiles_to_calculate:
            logger.info(f"Phase 2: Calculating local descriptors for {len(smiles_to_calculate)} compounds...")
            import os
            
            # Balance CPU core allocation: use 50% of available cores (min 1, max 4) to ensure
            # that Streamlit, the web browser, and the OS UI remain completely lag-free.
            num_workers = min(4, max(1, os.cpu_count() // 2))
            logger.info(f"Spawning parallel workers (concurrency level: {num_workers}) using ProcessPoolExecutor...")
            
            completed_calcs = 0
            
            try:
                with ProcessPoolExecutor(max_workers=num_workers, initializer=init_worker) as executor:
                    future_to_smiles = {
                        executor.submit(calculate_descriptors_worker, smiles, include_mordred, mode): smiles
                        for smiles in smiles_to_calculate
                    }
                    
                    for future in as_completed(future_to_smiles):
                        smiles = future_to_smiles[future]
                        try:
                            res = future.result()
                            calculated_results[smiles] = res
                        except Exception as e:
                            logger.error(f"Process worker execution error for SMILES {smiles}: {e}")
                            calculated_results[smiles] = {"smiles": smiles, "success": False, "error": str(e)}
                        
                        completed_calcs += 1
                        if progress_callback:
                            progress_val = int(total_unique * 0.4 + (completed_calcs / len(smiles_to_calculate)) * total_unique * 0.6)
                            progress_callback(min(progress_val, total_unique), total_unique)
            except Exception as pe:
                logger.error(f"Failed to execute ProcessPoolExecutor, falling back to ThreadPoolExecutor: {pe}")
                with ThreadPoolExecutor(max_workers=2) as executor:
                    future_to_smiles = {
                        executor.submit(calculate_descriptors_worker, smiles, include_mordred, mode): smiles
                        for smiles in smiles_to_calculate
                    }
                    for future in as_completed(future_to_smiles):
                        smiles = future_to_smiles[future]
                        try:
                            res = future.result()
                            calculated_results[smiles] = res
                        except Exception as e:
                            logger.error(f"Thread worker execution error for SMILES {smiles}: {e}")
                            calculated_results[smiles] = {"smiles": smiles, "success": False, "error": str(e)}
                        
                        completed_calcs += 1
                        if progress_callback:
                            progress_val = int(total_unique * 0.4 + (completed_calcs / len(smiles_to_calculate)) * total_unique * 0.6)
                            progress_callback(min(progress_val, total_unique), total_unique)
        else:
            if progress_callback and total_unique > 0:
                progress_callback(total_unique, total_unique)
                
        # ─── SEQUENTIAL SAFE WRITE TO SQLITE (Eliminates write collision lockups) ───
        if calculated_results:
            logger.info("Writing newly calculated descriptors to SQLite database sequentially...")
            for smiles, res in calculated_results.items():
                if res.get("success") and res.get("data"):
                    id_res = smiles_to_id_res.get(smiles)
                    if not id_res:
                        continue
                        
                    combined_data = {}
                    combined_data.update(res["data"])
                    
                    combined_data["canonical_smiles"] = smiles
                    combined_data["CanonicalSMILES"] = smiles
                    combined_data["InChIKey"] = id_res.get("inchikey") or ""
                    combined_data["InChI"] = id_res.get("inchi") or ""
                    combined_data["MolecularFormula"] = id_res.get("molecular_formula") or ""
                    combined_data["CID"] = id_res.get("cid") or ""
                    combined_data["IUPACName"] = id_res.get("input_name") or ""
                    
                    c_data, d_data, e_data = self._map_to_db_schema(combined_data, id_res.get("id_type", "smiles"), id_res.get("input_name"))
                    try:
                        self.db_manager.save_compound(c_data, d_data, e_data)
                    except Exception as e:
                        logger.error(f"Sequential SQLite write error for SMILES {smiles}: {e}")
        # ─── END PHASE 2 ───

        # ─── POPULATE Downstream compat structures smiles_results & name_results ───
        smiles_results = {}
        name_results = {}
        
        for original_ident, id_res in resolved_compounds.items():
            canon_smiles = id_res.get("canonical_smiles")
            if not canon_smiles:
                res_obj = {"success": False, "error": id_res.get("status") or "Identity resolution failed"}
            else:
                if canon_smiles in cached_results:
                    desc_data = cached_results[canon_smiles]
                    combined_data = {}
                    combined_data.update(desc_data)
                    combined_data["canonical_smiles"] = canon_smiles
                    combined_data["CanonicalSMILES"] = canon_smiles
                    combined_data["InChIKey"] = id_res.get("inchikey") or ""
                    combined_data["InChI"] = id_res.get("inchi") or ""
                    combined_data["MolecularFormula"] = id_res.get("molecular_formula") or ""
                    combined_data["CID"] = id_res.get("cid") or ""
                    combined_data["IUPACName"] = id_res.get("input_name") or ""
                    
                    res_obj = {"success": True, "data": combined_data, "source": "cache"}
                elif canon_smiles in calculated_results:
                    calc_res = calculated_results[canon_smiles]
                    if calc_res.get("success"):
                        combined_data = {}
                        combined_data.update(calc_res["data"])
                        combined_data["canonical_smiles"] = canon_smiles
                        combined_data["CanonicalSMILES"] = canon_smiles
                        combined_data["InChIKey"] = id_res.get("inchikey") or ""
                        combined_data["InChI"] = id_res.get("inchi") or ""
                        combined_data["MolecularFormula"] = id_res.get("molecular_formula") or ""
                        combined_data["CID"] = id_res.get("cid") or ""
                        combined_data["IUPACName"] = id_res.get("input_name") or ""
                        
                        res_obj = {"success": True, "data": combined_data, "source": "local_rdkit"}
                    else:
                        res_obj = {"success": False, "error": calc_res.get("error") or "Descriptor calculation failed"}
                else:
                    res_obj = {"success": False, "error": "Descriptor calculation not run or failed"}
                    
            if original_ident in unique_smiles:
                smiles_results[original_ident] = res_obj
            else:
                name_results[original_ident] = res_obj
            
        # API key mapping
        _DESC_TO_API = {
            "PubChem_CID":       ["CID"],
            "canonical_smiles":  ["canonical_smiles", "CanonicalSMILES"],
            "Isomeric_SMILES":   ["IsomericSMILES"],
            "InChIKey":          ["InChIKey"],
            "InChI":             ["InChI"],
            "IUPAC_Name":        ["IUPACName"],
            "Molecular_Weight":  ["MolecularWeight", "MolWt"],
            "Molecular_Formula": ["MolecularFormula"],
            "XLogP":             ["XLogP", "LogP"],
            "TPSA":              ["TPSA"],
            "HB_Donor_Count":    ["HBondDonorCount", "HBD"],
            "HB_Acceptor_Count": ["HBondAcceptorCount", "HBA"],
        }
        
        # Create a mapping dictionary for fast vectorized lookup
        id_to_data = {}
        id_to_error = {}
        
        for identifier, res in smiles_results.items():
            if res.get("success"):
                id_to_data[identifier] = res.get("data", {})
            else:
                id_to_error[identifier] = res.get("error", "FETCH_FAILED")
                
        for identifier, res in name_results.items():
            if res.get("success"):
                id_to_data[identifier] = res.get("data", {})
            else:
                id_to_error[identifier] = res.get("error", "FETCH_FAILED")

        # List of descriptor records to build the unique descriptors DataFrame
        unique_records = []
        all_cols_to_assemble = list(set(selected_descriptors + offline_selected_descriptors))
        
        for identifier, data in id_to_data.items():
            record = {"__join_identifier__": identifier}
            
            # 1. Base PubChem Descriptors mapping
            for desc_name in selected_descriptors:
                api_keys = _DESC_TO_API.get(desc_name, [desc_name])
                val = None
                for api_key in api_keys:
                    if api_key in data and data[api_key] is not None:
                        val = data[api_key]
                        break
                
                if val is None:
                    if "CanonicalSMILES" in api_keys and 'IsomericSMILES' in data:
                        val = str(data['IsomericSMILES'])
                    elif "IsomericSMILES" in api_keys and 'CanonicalSMILES' in data:
                        val = str(data['CanonicalSMILES'])
                
                # Basic parsing/cleanup
                string_only = ["canonical_smiles", "Isomeric_SMILES", "InChIKey", "InChI", "IUPAC_Name", "Molecular_Formula", "MolecularFormula"]
                if desc_name not in string_only and val is not None:
                    try:
                        if float(val).is_integer():
                            val = int(float(val))
                        else:
                            val = float(val)
                    except (ValueError, TypeError):
                        pass
                record[desc_name] = val
                
            # 2. Offline Descriptors mapping
            for key in offline_selected_descriptors:
                if key not in selected_descriptors:
                    val = data.get(key)
                    if pd.notna(val):
                        string_only = ["canonical_smiles", "Isomeric_SMILES", "InChIKey", "InChI", "IUPAC_Name", "Molecular_Formula", "MolecularFormula"]
                        if key not in string_only:
                            try:
                                if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.','',1).isdigit()):
                                    f_val = float(val)
                                    if f_val.is_integer():
                                        val = int(f_val)
                                    else:
                                        val = f_val
                            except (ValueError, TypeError):
                                pass
                        record[key] = val
            
            unique_records.append(record)

        if unique_records:
            descriptors_df = pd.DataFrame(unique_records)
        else:
            descriptors_df = pd.DataFrame(columns=["__join_identifier__"] + all_cols_to_assemble)

        # Determine for each row which identifier to join on
        def get_join_id(row):
            if smiles_col and pd.notna(row.get(smiles_col)) and str(row.get(smiles_col, "")).strip():
                return str(row[smiles_col]).strip()
            elif name_col and pd.notna(row.get(name_col)) and str(row.get(name_col, "")).strip():
                return str(row[name_col]).strip()
            return None
            
        enriched_df["__join_identifier__"] = enriched_df.apply(get_join_id, axis=1)
        
        # Populate PubChem_Error column dynamically in a vectorized way
        def get_row_error(jid):
            if not jid:
                return "MISSING_IDENTITY"
            if jid in id_to_error:
                return id_to_error[jid]
            if jid not in id_to_data:
                return "FETCH_FAILED"
            return None
            
        # Map row errors
        enriched_df["PubChem_Error"] = enriched_df["__join_identifier__"].map(get_row_error)

        # Drop columns from enriched_df if they already exist in the descriptors_df to prevent _x, _y suffixes
        cols_to_drop = [c for c in all_cols_to_assemble if c in enriched_df.columns]
        if cols_to_drop:
            enriched_df = enriched_df.drop(columns=cols_to_drop)
            
        # Perform single, lightning-fast vectorized merge!
        enriched_df = pd.merge(enriched_df, descriptors_df, on="__join_identifier__", how="left")
        
        # Drop the temporary join column
        enriched_df = enriched_df.drop(columns=["__join_identifier__"])
 
        # ── EXPORT OPTIMIZATION & VALIDATION ────────────────────────────
        logger.info("[ENRICHMENT] === PRE-EXPORT VALIDATION ===")
        total_rows = len(enriched_df)
        
        # Column Difference Tracker
        prev_cols = set(df.columns)
        next_cols = set(enriched_df.columns)
        added_cols = list(next_cols - prev_cols)
        removed_cols = list(prev_cols - next_cols)
        logger.info(f"[ENRICHMENT] Column Difference Tracker -> Added: {added_cols} | Removed: {removed_cols}")
        
        for desc_name in selected_descriptors:
            if desc_name in enriched_df.columns:
                non_empty = enriched_df[desc_name].notna() & (enriched_df[desc_name].astype(str).str.strip() != '') & (enriched_df[desc_name].astype(str) != 'None')
                pct = (non_empty.sum() / total_rows * 100) if total_rows > 0 else 0
                logger.info(f"[ENRICHMENT]   {desc_name}: {non_empty.sum()}/{total_rows} populated ({pct:.1f}%)")
                
        # Cast ALL new descriptor columns to true numeric types where applicable
        import warnings
        from pandas.errors import PerformanceWarning
        warnings.simplefilter(action='ignore', category=PerformanceWarning)
        
        all_cols_to_cast = set(selected_descriptors + offline_selected_descriptors)
        
        for col_name in all_cols_to_cast:
            if col_name in enriched_df.columns:
                string_only_descriptors = ["canonical_smiles", "Isomeric_SMILES", "InChIKey", "InChI", "IUPAC_Name", "Molecular_Formula", "MolecularFormula", "PubChem_Error", "success", "error", "source"]
                if col_name not in string_only_descriptors:
                    try:
                        enriched_df[col_name] = pd.to_numeric(enriched_df[col_name], errors='coerce')
                    except Exception:
                        pass
 
        failed_mask = enriched_df['PubChem_Error'].notna() & (enriched_df['PubChem_Error'] != 'None')
        failed_count = failed_mask.sum()
        populated_count = total_rows - failed_count
        
        logger.info(f"[ENRICHMENT]   Total Rows: {total_rows}")
        logger.info(f"[ENRICHMENT]   Populated:  {populated_count}")
        logger.info(f"[ENRICHMENT]   Failed:     {failed_count}")
        
        if failed_count > 0:
            audit_logs.append({
                "issue": "API/Calculation Failures",
                "details": f"{failed_count} compounds failed to enrich completely. Check 'PubChem_Error' column for details."
            })
            
        return enriched_df, audit_logs

    def enrich_dataframe_async(self, *args, **kwargs):
        """Fully synchronous alias for backward compatibility."""
        return self.enrich_dataframe(*args, **kwargs)

# Keep standard aliases to ensure zero import disruptions
EnrichmentOrchestrator = AsyncEnrichmentOrchestrator
