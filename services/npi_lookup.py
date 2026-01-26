"""
NPI Lookup Service
NPPES provider auto-fill with local caching.
On NPI entry: fetch provider name, address, taxonomy.
Allow override.
"""

import requests
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path


class NPILookupService:
    """NPI lookup with local caching"""
    
    NPPES_API_URL = "https://npiregistry.cms.hhs.gov/api"
    CACHE_DIR = Path.home() / ".opticlaimai" / "npi_cache"
    CACHE_TTL_DAYS = 30  # Cache for 30 days
    
    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
    
    def lookup_npi(self, npi: str) -> Optional[Dict[str, Any]]:
        """
        Look up NPI and return provider info.
        Checks: memory cache → disk cache → API → None
        """
        if not self._is_valid_npi_format(npi):
            return None
        
        npi = str(npi).strip()
        
        # Check memory cache
        if npi in self._memory_cache:
            cached_data = self._memory_cache[npi]
            if not self._is_cache_expired(cached_data):
                return cached_data.get("data")
        
        # Check disk cache
        cached_data = self._get_disk_cache(npi)
        if cached_data and not self._is_cache_expired(cached_data):
            self._memory_cache[npi] = cached_data
            return cached_data.get("data")
        
        # Query API
        provider_info = self._query_nppes_api(npi)
        if provider_info:
            # Cache result
            cache_entry = {
                "npi": npi,
                "data": provider_info,
                "timestamp": datetime.now().isoformat()
            }
            self._memory_cache[npi] = cache_entry
            self._save_disk_cache(npi, cache_entry)
            return provider_info
        
        return None
    
    def _query_nppes_api(self, npi: str) -> Optional[Dict[str, Any]]:
        """Query NPPES API for NPI info"""
        try:
            response = requests.get(
                f"{self.NPPES_API_URL}",
                params={
                    "number": npi,
                    "version": "2.1"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("results"):
                    result = data["results"][0]
                    return self._parse_nppes_response(result)
        except Exception as e:
            print(f"NPI lookup error: {e}")
        
        return None
    
    def _parse_nppes_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse NPPES API response into canonical format"""
        basic_info = result.get("basic", {})
        address_info = result.get("addresses", [{}])[0] if result.get("addresses") else {}
        taxonomies = result.get("taxonomies", [])
        primary_taxonomy = taxonomies[0] if taxonomies else {}
        
        return {
            "npi": result.get("number"),
            "first_name": basic_info.get("first_name"),
            "last_name": basic_info.get("last_name"),
            "organization_name": basic_info.get("organization_name"),
            "credential": basic_info.get("credential"),
            "address": {
                "street_address": address_info.get("address_1"),
                "city": address_info.get("city"),
                "state": address_info.get("state"),
                "zip_code": address_info.get("postal_code"),
            },
            "phone": address_info.get("telephone_number"),
            "taxonomy_code": primary_taxonomy.get("code"),
            "taxonomy_description": primary_taxonomy.get("desc"),
            "is_org": result.get("enumeration_type") == "Organization",
        }
    
    def _get_disk_cache(self, npi: str) -> Optional[Dict[str, Any]]:
        """Get cached NPI info from disk"""
        cache_file = self.CACHE_DIR / f"{npi}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Cache read error: {e}")
        
        return None
    
    def _save_disk_cache(self, npi: str, data: Dict[str, Any]) -> None:
        """Save NPI info to disk cache"""
        cache_file = self.CACHE_DIR / f"{npi}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Cache write error: {e}")
    
    def _is_cache_expired(self, cached_data: Dict[str, Any]) -> bool:
        """Check if cached entry is expired"""
        if "timestamp" not in cached_data:
            return True
        
        try:
            timestamp = datetime.fromisoformat(cached_data["timestamp"])
            age = datetime.now() - timestamp
            return age > timedelta(days=self.CACHE_TTL_DAYS)
        except Exception:
            return True
    
    def _is_valid_npi_format(self, npi: Any) -> bool:
        """Validate NPI format"""
        import re
        npi_str = str(npi).strip()
        return bool(re.match(r"^[0-9]{10}$", npi_str))
    
    def clear_cache(self) -> None:
        """Clear all caches"""
        self._memory_cache.clear()
        try:
            for cache_file in self.CACHE_DIR.glob("*.json"):
                cache_file.unlink()
        except Exception as e:
            print(f"Cache clear error: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_files = list(self.CACHE_DIR.glob("*.json"))
        return {
            "memory_cache_size": len(self._memory_cache),
            "disk_cache_files": len(cache_files),
            "cache_directory": str(self.CACHE_DIR),
            "ttl_days": self.CACHE_TTL_DAYS,
        }


# Singleton instance
_npi_service = None

def get_npi_service() -> NPILookupService:
    """Get singleton NPI service instance"""
    global _npi_service
    if _npi_service is None:
        _npi_service = NPILookupService()
    return _npi_service
