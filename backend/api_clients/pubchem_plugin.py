import requests
import logging
from urllib.parse import quote
from typing import Optional, List, Dict
from backend.api_clients.base_plugin import BaseAPIPlugin, PluginResult

logger = logging.getLogger("sdo.pubchem")

class PubChemPlugin(BaseAPIPlugin):
    """Plugin for PubChem API integration."""
    
    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    # PubChem PUG REST returns different JSON keys than what we request.
    # This map normalizes the response keys back to the canonical names
    # used throughout the codebase.
    _RESPONSE_KEY_ALIASES = {
        'SMILES':             'CanonicalSMILES',
        'ConnectivitySMILES': 'IsomericSMILES',
    }

    # PubChem PUG REST batch POST only works for these identifier types.
    # 'name' lookups MUST use individual GET requests.
    _BATCH_SUPPORTED_TYPES = frozenset({'smiles', 'cid', 'inchikey'})

    @classmethod
    def _normalize_response_keys(cls, data: dict) -> dict:
        """Map PubChem response key aliases to canonical property names."""
        for api_alias, canonical_name in cls._RESPONSE_KEY_ALIASES.items():
            if api_alias in data and canonical_name not in data:
                data[canonical_name] = data[api_alias]
        return data
    
    def fetch(self, identifier: str, 
              identifier_type: str = "name",
              properties: list = None,
              **kwargs) -> PluginResult:
        """
        Fetch compound data from PubChem.
        identifier_type can be 'name', 'smiles', 'cid'.
        """
        if not identifier:
            return PluginResult(success=False, data={}, error="FETCH_FAILED: Empty identifier")
            
        # Check cache first
        cached = self._get_cached(identifier, identifier_type, properties)
        if cached:
            logger.debug("Cache hit for %s:%s", identifier_type, identifier[:40])
            return cached
            
        if properties is None:
            properties = ['MolecularWeight', 'MolecularFormula', 'CanonicalSMILES', 
                         'InChI', 'InChIKey', 'IUPACName']
        
        try:
            self._respect_rate_limit()
            
            # URL Encode the identifier, especially critical for SMILES which contains special chars
            encoded_id = quote(str(identifier).strip(), safe='')
            props_str = ','.join(properties)
            
            url = f"{self.BASE_URL}/compound/{identifier_type}/{encoded_id}/property/{props_str}/JSON"
            logger.debug("GET %s", url)
            
            response = requests.get(url, timeout=30)
            logger.debug("Response %d for %s:%s", response.status_code, identifier_type, identifier[:40])
            
            if response.status_code == 404:
                result = PluginResult(success=False, data={}, error="NOT_FOUND")
                self._cache_result(identifier, identifier_type, result, properties)
                return result
                
            response.raise_for_status()
            data = response.json()
            
            if 'PropertyTable' in data and 'Properties' in data['PropertyTable']:
                properties_list = data['PropertyTable']['Properties']
                
                # Check for Ambiguity
                if len(properties_list) > 1:
                    candidate_cids = [str(p.get('CID', '')) for p in properties_list if 'CID' in p]
                    result = PluginResult(
                        success=False, 
                        data={}, 
                        error="AMBIGUOUS_IDENTITY",
                        ambiguous=True,
                        candidate_ids=candidate_cids
                    )
                    self._cache_result(identifier, identifier_type, result, properties)
                    return result
                
                # Success - Exactly one match
                result_data = self._normalize_response_keys(properties_list[0])
                
                # ── SMILES safe fallback ──────────────────────────────
                # Ensure CanonicalSMILES and IsomericSMILES cross-populate
                # so that downstream consumers never encounter empty SMILES.
                canonical = result_data.get('CanonicalSMILES', '')
                isomeric  = result_data.get('IsomericSMILES', '')
                if not canonical and isomeric:
                    result_data['CanonicalSMILES'] = isomeric
                elif not isomeric and canonical:
                    result_data['IsomericSMILES'] = canonical
                
                logger.debug("SUCCESS %s:%s -> CID=%s", identifier_type, identifier[:40], result_data.get('CID'))
                
                result = PluginResult(
                    success=True,
                    data=result_data
                )
                self._cache_result(identifier, identifier_type, result, properties)
                return result
            else:
                return PluginResult(success=False, data={}, error="FETCH_FAILED: Invalid response format")
                
        except requests.exceptions.Timeout:
            logger.warning("TIMEOUT for %s:%s", identifier_type, identifier[:40])
            return PluginResult(success=False, data={}, error="TIMEOUT")
        except requests.exceptions.ConnectionError:
            logger.warning("CONNECTION_ERROR for %s:%s", identifier_type, identifier[:40])
            return PluginResult(success=False, data={}, error="CONNECTION_ERROR")
        except requests.exceptions.RequestException as e:
            logger.warning("API Error for %s:%s: %s", identifier_type, identifier[:40], str(e))
            return PluginResult(success=False, data={}, error=f"FETCH_FAILED: {str(e)}")
        except Exception as e:
            logger.error("Unexpected error for %s:%s: %s", identifier_type, identifier[:40], str(e))
            return PluginResult(success=False, data={}, error=f"FETCH_FAILED: {str(e)}")

    def fetch_batch(self, identifiers: List[str], identifier_type: str = "smiles", properties: list = None) -> Dict[str, PluginResult]:
        """
        Fetch compound data from PubChem in bulk using POST.
        Returns a dictionary mapping the original identifier to its PluginResult.
        
        IMPORTANT: PubChem PUG REST batch POST only supports 'smiles' and 'cid'
        identifier types. For 'name' lookups, this method automatically falls back
        to individual GET requests via fetch().
        """
        results = {}
        if not identifiers:
            return results
            
        # Filter out already cached items
        to_fetch = []
        for ident in identifiers:
            cached = self._get_cached(ident, identifier_type, properties)
            if cached:
                results[ident] = cached
            else:
                to_fetch.append(ident)
                
        if not to_fetch:
            return results
            
        if properties is None:
            properties = ['MolecularWeight', 'MolecularFormula', 'CanonicalSMILES', 'InChIKey', 'IUPACName']

        # ── CRITICAL FIX ────────────────────────────────────────────
        # PubChem PUG REST batch POST endpoint only works for 'smiles'
        # and 'cid' identifier types. For 'name', it returns 404.
        # Fall back to individual fetch() for unsupported batch types.
        # ────────────────────────────────────────────────────────────
        if identifier_type not in self._BATCH_SUPPORTED_TYPES:
            logger.info(
                "Batch POST not supported for '%s' — falling back to %d individual GET requests",
                identifier_type, len(to_fetch),
            )
            for ident in to_fetch:
                res = self.fetch(ident, identifier_type, properties)
                results[ident] = res
            return results
            
        try:
            self._respect_rate_limit()
            props_str = ','.join(properties)
            url = f"{self.BASE_URL}/compound/{identifier_type}/property/{props_str}/JSON"
            
            # PubChem PUG REST POST data
            data = {identifier_type: "\n".join(to_fetch)}
            logger.debug("Batch POST %s (%d identifiers)", url, len(to_fetch))
            response = requests.post(url, data=data, timeout=60)
            
            if response.status_code == 404:
                # Batch returned 404 — fall back to individual fetch for each
                # to avoid poisoning the cache with blanket "Not Found" errors.
                logger.warning(
                    "Batch POST returned 404 for %s — falling back to individual fetch (%d items)",
                    identifier_type, len(to_fetch),
                )
                for ident in to_fetch:
                    res = self.fetch(ident, identifier_type, properties)
                    results[ident] = res
                return results
                
            response.raise_for_status()
            data_json = response.json()
            
            if 'PropertyTable' in data_json and 'Properties' in data_json['PropertyTable']:
                properties_list = data_json['PropertyTable']['Properties']
                
                if len(properties_list) == len(to_fetch):
                    for i, ident in enumerate(to_fetch):
                        prop_data = self._normalize_response_keys(properties_list[i])
                        # ── SMILES safe fallback (batch) ─────────────
                        canonical = prop_data.get('CanonicalSMILES', '')
                        isomeric  = prop_data.get('IsomericSMILES', '')
                        if not canonical and isomeric:
                            prop_data['CanonicalSMILES'] = isomeric
                        elif not isomeric and canonical:
                            prop_data['IsomericSMILES'] = canonical
                        res = PluginResult(success=True, data=prop_data)
                        self._cache_result(ident, identifier_type, res, properties)
                        results[ident] = res
                else:
                    # Length mismatch! Some were invalid. Fallback to individual fetch.
                    logger.warning(
                        "Batch response length mismatch (got %d, expected %d) — falling back",
                        len(properties_list), len(to_fetch),
                    )
                    for ident in to_fetch:
                        res = self.fetch(ident, identifier_type, properties)
                        results[ident] = res
                        
            else:
                # Invalid response format — fall back to individual
                logger.warning("Batch response missing PropertyTable — falling back to individual")
                for ident in to_fetch:
                    res = self.fetch(ident, identifier_type, properties)
                    results[ident] = res
                    
        except Exception as e:
            # On bulk error, fallback to individual fetching
            logger.error("Batch exception: %s — falling back to individual", str(e))
            for ident in to_fetch:
                res = self.fetch(ident, identifier_type, properties)
                results[ident] = res
                
        return results

    def purge_failed_cache_entries(self) -> int:
        """
        Remove all cached entries where success=False.
        
        This is used to clean a poisoned cache (e.g. from the batch POST bug
        that cached every name-based lookup as 'Not Found').
        
        Returns the number of entries purged.
        """
        if not self.cache_enabled:
            return 0
            
        keys_to_remove = [
            k for k, v in self._memory_cache.items()
            if not v.get('success', False)
        ]
        
        for k in keys_to_remove:
            del self._memory_cache[k]
        
        if keys_to_remove:
            self._save_local_cache()
            
        return len(keys_to_remove)

