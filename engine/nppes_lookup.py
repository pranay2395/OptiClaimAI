"""
NPPES (National Plan and Provider Enumeration System) Provider Lookup
Free public API - no paid services required
Caches results locally to reduce API calls
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

CACHE_FILE = "nppes_cache.json"
CACHE_EXPIRY_HOURS = 24
NPPES_API_URL = "https://npiregistry.cms.hhs.gov/api/"


class NPPESLookup:
    """NPPES provider lookup with local caching"""
    
    def __init__(self):
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Load cache from file if it exists and is fresh"""
        if not os.path.exists(CACHE_FILE):
            return {}
        
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                # Check if cache is still valid
                if data.get('timestamp'):
                    cache_time = datetime.fromisoformat(data['timestamp'])
                    if datetime.now() - cache_time > timedelta(hours=CACHE_EXPIRY_HOURS):
                        return {}
                return data.get('providers', {})
        except:
            return {}
    
    def _save_cache(self):
        """Save cache to file"""
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'providers': self.cache
                }, f, indent=2)
        except:
            pass  # Silently fail - caching is optional
    
    def lookup_npi(self, npi: str) -> Optional[Dict]:
        """
        Look up provider by NPI
        Returns: {first_name, last_name, address, city, state, zip, phone, taxonomy_code, specialty}
        Returns None if not found
        """
        if not npi or not npi.isdigit():
            return None
        
        # Check cache first
        if npi in self.cache:
            return self.cache[npi]
        
        try:
            response = requests.get(
                f"{NPPES_API_URL}",
                params={"number": npi, "limit": 1},
                timeout=5
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            results = data.get('results', [])
            
            if not results:
                return None
            
            result = results[0]
            
            # Extract individual provider info
            basic = result.get('basic', {})
            addresses = result.get('addresses', [])
            taxonomies = result.get('taxonomies', [])
            
            first_address = addresses[0] if addresses else {}
            first_taxonomy = taxonomies[0] if taxonomies else {}
            
            provider_info = {
                'first_name': basic.get('first_name', ''),
                'last_name': basic.get('last_name', ''),
                'middle_name': basic.get('middle_name', ''),
                'address': first_address.get('address_1', ''),
                'address_2': first_address.get('address_2', ''),
                'city': first_address.get('city', ''),
                'state': first_address.get('state', ''),
                'zip': first_address.get('postal_code', ''),
                'phone': first_address.get('telephone_number', ''),
                'taxonomy_code': first_taxonomy.get('code', ''),
                'specialty': first_taxonomy.get('desc', ''),
            }
            
            # Cache the result
            self.cache[npi] = provider_info
            self._save_cache()
            
            return provider_info
            
        except Exception as e:
            return None
    
    def lookup_provider_name(self, npi: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Quick lookup - returns (first_name, last_name) or (None, None)
        """
        info = self.lookup_npi(npi)
        if info:
            return (info.get('first_name'), info.get('last_name'))
        return (None, None)


# Singleton instance
_nppes_instance = None

def get_nppes_lookup() -> NPPESLookup:
    """Get or create NPPES lookup instance"""
    global _nppes_instance
    if _nppes_instance is None:
        _nppes_instance = NPPESLookup()
    return _nppes_instance


if __name__ == "__main__":
    # Test
    lookup = NPPESLookup()
    result = lookup.lookup_npi("1122334455")
    print("Test lookup result:", result)
