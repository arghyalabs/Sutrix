import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from backend.api_clients.pubchem_plugin import PubChemPlugin
from backend.api_clients.chembl_plugin import ChEMBLPlugin
from backend.api_clients.uniprot_plugin import UniProtPlugin

logger = logging.getLogger("sdo.enrichment")

class ScientificEnrichmentManager:
    """Orchestrates API enrichment of datasets."""
    
    def __init__(self):
        self.pubchem = PubChemPlugin(cache_enabled=True)
        self.chembl = ChEMBLPlugin(cache_enabled=True)
        self.uniprot = UniProtPlugin(cache_enabled=True)
        
    def _find_column_by_mapping(self, mappings: Dict[str, str], target: str) -> str:
        """Find the original dataframe column mapped to a specific scientific variable."""
        for user_col, sci_var in mappings.items():
            if sci_var == target:
                return user_col
        return None

    def _find_chemical_column(self, mappings: Dict[str, str]) -> str:
        """Find the chemical/substance identity column trying multiple aliases.
        
        The synonym mapper may canonicalize to 'chemical_id', 'chemical_name',
        or 'cas_number' depending on the source column name. We check all of
        them in priority order.
        """
        for alias in ('chemical_id', 'chemical_name', 'cas_number'):
            col = self._find_column_by_mapping(mappings, alias)
            if col:
                return col
        return None
        
    def _find_mw_column(self, df: pd.DataFrame, mappings: Dict[str, str]) -> str:
        """Try to find a Molecular Weight column either by mapping or heuristic name."""
        mapped = self._find_column_by_mapping(mappings, 'molecular_weight')
        if mapped and mapped in df.columns:
            return mapped
            
        for col in df.columns:
            col_lower = str(col).lower()
            if 'molecular weight' in col_lower or 'mw' == col_lower.strip():
                return col
        return None

    def enrich_dataframe(self, df: pd.DataFrame, mappings: Dict[str, str], progress_callback=None) -> Tuple[pd.DataFrame, List[dict]]:
        """
        Enriches a dataframe with PubChem data.
        Returns the enriched dataframe and a list of audit discrepancy logs.
        """
        enriched_df = df.copy()
        
        smiles_col = self._find_column_by_mapping(mappings, 'smiles')
        name_col = self._find_chemical_column(mappings)
        orig_mw_col = self._find_mw_column(df, mappings)
        
        # New columns to add
        enriched_df['PubChem_CID'] = ""
        enriched_df['PubChem_MW'] = np.nan
        enriched_df['PubChem_CanonicalSMILES'] = ""
        enriched_df['PubChem_InChIKey'] = ""
        enriched_df['PubChem_Ambiguous'] = False
        enriched_df['PubChem_Candidate_CIDs'] = ""
        enriched_df['PubChem_Error'] = ""
        
        audit_logs = []
        
        # STAGE 1: Exact Match Batching for SMILES
        unique_smiles = []
        if smiles_col and smiles_col in enriched_df.columns:
            # Extract valid SMILES
            valid_mask = enriched_df[smiles_col].notna() & (enriched_df[smiles_col].astype(str).str.strip() != "")
            unique_smiles = enriched_df.loc[valid_mask, smiles_col].astype(str).str.strip().unique().tolist()
            
        # STAGE 2: Unique Name Deduplication
        unique_names = []
        if name_col and name_col in enriched_df.columns:
            # Extract valid Names that do NOT have a SMILES (since SMILES has priority)
            if smiles_col and smiles_col in enriched_df.columns:
                no_smiles_mask = enriched_df[smiles_col].isna() | (enriched_df[smiles_col].astype(str).str.strip() == "")
                valid_name_mask = enriched_df[name_col].notna() & (enriched_df[name_col].astype(str).str.strip() != "")
                valid_mask = no_smiles_mask & valid_name_mask
            else:
                valid_mask = enriched_df[name_col].notna() & (enriched_df[name_col].astype(str).str.strip() != "")
                
            unique_names = enriched_df.loc[valid_mask, name_col].astype(str).str.strip().unique().tolist()

        total_unique = len(unique_smiles) + len(unique_names)
        processed_count = 0
            
        smiles_results = {}
        if unique_smiles:
            # Chunk into batches of 100 to prevent payload too large/timeout
            chunk_size = 100
            for i in range(0, len(unique_smiles), chunk_size):
                chunk = unique_smiles[i:i+chunk_size]
                batch_res = self.pubchem.fetch_batch(chunk, identifier_type="smiles", 
                    properties=['MolecularWeight', 'CanonicalSMILES', 'InChIKey'])
                smiles_results.update(batch_res)
                
                processed_count += len(chunk)
                if progress_callback:
                    progress_callback(processed_count, total_unique)
                    
        name_results = {}
        if unique_names:
            for ident in unique_names:
                name_results[ident] = self.pubchem.fetch(ident, identifier_type="name")
                processed_count += 1
                if progress_callback:
                    progress_callback(processed_count, total_unique)
                
        # Determine value column to enforce qsar_ready logic later
        val_col = self._find_column_by_mapping(mappings, 'value')
        qsar_col = f"{val_col}_qsar_ready" if val_col else None
        
        # Add Substance provenance column:
        # If the dataset already has a substance name column, we add a CAS Number
        # column instead of duplicating the substance name.
        # If no substance name exists, we add Substance_Original for traceability.
        self._add_substance_provenance(enriched_df, name_col)
                
        # Iterative Overlay & STAGE 3 Single Name Fetch
        for idx, row in enriched_df.iterrows():
            identifier = None
            id_type = None
            result = None
            
            # STAGE 1 & 2: Process SMILES if present
            if smiles_col and pd.notna(row[smiles_col]) and str(row[smiles_col]).strip():
                identifier = str(row[smiles_col]).strip()
                id_type = "smiles"
                result = smiles_results.get(identifier)
            # STAGE 3: Individual Name Verification
            elif name_col and pd.notna(row[name_col]) and str(row[name_col]).strip():
                identifier = str(row[name_col]).strip()
                id_type = "name"
                result = name_results.get(identifier)
                
            if not identifier:
                enriched_df.at[idx, 'PubChem_Error'] = "Missing Identity"
                continue
                
            if not result:
                enriched_df.at[idx, 'PubChem_Error'] = "API Error: No result generated"
                continue
                
            # Handle Ambiguity Flag
            if result.ambiguous:
                enriched_df.at[idx, 'PubChem_Ambiguous'] = True
                enriched_df.at[idx, 'PubChem_Candidate_CIDs'] = ",".join(result.candidate_ids)
                enriched_df.at[idx, 'PubChem_Error'] = "Ambiguous Identity"
                audit_logs.append({
                    "row": idx,
                    "issue": "Ambiguous Identity",
                    "details": f"Searched '{identifier}' ({id_type}) - Found {len(result.candidate_ids)} candidates."
                })
                continue
                
            if not result.success:
                enriched_df.at[idx, 'PubChem_Error'] = result.error
                continue
                
            # STAGE 4: Metadata Overlay
            cid = result.data.get('CID', '')
            if cid:
                enriched_df.at[idx, 'PubChem_CID'] = str(cid)
                # We do NOT overwrite the original mapped chemical_id
                # (User request: Identity Preservation)
                    
            pub_mw_str = result.data.get('MolecularWeight', '')
            pub_mw = None
            if pub_mw_str:
                try:
                    pub_mw = float(pub_mw_str)
                    enriched_df.at[idx, 'PubChem_MW'] = pub_mw
                except ValueError:
                    pass
                    
            # Molar Normalization "Safety Catch": If MW is missing, set qsar_ready to False
            if pub_mw is None and qsar_col and qsar_col in enriched_df.columns:
                enriched_df.at[idx, qsar_col] = False
                
            enriched_df.at[idx, 'PubChem_CanonicalSMILES'] = result.data.get('CanonicalSMILES', result.data.get('SMILES', result.data.get('IsomericSMILES', '')))
            enriched_df.at[idx, 'PubChem_InChIKey'] = result.data.get('InChIKey', '')
            
            # Data Verification logic
            if orig_mw_col and pd.notna(row[orig_mw_col]) and pub_mw is not None:
                try:
                    orig_mw = float(row[orig_mw_col])
                    diff_percent = abs(orig_mw - pub_mw) / pub_mw * 100
                    if diff_percent > 1.0:
                        audit_logs.append({
                            "row": idx,
                            "issue": "Data Discrepancy",
                            "details": f"Row {idx}: Original MW ({orig_mw}) vs PubChem MW ({pub_mw}) diff >1% ({diff_percent:.2f}%)"
                        })
                except ValueError:
                    pass
                    
        # Post-processing: resolve CAS numbers from PubChem CIDs
        if name_col and name_col in enriched_df.columns and 'PubChem_CAS' not in enriched_df.columns:
            self._resolve_cas_from_cids(enriched_df)
        
        return enriched_df, audit_logs

    def _add_substance_provenance(self, df: pd.DataFrame, name_col: str) -> None:
        """
        Add substance provenance column.
        
        If the dataset already has a substance name column, we DON'T duplicate it.
        Instead we add a PubChem_CAS column (populated later from CIDs).
        If no substance name exists, we add Substance_Original for traceability.
        """
        if name_col and name_col in df.columns:
            # Dataset has substance names — prepare CAS column (populated after enrichment)
            if 'PubChem_CAS' not in df.columns:
                df['PubChem_CAS'] = ""
        else:
            # No substance name — can't do CAS lookup
            pass
    
    def _resolve_cas_from_cids(self, df: pd.DataFrame) -> None:
        """
        For rows that have a PubChem CID, attempt to fetch the CAS Registry Number
        from PubChem synonyms endpoint and populate the PubChem_CAS column.
        """
        import requests
        import re
        
        if 'PubChem_CAS' not in df.columns or 'PubChem_CID' not in df.columns:
            return
        
        # Get unique CIDs that need CAS lookup
        unique_cids = df.loc[
            (df['PubChem_CID'].astype(str).str.strip() != '') & 
            (df['PubChem_CAS'].astype(str).str.strip() == ''),
            'PubChem_CID'
        ].astype(str).str.strip().unique().tolist()
        
        if not unique_cids:
            return
        
        cas_pattern = re.compile(r'^\d{2,7}-\d{2}-\d$')
        cid_to_cas = {}
        
        for cid in unique_cids:
            try:
                self.pubchem._respect_rate_limit()
                url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/synonyms/JSON"
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    synonyms = data.get('InformationList', {}).get('Information', [{}])[0].get('Synonym', [])
                    for syn in synonyms:
                        if cas_pattern.match(syn):
                            cid_to_cas[cid] = syn
                            break
            except Exception:
                pass
        
        # Vectorized update
        if cid_to_cas:
            cid_str = df['PubChem_CID'].astype(str).str.strip()
            df['PubChem_CAS'] = cid_str.map(cid_to_cas).fillna(df['PubChem_CAS'])

    # ═══════════════════════════════════════════════════════════════════
    # Selective PubChem Enrichment (Step 4)
    # ═══════════════════════════════════════════════════════════════════

    def enrich_dataframe_selective(
        self,
        df: pd.DataFrame,
        mappings: Dict[str, str],
        selected_descriptors: List[str],
        api_properties: List[str],
        progress_callback=None,
    ) -> Tuple[pd.DataFrame, List[dict]]:
        """
        Enriches a dataframe with only the user-selected PubChem descriptors.

        Unlike ``enrich_dataframe()``, this method:
        - Only creates columns for descriptors the user chose.
        - Uses the dynamic ``api_properties`` list to build the PubChem URL.
        - Returns the enriched df and an audit log list.

        Args:
            df:                   Input dataframe.
            mappings:             {user_col: scientific_var} dict.
            selected_descriptors: List of user-friendly descriptor names
                                  (e.g. 'PubChem_CID', 'Canonical_SMILES').
            api_properties:       List of PubChem API property keys to fetch
                                  (e.g. 'CanonicalSMILES', 'MolecularWeight').
            progress_callback:    Optional fn(current, total) for UI progress.
        """
        # Map from user-friendly name → PubChem API key
        _DESC_TO_API = {
            "PubChem_CID":       None,               # resolved from URL path
            "Canonical_SMILES":  "CanonicalSMILES",
            "Isomeric_SMILES":   "IsomericSMILES",
            "InChIKey":          "InChIKey",
            "IUPAC_Name":        "IUPACName",
            "Molecular_Weight":  "MolecularWeight",
            "Molecular_Formula": "MolecularFormula",
            "XLogP":             "XLogP",
            "TPSA":              "TPSA",
            "HB_Donor_Count":    "HBondDonorCount",
            "HB_Acceptor_Count": "HBondAcceptorCount",
        }

        enriched_df = df.copy()
        audit_logs: List[dict] = []

        smiles_col = self._find_column_by_mapping(mappings, 'smiles')
        name_col = self._find_chemical_column(mappings)
        orig_mw_col = self._find_mw_column(df, mappings)

        logger.info("[ENRICHMENT] Starting selective enrichment")
        logger.info("[ENRICHMENT]   SMILES column: %s", smiles_col)
        logger.info("[ENRICHMENT]   Name column:   %s", name_col)
        logger.info("[ENRICHMENT]   MW column:     %s", orig_mw_col)
        logger.info("[ENRICHMENT]   Descriptors:   %s", selected_descriptors)
        logger.info("[ENRICHMENT]   API props:     %s", api_properties)

        # ── Purge poisoned cache entries ─────────────────────────────────
        # Previous versions had a bug where batch POST for 'name' lookups
        # returned 404 and cached ALL compounds as 'Not Found'. Purge these
        # stale failures so fresh API calls are made.
        purged = self.pubchem.purge_failed_cache_entries()
        if purged > 0:
            logger.info("[ENRICHMENT] Purged %d stale/failed cache entries", purged)

        # Initialize only the columns the user selected
        # Use None so pandas infers object dtype, allowing mixed str/numeric writes
        for desc_name in selected_descriptors:
            if desc_name not in enriched_df.columns:
                enriched_df[desc_name] = None

        # Convenience error column
        if 'PubChem_Error' not in enriched_df.columns:
            enriched_df['PubChem_Error'] = None

        # ── Collect unique identifiers ──────────────────────────────────
        unique_smiles: list = []
        if smiles_col and smiles_col in enriched_df.columns:
            valid_mask = enriched_df[smiles_col].notna() & (enriched_df[smiles_col].astype(str).str.strip() != "")
            unique_smiles = enriched_df.loc[valid_mask, smiles_col].astype(str).str.strip().unique().tolist()

        unique_names: list = []
        if name_col and name_col in enriched_df.columns:
            if smiles_col and smiles_col in enriched_df.columns:
                no_smiles = enriched_df[smiles_col].isna() | (enriched_df[smiles_col].astype(str).str.strip() == "")
                valid_name = enriched_df[name_col].notna() & (enriched_df[name_col].astype(str).str.strip() != "")
                unique_names = enriched_df.loc[no_smiles & valid_name, name_col].astype(str).str.strip().unique().tolist()
            else:
                valid_name = enriched_df[name_col].notna() & (enriched_df[name_col].astype(str).str.strip() != "")
                unique_names = enriched_df.loc[valid_name, name_col].astype(str).str.strip().unique().tolist()

        total_unique = len(unique_smiles) + len(unique_names)
        processed_count = 0

        logger.info("[ENRICHMENT] Unique SMILES: %d, Unique Names: %d, Total: %d",
                    len(unique_smiles), len(unique_names), total_unique)

        import concurrent.futures

        # ── Batch fetch SMILES (true batch POST — efficient) ────────────
        smiles_results: dict = {}
        if unique_smiles:
            logger.info("[ENRICHMENT] Fetching %d unique SMILES (batch POST)...", len(unique_smiles))
            chunk_size = 100  # Smaller chunks for reliable batch POST
            chunks = [unique_smiles[i:i + chunk_size] for i in range(0, len(unique_smiles), chunk_size)]

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(
                        self.pubchem.fetch_batch, chunk, identifier_type="smiles", properties=api_properties
                    ): chunk
                    for chunk in chunks
                }
                for future in concurrent.futures.as_completed(futures):
                    chunk = futures[future]
                    try:
                        chunk_results = future.result()
                        smiles_results.update(chunk_results)
                        successes = sum(1 for r in chunk_results.values() if r.success)
                        failures = len(chunk_results) - successes
                        logger.info("[ENRICHMENT] SMILES chunk done: %d/%d succeeded, %d failed",
                                    successes, len(chunk_results), failures)
                    except Exception as e:
                        logger.error("[ENRICHMENT] SMILES chunk exception: %s", str(e))
                        for ident in chunk:
                            try:
                                res = self.pubchem.fetch(ident, identifier_type="smiles", properties=api_properties)
                                smiles_results[ident] = res
                            except Exception as inner_e:
                                from backend.api_clients.base_plugin import PluginResult
                                smiles_results[ident] = PluginResult(
                                    success=False, data={},
                                    error=f"FETCH_FAILED: {str(inner_e)}"
                                )

                    processed_count += len(chunk)
                    if progress_callback:
                        progress_callback(processed_count, total_unique)

        # ── Fetch Names (individual GET — per-compound progress) ────────
        # PubChem PUG REST does NOT support batch POST for name lookups,
        # so each name is fetched individually. We update the progress
        # callback after EVERY compound for real-time ETA display.
        name_results: dict = {}
        if unique_names:
            logger.info("[ENRICHMENT] Fetching %d unique names (individual GET)...", len(unique_names))
            for ident in unique_names:
                try:
                    res = self.pubchem.fetch(ident, identifier_type="name", properties=api_properties)
                    name_results[ident] = res
                except Exception as e:
                    from backend.api_clients.base_plugin import PluginResult
                    name_results[ident] = PluginResult(
                        success=False, data={},
                        error=f"FETCH_FAILED: {str(e)}"
                    )

                processed_count += 1
                if progress_callback:
                    progress_callback(processed_count, total_unique)

            successes = sum(1 for r in name_results.values() if r.success)
            failures = len(name_results) - successes
            logger.info("[ENRICHMENT] Names done: %d/%d succeeded, %d failed",
                        successes, len(name_results), failures)

        # Log aggregate fetch results
        smiles_ok = sum(1 for r in smiles_results.values() if r.success) if smiles_results else 0
        names_ok = sum(1 for r in name_results.values() if r.success) if name_results else 0
        logger.info("[ENRICHMENT] Fetch complete: SMILES %d/%d ok, Names %d/%d ok",
                    smiles_ok, len(smiles_results), names_ok, len(name_results))

        # ── QSAR safety column reference ────────────────────────────────
        val_col = self._find_column_by_mapping(mappings, 'value')
        qsar_col = f"{val_col}_qsar_ready" if val_col else None

        # ── Row-level overlay ───────────────────────────────────────────
        _populated_count = 0
        _failed_count = 0
        _missing_identity_count = 0

        for idx, row in enriched_df.iterrows():
            identifier = None
            id_type = None
            result = None

            if smiles_col and pd.notna(row.get(smiles_col)) and str(row.get(smiles_col, "")).strip():
                identifier = str(row[smiles_col]).strip()
                id_type = "smiles"
                result = smiles_results.get(identifier)
            elif name_col and pd.notna(row.get(name_col)) and str(row.get(name_col, "")).strip():
                identifier = str(row[name_col]).strip()
                id_type = "name"
                result = name_results.get(identifier)

            if not identifier:
                enriched_df.at[idx, 'PubChem_Error'] = "MISSING_IDENTITY"
                _missing_identity_count += 1
                continue

            if not result:
                enriched_df.at[idx, 'PubChem_Error'] = "FETCH_FAILED"
                _failed_count += 1
                continue

            # Ambiguity handling
            if result.ambiguous:
                enriched_df.at[idx, 'PubChem_Error'] = "AMBIGUOUS_IDENTITY"
                audit_logs.append({
                    "row": idx,
                    "issue": "Ambiguous Identity",
                    "details": f"Searched '{identifier}' ({id_type}) - {len(result.candidate_ids)} candidates."
                })
                _failed_count += 1
                continue

            if not result.success:
                # Use the error label from the API (NOT_FOUND, TIMEOUT, etc.)
                enriched_df.at[idx, 'PubChem_Error'] = result.error or "FETCH_FAILED"
                _failed_count += 1
                continue

            # Map API response -> user-selected columns
            # All values are cast to str to prevent dtype conflicts
            data = result.data
            for desc_name in selected_descriptors:
                api_key = _DESC_TO_API.get(desc_name)
                if desc_name == "PubChem_CID":
                    enriched_df.at[idx, desc_name] = str(data.get('CID', ''))
                elif api_key and api_key in data:
                    enriched_df.at[idx, desc_name] = str(data[api_key])
                elif api_key:
                    # Safe SMILES fallback: CanonicalSMILES <-> IsomericSMILES
                    if api_key == 'CanonicalSMILES':
                        enriched_df.at[idx, desc_name] = str(data.get('IsomericSMILES', ''))
                    elif api_key == 'IsomericSMILES':
                        enriched_df.at[idx, desc_name] = str(data.get('CanonicalSMILES', ''))

            _populated_count += 1

            # MW safety catch
            pub_mw_str = data.get('MolecularWeight', '')
            pub_mw = None
            if pub_mw_str:
                try:
                    pub_mw = float(pub_mw_str)
                except ValueError:
                    pass

            if pub_mw is None and qsar_col and qsar_col in enriched_df.columns:
                enriched_df.at[idx, qsar_col] = False

            # MW discrepancy audit
            if orig_mw_col and pd.notna(row.get(orig_mw_col)) and pub_mw is not None:
                try:
                    orig_mw = float(row[orig_mw_col])
                    diff_pct = abs(orig_mw - pub_mw) / pub_mw * 100
                    if diff_pct > 1.0:
                        audit_logs.append({
                            "row": idx,
                            "issue": "Data Discrepancy",
                            "details": f"Row {idx}: Original MW ({orig_mw}) vs PubChem MW ({pub_mw}) diff >{diff_pct:.2f}%"
                        })
                except ValueError:
                    pass

        # ── Pre-export validation & diagnostics ─────────────────────────
        logger.info("[ENRICHMENT] === PRE-EXPORT VALIDATION ===")
        logger.info("[ENRICHMENT]   Total rows:          %d", len(enriched_df))
        logger.info("[ENRICHMENT]   Populated:           %d", _populated_count)
        logger.info("[ENRICHMENT]   Failed:              %d", _failed_count)
        logger.info("[ENRICHMENT]   Missing identity:    %d", _missing_identity_count)

        for desc_name in selected_descriptors:
            if desc_name in enriched_df.columns:
                non_empty = enriched_df[desc_name].notna() & (enriched_df[desc_name].astype(str).str.strip() != '') & (enriched_df[desc_name].astype(str) != 'None')
                pct = non_empty.sum() / len(enriched_df) * 100 if len(enriched_df) > 0 else 0
                logger.info("[ENRICHMENT]   %s: %d/%d populated (%.1f%%)",
                            desc_name, non_empty.sum(), len(enriched_df), pct)

        # Log sample rows for visual verification
        if _populated_count > 0:
            sample_cols = [c for c in selected_descriptors if c in enriched_df.columns]
            if sample_cols:
                sample = enriched_df.loc[enriched_df[sample_cols[0]].notna() & (enriched_df[sample_cols[0]].astype(str).str.strip() != '') & (enriched_df[sample_cols[0]].astype(str) != 'None'), sample_cols].head(3)
                logger.info("[ENRICHMENT] Sample enriched rows:\n%s", sample.to_string())

        return enriched_df, audit_logs

    # ═══════════════════════════════════════════════════════════════════
    # ChEMBL Enrichment
    # ═══════════════════════════════════════════════════════════════════
    
    def enrich_chembl(self, df: pd.DataFrame, mappings: Dict[str, str],
                      progress_callback=None) -> Tuple[pd.DataFrame, List[dict]]:
        """
        Enrich dataframe with ChEMBL molecular data.
        Uses InChIKey from PubChem enrichment if available, otherwise compound name.
        """
        enriched_df = df.copy()
        audit_logs = []
        
        name_col = self._find_column_by_mapping(mappings, 'chemical_id')
        
        # Initialize ChEMBL columns
        chembl_cols = [
            'ChEMBL_ID', 'ChEMBL_Name', 'ChEMBL_Type', 'ChEMBL_MaxPhase',
            'ChEMBL_MW', 'ChEMBL_ALogP', 'ChEMBL_HBA', 'ChEMBL_HBD',
            'ChEMBL_PSA', 'ChEMBL_RO5', 'ChEMBL_AromaticRings', 'ChEMBL_HeavyAtoms',
        ]
        for col in chembl_cols:
            enriched_df[col] = ""
        
        # Determine identifiers to search — prefer InChIKey, fallback to name
        identifiers = []
        id_types = []
        
        inchikey_col = 'PubChem_InChIKey' if 'PubChem_InChIKey' in enriched_df.columns else None
        
        for idx, row in enriched_df.iterrows():
            ident = None
            id_type = None
            
            if inchikey_col and pd.notna(row[inchikey_col]) and str(row[inchikey_col]).strip():
                ident = str(row[inchikey_col]).strip()
                id_type = 'inchi_key'
            elif name_col and name_col in enriched_df.columns and pd.notna(row[name_col]):
                ident = str(row[name_col]).strip()
                id_type = 'name'
            
            identifiers.append(ident)
            id_types.append(id_type)
        
        # Deduplicate for unique lookups
        unique_lookups = {}
        for ident, id_type in zip(identifiers, id_types):
            if ident and id_type and ident not in unique_lookups:
                unique_lookups[ident] = id_type
        
        total = len(unique_lookups)
        results_cache = {}
        
        for i, (ident, id_type) in enumerate(unique_lookups.items()):
            result = self.chembl.fetch(ident, identifier_type=id_type)
            results_cache[ident] = result
            if progress_callback:
                progress_callback(i + 1, total)
        
        # Overlay results
        for idx in range(len(enriched_df)):
            ident = identifiers[idx]
            if ident and ident in results_cache:
                result = results_cache[ident]
                if result.success:
                    for key, val in result.data.items():
                        if key in chembl_cols:
                            enriched_df.at[idx, key] = str(val) if val else ""
                elif result.ambiguous:
                    audit_logs.append({
                        'row': idx, 'issue': 'ChEMBL Ambiguous',
                        'details': f"Multiple ChEMBL matches for '{ident}': {result.candidate_ids}"
                    })
        
        return enriched_df, audit_logs

    # ═══════════════════════════════════════════════════════════════════
    # UniProt Enrichment
    # ═══════════════════════════════════════════════════════════════════
    
    def enrich_uniprot(self, df: pd.DataFrame, mappings: Dict[str, str],
                       progress_callback=None) -> Tuple[pd.DataFrame, List[dict]]:
        """
        Enrich dataframe with UniProt protein/metabolite metadata.
        Searches by compound name or gene symbol.
        """
        enriched_df = df.copy()
        audit_logs = []
        
        name_col = self._find_column_by_mapping(mappings, 'chemical_id')
        
        # Initialize UniProt columns
        uniprot_cols = [
            'UniProt_Accession', 'UniProt_ProteinName', 'UniProt_Gene',
            'UniProt_Organism', 'UniProt_EC', 'UniProt_Function',
        ]
        for col in uniprot_cols:
            enriched_df[col] = ""
        
        if not name_col or name_col not in enriched_df.columns:
            return enriched_df, audit_logs
        
        # Get unique compound names
        unique_names = enriched_df[name_col].dropna().astype(str).str.strip().unique().tolist()
        unique_names = [n for n in unique_names if n]
        
        total = len(unique_names)
        results_cache = {}
        
        for i, name in enumerate(unique_names):
            result = self.uniprot.fetch(name, identifier_type='name')
            results_cache[name] = result
            if progress_callback:
                progress_callback(i + 1, total)
        
        # Overlay results
        for idx, row in enriched_df.iterrows():
            if name_col and pd.notna(row[name_col]):
                name = str(row[name_col]).strip()
                if name in results_cache:
                    result = results_cache[name]
                    if result.success:
                        for key, val in result.data.items():
                            if key in uniprot_cols:
                                enriched_df.at[idx, key] = str(val) if val else ""
                        if result.ambiguous:
                            audit_logs.append({
                                'row': idx, 'issue': 'UniProt Ambiguous',
                                'details': f"Multiple UniProt entries for '{name}': {result.candidate_ids}"
                            })
        
        return enriched_df, audit_logs
