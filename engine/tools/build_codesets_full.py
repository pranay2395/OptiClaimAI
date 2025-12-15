import os
import zipfile
import requests
import pandas as pd
from io import BytesIO
from tqdm import tqdm

BASE_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "code_sets"))
os.makedirs(OUT_DIR, exist_ok=True)

def download(url, desc):
    print(f"\n[DOWNLOADING] {desc}")
    r = requests.get(url, stream=True, timeout=300)
    r.raise_for_status()
    return r.content

# -------------------------------------------------------
# ICD-10-CM (FULL – ~75k codes)
# -------------------------------------------------------
def build_icd10():
    url = "https://www.cms.gov/files/zip/2025-code-descriptions-tabular-order.zip"
    content = download(url, "ICD-10-CM Full")

    z = zipfile.ZipFile(BytesIO(content))
    txt_file = [f for f in z.namelist() if f.endswith(".txt")][0]

    rows = []
    for line in z.open(txt_file).read().decode("latin1").splitlines():
        code = line[:7].strip()
        desc = line[7:].strip()
        if code:
            rows.append((code, desc))

    df = pd.DataFrame(rows, columns=["code", "description"])
    df.to_csv(os.path.join(OUT_DIR, "icd10.csv"), index=False)
    print(f"[OK] ICD-10-CM rows: {len(df)}")

# -------------------------------------------------------
# HCPCS Level II (FULL)
# -------------------------------------------------------
def build_hcpcs():
    url = "https://www.cms.gov/files/excel/2025-alphanumeric-hcpcs.xlsx"
    content = download(url, "HCPCS Level II")

    df = pd.read_excel(BytesIO(content))
    df = df.rename(columns={
        "HCPCS Code": "code",
        "Short Description": "description"
    })

    df = df[["code", "description"]].dropna()
    df.to_csv(os.path.join(OUT_DIR, "hcpcs_level2.csv"), index=False)
    print(f"[OK] HCPCS rows: {len(df)}")

# -------------------------------------------------------
# CPT via CMS RVU file (LEGAL PROXY)
# -------------------------------------------------------
def build_cpt_rvu():
    url = "https://www.cms.gov/files/csv/2025-pfs-relative-value-file.csv"
    content = download(url, "CMS RVU (CPT proxy)")

    df = pd.read_csv(BytesIO(content), low_memory=False)
    df = df.rename(columns={
        "hcpcs_code": "code",
        "short_descriptor": "description"
    })

    df = df[["code", "description", "work_rvu", "non_fac_pe_rvu", "fac_pe_rvu"]]
    df = df.dropna(subset=["code"])
    df.to_csv(os.path.join(OUT_DIR, "cpt_rvu.csv"), index=False)
    print(f"[OK] CPT/RVU rows: {len(df)}")

# -------------------------------------------------------
# Provider Taxonomy (FULL)
# -------------------------------------------------------
def build_taxonomy():
    url = "https://data.cms.gov/data-api/v1/dataset/healthcare-provider-taxonomy.csv"
    content = download(url, "Provider Taxonomy")

    df = pd.read_csv(BytesIO(content))
    df = df.rename(columns={
        "Code": "code",
        "Classification": "classification",
        "Specialization": "specialization"
    })

    df = df[["code", "classification", "specialization"]]
    df.to_csv(os.path.join(OUT_DIR, "taxonomy.csv"), index=False)
    print(f"[OK] Taxonomy rows: {len(df)}")

# -------------------------------------------------------
# Revenue Codes (CMS OPPS – FULL SET)
# -------------------------------------------------------
def build_revenue_codes():
    url = "https://www.cms.gov/files/excel/opps-addendum-a-and-b-updated.xlsx"
    content = download(url, "Revenue Codes")

    df = pd.read_excel(BytesIO(content), sheet_name=0)
    df = df.rename(columns={
        "APC": "revenue_code",
        "APC Description": "description"
    })

    df = df[["revenue_code", "description"]].dropna()
    df.to_csv(os.path.join(OUT_DIR, "revenue_codes.csv"), index=False)
    print(f"[OK] Revenue code rows: {len(df)}")

# -------------------------------------------------------
if __name__ == "__main__":
    print("\n=== BUILDING FULL CODESETS ===")
    build_icd10()
    build_hcpcs()
    build_cpt_rvu()
    build_taxonomy()
    build_revenue_codes()
    print("\nDONE. Code sets written to engine/code_sets/")
