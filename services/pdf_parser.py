"""
PDF Claim Parser
Extract claim information from uploaded PDF documents
"""

import re
from typing import Optional, Dict, Any
from datetime import datetime
import io


class PDFClaimParser:
    """Parse claims from PDF and auto-fill form"""
    
    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> Optional[str]:
        """
        Extract text from PDF bytes.
        Requires PyPDF2 or pdfplumber
        Returns None if extraction fails (image-based PDFs, scanned documents)
        """
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text if text.strip() else None
        except ImportError:
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    text = ""
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    return text if text.strip() else None
            except ImportError:
                return None
        except Exception as e:
            return None
    
    @staticmethod
    def parse_claim_data(text: str) -> Dict[str, Any]:
        """
        Parse claim text and extract structured data.
        Handles CMS-1500 and claim documents.
        """
        parsed = {
            "patient_first": None,
            "patient_last": None,
            "patient_dob": None,
            "patient_member_id": None,
            "provider_npi": None,
            "provider_first": None,
            "provider_last": None,
            "service_date": None,
            "procedure_code": None,
            "charge": None,
            "diagnosis_code": None,
        }
        
        # Patient name patterns
        patient_patterns = [
            r"(?:PATIENT|INSURED).*?NAME[:\s]+([A-Z][a-z]+)\s+([A-Z][a-z]+)",
            r"(?:Patient|Insured)\s+(?:Name|name)[:\s]+([A-Z][a-z]+)\s+([A-Z][a-z]+)",
        ]
        
        for pattern in patient_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parsed["patient_first"] = match.group(1)
                parsed["patient_last"] = match.group(2)
                break
        
        # DOB patterns (MM/DD/YYYY or YYYY-MM-DD)
        dob_patterns = [
            r"(?:DOB|Date of Birth)[:\s]+(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
            r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",
        ]
        
        for pattern in dob_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        # Try MM/DD/YYYY format
                        if len(groups[0]) <= 2:
                            dob = f"{groups[2]}-{groups[0]:0>2}-{groups[1]:0>2}"
                        else:
                            # YYYY-MM-DD format
                            dob = f"{groups[0]}-{groups[1]:0>2}-{groups[2]:0>2}"
                        parsed["patient_dob"] = dob
                        break
                except:
                    pass
        
        # Member ID
        member_patterns = [
            r"(?:Member|Policy|ID|MRN)[#\s:]+([A-Z0-9]{5,20})",
            r"(?:Member|Policy)\s+(?:ID|ID#)[:\s]+([A-Z0-9]{5,20})",
        ]
        
        for pattern in member_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parsed["patient_member_id"] = match.group(1)
                break
        
        # Provider NPI (10 digits)
        npi_match = re.search(r"(?:NPI|Provider\s+ID)[#:\s]*(\d{10})", text, re.IGNORECASE)
        if npi_match:
            parsed["provider_npi"] = npi_match.group(1)
        
        # Provider name
        provider_patterns = [
            r"(?:Provider|Physician|Dr\.?)\s+(?:Name|name)[:\s]+([A-Z][a-z]+)\s+([A-Z][a-z]+)",
            r"(?:Provider|Physician)[:\s]+([A-Z][a-z]+)\s+([A-Z][a-z]+)",
        ]
        
        for pattern in provider_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parsed["provider_first"] = match.group(1)
                parsed["provider_last"] = match.group(2)
                break
        
        # Service date (MM/DD/YYYY or YYYY-MM-DD)
        service_patterns = [
            r"(?:Service|DOS|Date of Service)[:\s]+(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
            r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",
        ]
        
        for pattern in service_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if len(groups[0]) <= 2:
                            service_date = f"{groups[2]}-{groups[0]:0>2}-{groups[1]:0>2}"
                        else:
                            service_date = f"{groups[0]}-{groups[1]:0>2}-{groups[2]:0>2}"
                        parsed["service_date"] = service_date
                        break
                except:
                    pass
        
        # Procedure code (5-10 alphanumeric, typically CPT or HCPCS)
        proc_patterns = [
            r"(?:CPT|Procedure|Code)[:\s#]+([0-9A-Z]{5,10})",
            r"(?:Code|Procedure)[:\s]+([0-9A-Z]{5,10})",
        ]
        
        for pattern in proc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parsed["procedure_code"] = match.group(1).upper()
                break
        
        # Charge amount (dollar amount)
        charge_patterns = [
            r"(?:Charge|Amount|Total)[:\s$]+(\d+\.?\d{0,2})",
            r"\$(\d+\.?\d{0,2})",
        ]
        
        for pattern in charge_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    parsed["charge"] = float(match.group(1))
                    break
                except:
                    pass
        
        # Diagnosis (ICD-10 code)
        diag_patterns = [
            r"(?:Diagnosis|ICD-10|ICD10|Dx)[#:\s]+([A-Z]\d{1,2}\.?\d{0,3})",
        ]
        
        for pattern in diag_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parsed["diagnosis_code"] = match.group(1).upper()
                break
        
        return parsed
    
    @staticmethod
    def parse_from_pdf_bytes(pdf_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse claim from PDF bytes.
        
        Returns: Dictionary of extracted fields or None if parsing fails
        """
        # Extract text from PDF
        text = PDFClaimParser.extract_text_from_pdf(pdf_bytes)
        if not text:
            return None
        
        # Parse fields from text
        return PDFClaimParser.parse_claim_data(text)
