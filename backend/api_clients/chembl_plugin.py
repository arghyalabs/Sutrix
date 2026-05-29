"""
ChEMBL API Plugin for the Scientific Data Orchestrator.

Provides access to the ChEMBL database for:
- Compound bioactivity data (IC50, Ki, EC50)
- Target information and mechanism of action
- Molecular property enrichment
- ADMET predictions

API Docs: https://www.ebi.ac.uk/chembl/api/data/docs
"""
import requests
from urllib.parse import quote
from typing import Optional, List, Dict, Any
from backend.api_clients.base_plugin import BaseAPIPlugin, PluginResult


class ChEMBLPlugin(BaseAPIPlugin):
    """Plugin for ChEMBL API integration."""
    
    BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
    
    def __init__(self, cache_enabled: bool = True, rate_limit_delay: float = 0.3):
        super().__init__(cache_enabled=cache_enabled, rate_limit_delay=rate_limit_delay)
    
    def fetch(self, identifier: str,
              identifier_type: str = "name",
              **kwargs) -> PluginResult:
        """
        Fetch compound data from ChEMBL.
        
        identifier_type can be:
            'name'    — search by compound name
            'smiles'  — search by SMILES structure
            'chembl_id' — direct lookup by ChEMBL ID (e.g. CHEMBL25)
            'inchi_key' — search by InChIKey
        """
        if not identifier:
            return PluginResult(success=False, data={}, error="Empty identifier")
        
        cached = self._get_cached(identifier, identifier_type)
        if cached:
            return cached
        
        try:
            self._respect_rate_limit()
            
            if identifier_type == "chembl_id":
                result = self._fetch_by_chembl_id(identifier)
            elif identifier_type == "smiles":
                result = self._search_by_smiles(identifier)
            elif identifier_type == "inchi_key":
                result = self._search_by_inchi_key(identifier)
            else:
                result = self._search_by_name(identifier)
            
            self._cache_result(identifier, identifier_type, result)
            return result
            
        except requests.exceptions.Timeout:
            return PluginResult(success=False, data={}, error="ChEMBL API Timeout")
        except requests.exceptions.ConnectionError:
            return PluginResult(success=False, data={}, error="ChEMBL API Connection Error")
        except Exception as e:
            return PluginResult(success=False, data={}, error=f"ChEMBL Error: {str(e)}")
    
    def _search_by_name(self, name: str) -> PluginResult:
        """Search ChEMBL by compound name."""
        encoded = quote(name.strip(), safe='')
        url = f"{self.BASE_URL}/molecule/search.json?q={encoded}&limit=5"
        
        resp = requests.get(url, timeout=30)
        if resp.status_code == 404:
            return PluginResult(success=False, data={}, error="Not Found in ChEMBL")
        resp.raise_for_status()
        
        data = resp.json()
        molecules = data.get('molecules', [])
        
        if not molecules:
            return PluginResult(success=False, data={}, error="No ChEMBL match found")
        
        if len(molecules) > 1:
            candidate_ids = [m.get('molecule_chembl_id', '') for m in molecules[:5]]
            return PluginResult(
                success=False, data={},
                error="Ambiguous ChEMBL Identity",
                ambiguous=True,
                candidate_ids=candidate_ids
            )
        
        return self._extract_molecule_data(molecules[0])
    
    def _fetch_by_chembl_id(self, chembl_id: str) -> PluginResult:
        """Direct lookup by ChEMBL ID."""
        url = f"{self.BASE_URL}/molecule/{chembl_id}.json"
        
        resp = requests.get(url, timeout=30)
        if resp.status_code == 404:
            return PluginResult(success=False, data={}, error=f"ChEMBL ID {chembl_id} not found")
        resp.raise_for_status()
        
        mol = resp.json()
        return self._extract_molecule_data(mol)
    
    def _search_by_smiles(self, smiles: str) -> PluginResult:
        """Search by SMILES string using structure search."""
        url = f"{self.BASE_URL}/molecule.json"
        params = {
            'molecule_structures__canonical_smiles': smiles.strip(),
            'limit': 3,
        }
        
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 404:
            return PluginResult(success=False, data={}, error="SMILES not found in ChEMBL")
        resp.raise_for_status()
        
        data = resp.json()
        molecules = data.get('molecules', [])
        
        if not molecules:
            return PluginResult(success=False, data={}, error="No ChEMBL match for SMILES")
        
        return self._extract_molecule_data(molecules[0])
    
    def _search_by_inchi_key(self, inchi_key: str) -> PluginResult:
        """Search by InChIKey."""
        url = f"{self.BASE_URL}/molecule.json"
        params = {
            'molecule_structures__standard_inchi_key': inchi_key.strip(),
            'limit': 3,
        }
        
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 404:
            return PluginResult(success=False, data={}, error="InChIKey not found in ChEMBL")
        resp.raise_for_status()
        
        data = resp.json()
        molecules = data.get('molecules', [])
        
        if not molecules:
            return PluginResult(success=False, data={}, error="No ChEMBL match for InChIKey")
        
        return self._extract_molecule_data(molecules[0])
    
    def _extract_molecule_data(self, mol: dict) -> PluginResult:
        """Extract standardized data from a ChEMBL molecule record."""
        props = mol.get('molecule_properties') or {}
        structs = mol.get('molecule_structures') or {}
        
        result_data = {
            'ChEMBL_ID': mol.get('molecule_chembl_id', ''),
            'ChEMBL_Name': mol.get('pref_name', ''),
            'ChEMBL_Type': mol.get('molecule_type', ''),
            'ChEMBL_MaxPhase': mol.get('max_phase', ''),
            'ChEMBL_MW': props.get('full_mwt', ''),
            'ChEMBL_ALogP': props.get('alogp', ''),
            'ChEMBL_HBA': props.get('hba', ''),
            'ChEMBL_HBD': props.get('hbd', ''),
            'ChEMBL_PSA': props.get('psa', ''),
            'ChEMBL_RO5': props.get('num_ro5_violations', ''),
            'ChEMBL_AromaticRings': props.get('aromatic_rings', ''),
            'ChEMBL_HeavyAtoms': props.get('heavy_atoms', ''),
            'ChEMBL_CanonicalSMILES': structs.get('canonical_smiles', ''),
            'ChEMBL_InChIKey': structs.get('standard_inchi_key', ''),
        }
        
        return PluginResult(success=True, data=result_data)
    
    def fetch_bioactivities(self, chembl_id: str, limit: int = 50) -> List[dict]:
        """
        Fetch bioactivity data for a given ChEMBL compound ID.
        Returns a list of activity records.
        """
        try:
            self._respect_rate_limit()
            url = f"{self.BASE_URL}/activity.json"
            params = {
                'molecule_chembl_id': chembl_id,
                'limit': limit,
            }
            
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            activities = data.get('activities', [])
            
            return [
                {
                    'target_name': a.get('target_pref_name', ''),
                    'target_chembl_id': a.get('target_chembl_id', ''),
                    'activity_type': a.get('standard_type', ''),
                    'activity_value': a.get('standard_value', ''),
                    'activity_units': a.get('standard_units', ''),
                    'activity_relation': a.get('standard_relation', ''),
                    'assay_type': a.get('assay_type', ''),
                }
                for a in activities
            ]
            
        except Exception:
            return []
