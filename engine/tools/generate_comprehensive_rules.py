"""
OptiClaimAI - Comprehensive Rules Generator
Generates validation rules from official healthcare code sets
Downloads latest data and creates practical validation rules
"""

import os
import json
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime

class ComprehensiveRulesGenerator:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.code_sets_dir = self.base_dir / "code_sets"
        self.rules_dir = self.base_dir / "rules"
        self.code_sets_dir.mkdir(exist_ok=True)
        self.rules_dir.mkdir(exist_ok=True)

    def download_latest_codesets(self):
        """Download the most recent healthcare code sets from official sources"""
        print("🔄 Downloading latest healthcare code sets...")

        # ICD-10-CM (2025)
        try:
            icd_url = "https://www.cms.gov/files/zip/2025-code-descriptions-tabular-order.zip"
            self._download_and_extract_icd10(icd_url)
        except Exception as e:
            print(f"⚠️ ICD-10 download failed: {e}")

        # HCPCS Level II (2025)
        try:
            hcpcs_url = "https://www.cms.gov/files/excel/2025-alphanumeric-hcpcs.xlsx"
            self._download_hcpcs(hcpcs_url)
        except Exception as e:
            print(f"⚠️ HCPCS download failed: {e}")

        # CPT (via RVU file)
        try:
            cpt_url = "https://www.cms.gov/files/csv/2025-pfs-relative-value-file.csv"
            self._download_cpt(cpt_url)
        except Exception as e:
            print(f"⚠️ CPT download failed: {e}")

        print("✅ Code sets downloaded successfully")

    def _download_and_extract_icd10(self, url):
        """Download and extract ICD-10 codes"""
        import zipfile
        from io import BytesIO

        response = requests.get(url, timeout=120)
        response.raise_for_status()

        with zipfile.ZipFile(BytesIO(response.content)) as zf:
            txt_files = [f for f in zf.namelist() if f.endswith('.txt')]
            if txt_files:
                with zf.open(txt_files[0]) as f:
                    content = f.read().decode('latin1')

                codes = []
                for line in content.splitlines():
                    if line.strip():
                        code = line[:7].strip()
                        desc = line[7:].strip()
                        if code:
                            codes.append({'code': code, 'description': desc})

                df = pd.DataFrame(codes)
                df.to_csv(self.code_sets_dir / "icd10.csv", index=False)
                print(f"📋 ICD-10: {len(df)} codes")

    def _download_hcpcs(self, url):
        """Download HCPCS codes"""
        response = requests.get(url, timeout=120)
        response.raise_for_status()

        df = pd.read_excel(BytesIO(response.content))
        df.columns = df.columns.str.lower()

