import aiohttp
import asyncio
from typing import Dict, Any
from urllib.parse import quote
from .base_client import BaseAsyncClient

class AsyncPubChemClient(BaseAsyncClient):
    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    async def fetch(self, identifier: str, identifier_type: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Fetch compound data from PubChem asynchronously."""
        encoded_id = quote(str(identifier).strip(), safe='')
        props = "MolecularWeight,MolecularFormula,CanonicalSMILES,IsomericSMILES,InChIKey,IUPACName,XLogP,TPSA,HBondDonorCount,HBondAcceptorCount"
        url = f"{self.BASE_URL}/compound/{identifier_type}/{encoded_id}/property/{props}/JSON"
        
        retries = 3
        async with self._semaphore:
            for attempt in range(retries):
                try:
                    # Add delay for rate limiting if requested rapidly, simple backoff
                    await asyncio.sleep(1.0 / self.rate_limit_rps)
                    
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status in [429, 502, 503, 504]:
                            await asyncio.sleep(2 ** attempt)
                            continue
                            
                        if response.status == 404:
                            return {"success": False, "error": "NOT_FOUND"}
                        
                        response.raise_for_status()
                        data = await response.json()
                        
                        if 'PropertyTable' in data and 'Properties' in data['PropertyTable']:
                            props_list = data['PropertyTable']['Properties']
                            if len(props_list) > 1:
                                return {"success": False, "error": "AMBIGUOUS_IDENTITY", "ambiguous": True}
                            
                            result_data = props_list[0]
                            
                            # Apply aliases
                            if 'SMILES' in result_data and 'CanonicalSMILES' not in result_data:
                                result_data['CanonicalSMILES'] = result_data['SMILES']
                            if 'ConnectivitySMILES' in result_data and 'IsomericSMILES' not in result_data:
                                result_data['IsomericSMILES'] = result_data['ConnectivitySMILES']
                            
                            # SMILES fallback
                            canonical = result_data.get('CanonicalSMILES', '')
                            isomeric = result_data.get('IsomericSMILES', '')
                            if not canonical and isomeric:
                                result_data['CanonicalSMILES'] = isomeric
                            elif not isomeric and canonical:
                                result_data['IsomericSMILES'] = canonical
                                
                            return {"success": True, "data": result_data}
                        else:
                            return {"success": False, "error": "FETCH_FAILED: Invalid response format"}
                except asyncio.TimeoutError:
                    if attempt == retries - 1:
                        return {"success": False, "error": "TIMEOUT"}
                    await asyncio.sleep(2 ** attempt)
                except Exception as e:
                    if attempt == retries - 1:
                        return {"success": False, "error": f"FETCH_FAILED: {str(e)}"}
                    await asyncio.sleep(2 ** attempt)
                    
            return {"success": False, "error": "MAX_RETRIES_EXCEEDED"}

    async def fetch_batch(self, identifiers: list, identifier_type: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Fetch multiple compounds asynchronously using POST batching with exponential backoff and timeout protection."""
        props = "MolecularWeight,MolecularFormula,CanonicalSMILES,IsomericSMILES,InChIKey,IUPACName,XLogP,TPSA,HBondDonorCount,HBondAcceptorCount"
        url = f"{self.BASE_URL}/compound/{identifier_type}/property/{props}/JSON"
        
        if identifier_type == 'name':
            data = {"name": ",".join(identifiers)}
        elif identifier_type == 'smiles':
            data = {"smiles": ",".join(identifiers)}
        elif identifier_type == 'cid':
            data = {"cid": ",".join([str(i) for i in identifiers])}
        else:
            return {"success": False, "error": "UNSUPPORTED_BATCH_ID_TYPE"}

        retries = 3
        async with self._semaphore:
            for attempt in range(retries):
                try:
                    await asyncio.sleep(1.0 / self.rate_limit_rps)
                    # 60s timeout for batch requests
                    async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=60)) as response:
                        if response.status in [429, 502, 503, 504]:
                            # Rate limited or server overloaded -> Exponential backoff
                            await asyncio.sleep(2 ** attempt)
                            continue
                            
                        if response.status == 404:
                            return {"success": True, "data": []}
                            
                        response.raise_for_status()
                        result_data = await response.json()
                        
                        if 'PropertyTable' in result_data and 'Properties' in result_data['PropertyTable']:
                            properties = result_data['PropertyTable']['Properties']
                            
                            # Clean aliases per record
                            for rec in properties:
                                if 'SMILES' in rec and 'CanonicalSMILES' not in rec:
                                    rec['CanonicalSMILES'] = rec['SMILES']
                                if 'ConnectivitySMILES' in rec and 'IsomericSMILES' not in rec:
                                    rec['IsomericSMILES'] = rec['ConnectivitySMILES']
                                    
                                canonical = rec.get('CanonicalSMILES', '')
                                isomeric = rec.get('IsomericSMILES', '')
                                if not canonical and isomeric:
                                    rec['CanonicalSMILES'] = isomeric
                                elif not isomeric and canonical:
                                    rec['IsomericSMILES'] = canonical
                                    
                            return {"success": True, "data": properties}
                        else:
                            return {"success": False, "error": "INVALID_BATCH_RESPONSE"}
                            
                except asyncio.TimeoutError:
                    if attempt == retries - 1:
                        return {"success": False, "error": "TIMEOUT"}
                    await asyncio.sleep(2 ** attempt)
                except Exception as e:
                    if attempt == retries - 1:
                        return {"success": False, "error": f"BATCH_FETCH_FAILED: {str(e)}"}
                    await asyncio.sleep(2 ** attempt)
                    
            return {"success": False, "error": "MAX_RETRIES_EXCEEDED"}
