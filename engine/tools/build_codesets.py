"""
OptiClaimAI – Code Set Builder
Authoritative, FREE data only (CMS / CDC / NUCC)

This script:
- Downloads public datasets
- Normalizes them
- Writes CSVs compatible with rule_engine.py

Python 3.9+
pip install pandas requests openpyxl
"""

import os
import csv
import zipfile
import requests
import pandas as pd
from io import BytesIO

BASE_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "code_sets"))
os.makedirs(OUT_DIR, exist_ok=True)

def download(url):
    print(f"[DOWNLOAD] {url}")
    r = requests.get(url, allow_redirects=True, timeout=120)
    r.raise_for_status()
    return r.content

def save_csv(df, name):
    path = os.path.join(OUT_DIR, name)
    df.to_csv(path, index=False)
    print(f"[OK] {name} ({len(df)} rows)")

# ---------------------------------------------------
# ICD-10-CM (CDC / CMS – PUBLIC)
# ---------------------------------------------------
def build_icd10():
    """
    Source:
    https://www.cms.gov/medicare/coding/icd10
    """
    url = "https://www.cms.gov/files/zip/2025-code-descriptions-tabular-order.zip"
    data = download(url)

    z = zipfile.ZipFile(BytesIO(data))
    txt_file = [f for f in z.namelist() if f.endswith(".txt")][0]

    rows = []
    for line in z.open(txt_file).read().decode("latin1").splitlines():
        if line.strip():
            code = line[:7].strip()
            desc = line[7:].strip()
            if code:
                rows.append((code, desc))

    df = pd.DataFrame(rows, columns=["code", "description"])
    save_csv(df, "icd10.csv")

# ---------------------------------------------------
# HCPCS Level II (CMS – PUBLIC)
# ---------------------------------------------------
def build_hcpcs():
    """
    Source:
    https://www.cms.gov/medicare/healthcare-common-procedure-coding-system/quarterly-update
    """
    url = "https://www.cms.gov/files/excel/2025-alphanumeric-hcpcs.xlsx"
    data = download(url)

    df = pd.read_excel(BytesIO(data))
    df.columns = df.columns.str.lower()

    df = df.rename(columns={
        "hcpcs code": "code",
        "short description": "description"
    })[["code", "description"]]

    save_csv(df, "hcpcs_level2.csv")

# ---------------------------------------------------
# CPT via CMS RVU FILE (LEGAL PROXY)
# ---------------------------------------------------
def build_cpt_rvu():
    """
    Source:
    https://www.cms.gov/medicare/physician-fee-schedule
    """
    url = "https://www.cms.gov/files/csv/2025-pfs-relative-value-file.csv"
    data = download(url)

    df = pd.read_csv(BytesIO(data))
    df = df.rename(columns={
        "hcpcs_code": "code",
        "short_descriptor": "description"
    })

    df = df[["code", "description", "work_rvu"]]
    save_csv(df, "cpt_rvu.csv")

# ---------------------------------------------------
# PROVIDER TAXONOMY (NUCC – PUBLIC)
# ---------------------------------------------------
def build_taxonomy():
    """
    Source:
    https://data.cms.gov/provider-characteristics/healthcare-provider-taxonomy
    """
    url = "https://data.cms.gov/data-api/v1/dataset/healthcare-provider-taxonomy.csv"
    data = download(url)

    df = pd.read_csv(BytesIO(data))
    df = df.rename(columns={
        "Code": "code",
        "Classification": "classification",
        "Specialization": "specialization"
    })

    save_csv(df[["code", "classification", "specialization"]], "taxonomy.csv")

# ---------------------------------------------------
# REVENUE CODES (CMS OPPS – PUBLIC)
# ---------------------------------------------------
def build_revenue_codes():
    rows = [
        ("0100", "All inclusive room and board"),
        ("0120", "General medical/surgical"),
        ("0360", "Operating room services"),
        ("0450", "Emergency room"),
        ("0762", "Observation room"),
    ]

    df = pd.DataFrame(rows, columns=["code", "description"])
    save_csv(df, "revenue_codes.csv")

# ---------------------------------------------------
# MODIFIERS (CMS – PUBLIC LIST)
# ---------------------------------------------------
def build_modifiers():
    rows = [
        ("25", "Significant separately identifiable E/M"),
        ("26", "Professional component"),
        ("50", "Bilateral procedure"),
        ("59", "Distinct procedural service"),
        ("76", "Repeat procedure"),
        ("77", "Repeat procedure by another physician"),
        ("91", "Repeat lab test"),
    ]

    df = pd.DataFrame(rows, columns=["modifier", "description"])
    save_csv(df, "modifiers.csv")

# ---------------------------------------------------
# NPI REGISTRY (MANUAL DOWNLOAD)
# ---------------------------------------------------
def npi_notice():
    print("\n⚠️ NPI REGISTRY IS TOO LARGE FOR AUTO-DOWNLOAD")
    print("Download manually from:")
    print("https://download.cms.gov/nppes/NPI_Files.html")
    print("Then filter columns into: npi_registry.csv\n")

# ---------------------------------------------------
if __name__ == "__main__":
    build_icd10()
    build_hcpcs()
    build_cpt_rvu()
    build_taxonomy()
    build_revenue_codes()
    build_modifiers()
    npi_notice()