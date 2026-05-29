import time
import json
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class PluginResult:
    """Result from an API plugin operation."""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    cached: bool = False
    ambiguous: bool = False
    candidate_ids: List[str] = field(default_factory=list)

class BaseAPIPlugin(ABC):
    """Base class for API plugins with Rate Limiting and Disk Caching."""
    
    def __init__(self, cache_enabled: bool = True, rate_limit_delay: float = 0.2):
        self.cache_enabled = cache_enabled
        self.rate_limit_delay = rate_limit_delay
        self._memory_cache: Dict[str, dict] = {}
        self._last_request_time = 0.0
        
        # Local Disk Cache Setup
        self.cache_dir = Path("outputs/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / f"{self.__class__.__name__.lower()}_cache.json"
        
        if self.cache_enabled:
            self._load_local_cache()
            
    def _load_local_cache(self) -> None:
        """Load the local JSON cache to prevent redundant API hits on restarts."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self._memory_cache = json.load(f)
            except Exception:
                self._memory_cache = {}
                
    def _save_local_cache(self) -> None:
        """Persist memory cache to disk."""
        if self.cache_enabled:
            try:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self._memory_cache, f)
            except Exception:
                pass
    
    def _respect_rate_limit(self) -> None:
        """Ensure rate limiting is strictly respected (e.g. NCBI max 5 requests/sec)."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()
    
    def _get_cache_key(self, identifier: str, identifier_type: str, properties: list = None) -> str:
        """Generate cache key combining type, identifier, and requested properties."""
        base = f"{identifier_type}:{identifier.lower().strip()}"
        if properties:
            props_key = ",".join(sorted(properties))
            return f"{base}|{props_key}"
        return base
    
    def _get_cached(self, identifier: str, identifier_type: str, properties: list = None) -> Optional[PluginResult]:
        """Check memory (which is synced from disk) for a cached result."""
        if not self.cache_enabled:
            return None
        key = self._get_cache_key(identifier, identifier_type, properties)
        if key in self._memory_cache:
            data_dict = self._memory_cache[key]
            # Reconstruct PluginResult
            return PluginResult(
                success=data_dict.get("success", False),
                data=data_dict.get("data", {}),
                error=data_dict.get("error"),
                cached=True,
                ambiguous=data_dict.get("ambiguous", False),
                candidate_ids=data_dict.get("candidate_ids", [])
            )
        return None
    
    def _cache_result(self, identifier: str, identifier_type: str, result: PluginResult, properties: list = None) -> None:
        """Cache result in memory and flush to disk."""
        if self.cache_enabled:
            key = self._get_cache_key(identifier, identifier_type, properties)
            self._memory_cache[key] = {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "ambiguous": result.ambiguous,
                "candidate_ids": result.candidate_ids
            }
            # Immediately save to disk to ensure durability if process crashes
            self._save_local_cache()
    
    @abstractmethod
    def fetch(self, identifier: str, identifier_type: str = "name", **kwargs) -> PluginResult:
        """Fetch compound data from the external API."""
        pass
