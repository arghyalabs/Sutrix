"""
UniProt API Plugin for the Scientific Data Orchestrator.

Provides access to the UniProt knowledge base for:
- Protein identification and metadata
- Gene name resolution
- Organism/taxonomy information
- Functional annotations (GO terms, EC numbers)
- Metabolite associations via cross-references

API Docs: https://www.uniprot.org/help/api
"""
import requests
from urllib.parse import quote
from typing import Optional, List, Dict, Any
from backend.api_clients.base_plugin import BaseAPIPlugin, PluginResult


class UniProtPlugin(BaseAPIPlugin):
    """Plugin for UniProt API integration (proteins and metabolites)."""
    
    BASE_URL = "https://rest.uniprot.org"
    
    def __init__(self, cache_enabled: bool = True, rate_limit_delay: float = 0.5):
        super().__init__(cache_enabled=cache_enabled, rate_limit_delay=rate_limit_delay)
    
    def fetch(self, identifier: str,
              identifier_type: str = "name",
              **kwargs) -> PluginResult:
        """
        Fetch protein/metabolite data from UniProt.
        
        identifier_type can be:
            'name'        - search by protein/gene name
            'accession'   - direct lookup by UniProt accession (e.g. P12345)
            'gene'        - search by gene symbol
            'organism'    - search proteins by organism name (returns summary)
        """
        if not identifier:
            return PluginResult(success=False, data={}, error="Empty identifier")
        
        cached = self._get_cached(identifier, identifier_type)
        if cached:
            return cached
        
        try:
            self._respect_rate_limit()
            
            if identifier_type == "accession":
                result = self._fetch_by_accession(identifier)
            elif identifier_type == "gene":
                result = self._search_by_gene(identifier)
            else:
                result = self._search_by_name(identifier)
            
            self._cache_result(identifier, identifier_type, result)
            return result
            
        except requests.exceptions.Timeout:
            return PluginResult(success=False, data={}, error="UniProt API Timeout")
        except requests.exceptions.ConnectionError:
            return PluginResult(success=False, data={}, error="UniProt API Connection Error")
        except Exception as e:
            return PluginResult(success=False, data={}, error=f"UniProt Error: {str(e)}")
    
    def _fetch_by_accession(self, accession: str) -> PluginResult:
        """Direct lookup by UniProt accession ID."""
        url = f"{self.BASE_URL}/uniprotkb/{accession.strip()}.json"
        
        resp = requests.get(url, timeout=30)
        if resp.status_code == 404:
            return PluginResult(success=False, data={}, error=f"Accession {accession} not found")
        resp.raise_for_status()
        
        entry = resp.json()
        return self._extract_protein_data(entry)
    
    def _search_by_name(self, name: str) -> PluginResult:
        """Search UniProt by protein name."""
        encoded = quote(name.strip(), safe='')
        url = f"{self.BASE_URL}/uniprotkb/search"
        params = {
            'query': f'(protein_name:"{encoded}") AND (reviewed:true)',
            'format': 'json',
            'size': 5,
            'fields': 'accession,protein_name,gene_names,organism_name,organism_id,ec,go,cc_function,sequence',
        }
        
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        
        data = resp.json()
        results = data.get('results', [])
        
        if not results:
            # Try broader search without reviewed filter
            params['query'] = f'(protein_name:"{encoded}")'
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            results = data.get('results', [])
        
        if not results:
            return PluginResult(success=False, data={}, error="No UniProt match found")
        
        if len(results) > 1:
            candidate_ids = [r.get('primaryAccession', '') for r in results[:5]]
            # Return the best (first) result with ambiguity flag
            result = self._extract_protein_data(results[0])
            result.ambiguous = True
            result.candidate_ids = candidate_ids
            return result
        
        return self._extract_protein_data(results[0])
    
    def _search_by_gene(self, gene_symbol: str) -> PluginResult:
        """Search by gene symbol."""
        encoded = quote(gene_symbol.strip(), safe='')
        url = f"{self.BASE_URL}/uniprotkb/search"
        params = {
            'query': f'(gene:{encoded}) AND (reviewed:true)',
            'format': 'json',
            'size': 5,
            'fields': 'accession,protein_name,gene_names,organism_name,organism_id,ec,go,cc_function,sequence',
        }
        
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        
        data = resp.json()
        results = data.get('results', [])
        
        if not results:
            return PluginResult(success=False, data={}, error=f"No UniProt entry for gene '{gene_symbol}'")
        
        if len(results) > 1:
            candidate_ids = [r.get('primaryAccession', '') for r in results[:5]]
            result = self._extract_protein_data(results[0])
            result.ambiguous = True
            result.candidate_ids = candidate_ids
            return result
        
        return self._extract_protein_data(results[0])
    
    def _extract_protein_data(self, entry: dict) -> PluginResult:
        """Extract standardized data from a UniProt entry."""
        # Primary accession
        accession = entry.get('primaryAccession', '')
        
        # Protein name
        protein_desc = entry.get('proteinDescription', {})
        rec_name = protein_desc.get('recommendedName', {})
        full_name = rec_name.get('fullName', {}).get('value', '')
        if not full_name:
            # Try submittedName
            sub_names = protein_desc.get('submissionNames', [])
            if sub_names:
                full_name = sub_names[0].get('fullName', {}).get('value', '')
        
        # Gene names
        gene_list = entry.get('genes', [])
        primary_gene = ''
        if gene_list:
            gene_names = gene_list[0].get('geneName', {})
            primary_gene = gene_names.get('value', '')
        
        # Organism
        organism = entry.get('organism', {})
        organism_name = organism.get('scientificName', '')
        organism_id = organism.get('taxonId', '')
        
        # EC numbers (enzyme classification)
        ec_numbers = []
        if rec_name.get('ecNumbers'):
            ec_numbers = [ec.get('value', '') for ec in rec_name['ecNumbers']]
        
        # GO annotations
        go_terms = []
        xrefs = entry.get('uniProtKBCrossReferences', [])
        for xref in xrefs:
            if xref.get('database') == 'GO':
                props = {p.get('key', ''): p.get('value', '') for p in xref.get('properties', [])}
                go_terms.append({
                    'id': xref.get('id', ''),
                    'term': props.get('GoTerm', ''),
                    'source': props.get('GoEvidenceType', ''),
                })
        
        # Function description
        function_text = ''
        comments = entry.get('comments', [])
        for comment in comments:
            if comment.get('commentType') == 'FUNCTION':
                texts = comment.get('texts', [])
                if texts:
                    function_text = texts[0].get('value', '')
                break
        
        # Sequence length
        sequence = entry.get('sequence', {})
        seq_length = sequence.get('length', 0)
        seq_mass = sequence.get('molWeight', 0)
        
        result_data = {
            'UniProt_Accession': accession,
            'UniProt_ProteinName': full_name,
            'UniProt_Gene': primary_gene,
            'UniProt_Organism': organism_name,
            'UniProt_TaxonID': str(organism_id),
            'UniProt_EC': '; '.join(ec_numbers) if ec_numbers else '',
            'UniProt_Function': function_text[:500] if function_text else '',
            'UniProt_SeqLength': str(seq_length),
            'UniProt_MolWeight': str(seq_mass),
            'UniProt_GO_Count': str(len(go_terms)),
        }
        
        return PluginResult(success=True, data=result_data)
    
    def fetch_protein_targets(self, gene_or_name: str, organism: str = "Homo sapiens") -> List[dict]:
        """
        Fetch protein targets associated with a compound name or gene.
        Useful for linking toxicological compounds to their biological targets.
        """
        try:
            self._respect_rate_limit()
            encoded = quote(gene_or_name.strip(), safe='')
            url = f"{self.BASE_URL}/uniprotkb/search"
            params = {
                'query': f'({encoded}) AND (organism_name:"{organism}") AND (reviewed:true)',
                'format': 'json',
                'size': 10,
                'fields': 'accession,protein_name,gene_names,organism_name',
            }
            
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            results = data.get('results', [])
            
            targets = []
            for r in results:
                protein_desc = r.get('proteinDescription', {})
                rec_name = protein_desc.get('recommendedName', {})
                full_name = rec_name.get('fullName', {}).get('value', '')
                
                gene_list = r.get('genes', [])
                gene = gene_list[0].get('geneName', {}).get('value', '') if gene_list else ''
                
                targets.append({
                    'accession': r.get('primaryAccession', ''),
                    'protein_name': full_name,
                    'gene': gene,
                    'organism': r.get('organism', {}).get('scientificName', ''),
                })
            
            return targets
            
        except Exception:
            return []
