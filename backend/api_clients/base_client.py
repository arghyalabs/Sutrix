import abc
import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional
from backend.cache.sqlite_cache import SQLiteCache

logger = logging.getLogger("sdo.backend.api")

class BaseAsyncClient(abc.ABC):
    def __init__(self, cache: SQLiteCache, rate_limit_rps: float = 5.0):
        self.cache = cache
        self.rate_limit_rps = rate_limit_rps
        self._semaphore = asyncio.Semaphore(max(1, int(rate_limit_rps)))
        
    @abc.abstractmethod
    async def fetch(self, identifier: str, identifier_type: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        pass
