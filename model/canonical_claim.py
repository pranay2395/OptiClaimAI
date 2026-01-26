"""
Canonical Claim Model
Single source of truth for all healthcare claims.
Maps from CMS-1500, EDI 837P, free text, and guided forms.
"""

from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field, field_validator, ConfigDict
import json
from pathlib import Path


class Address(BaseModel):
    """Address information"""
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    zip_code: Optional[str] = None
    country: str = "US"


class Patient(BaseModel):
    """Patient demographic information"""
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Optional[str] = Field(None, pattern="^[MFU]$")
    member_id: Optional[str] = None
    address: Optional[Address] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class Subscriber(BaseModel):
    """Insurance subscriber (may differ from patient)"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, pattern="^[MFU]$")
    relationship_to_patient: Optional[str] = None  # self, spouse, parent, child, other
    member_id: Optional[str] = None
    group_number: Optional[str] = None
    address: Optional[Address] = None


class Payer(BaseModel):
    """Insurance payer information"""
    payer_name: Optional[str] = None
    payer_id: Optional[str] = None  # ANSI payer ID
    payer_code: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[Address] = None


class Provider(BaseModel):
    """Rendering provider (physician/clinician)"""
    npi: str = Field(..., pattern="^[0-9]{10}$")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    credential: Optional[str] = None  # MD, DO, NP, PA, etc.
    taxonomy_code: Optional[str] = None
    address: Optional[Address] = None
    phone: Optional[str] = None


class BillingProvider(BaseModel):
    """Facility/organization that submits claim"""
    npi: Optional[str] = Field(None, pattern="^[0-9]{10}$")
    facility_name: Optional[str] = None
    ein: Optional[str] = None  # Employer Identification Number
    address: Optional[Address] = None
    phone: Optional[str] = None


class Diagnosis(BaseModel):
    """ICD-10 diagnosis code and details"""
    sequence: Optional[int] = None  # 1 = primary
    icd10_code: str
    description: Optional[str] = None
    date_of_diagnosis: Optional[date] = None
    is_primary: Optional[bool] = None


class ServiceLine(BaseModel):
    """Individual service/procedure"""
    line_number: Optional[int] = None
    service_date: date
    service_end_date: Optional[date] = None
    place_of_service_code: Optional[str] = None  # CMS codes 01-99
    type_of_service_code: Optional[str] = None
    procedure_code: str  # CPT or HCPCS
    procedure_modifiers: Optional[List[str]] = None  # e.g., ['25', '59']
    description: Optional[str] = None
    units: Optional[float] = Field(None, ge=0)
    unit_price: Optional[float] = Field(None, ge=0)
    line_charge: float = Field(..., ge=0)
    line_paid: Optional[float] = Field(None, ge=0)
    line_patient_responsibility: Optional[float] = Field(None, ge=0)
    diagnosis_pointers: Optional[List[str]] = None  # A, B, C, D references
    rendering_provider_npi: Optional[str] = Field(None, pattern="^[0-9]{10}$")


class ClaimTotals(BaseModel):
    """Aggregated claim amounts"""
    total_charges: Optional[float] = Field(None, ge=0)
    total_paid: Optional[float] = Field(None, ge=0)
    patient_responsibility: Optional[float] = Field(None, ge=0)


class ClaimMetadata(BaseModel):
    """Claim-level metadata"""
    claim_id: Optional[str] = None
    submission_date: Optional[date] = None
    source: Optional[str] = None  # cms1500_form, edi_837p, free_text, guided_form
    version: str = "1.0"


class CanonicalClaim(BaseModel):
    """
    Canonical claim model - single source of truth.
    All input methods map to this structure.
    """
    patient: Patient
    provider: Provider
    service_lines: List[ServiceLine] = Field(..., min_length=1)
    diagnoses: List[Diagnosis] = Field(..., min_length=1)
    
    subscriber: Optional[Subscriber] = None
    payer: Optional[Payer] = None
    billing_provider: Optional[BillingProvider] = None
    claim_totals: Optional[ClaimTotals] = None
    metadata: Optional[ClaimMetadata] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patient": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "date_of_birth": "1980-01-15",
                    "gender": "M",
                    "member_id": "MEM123456"
                },
                "provider": {
                    "npi": "1234567890",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "credential": "MD"
                },
                "service_lines": [
                    {
                        "line_number": 1,
                        "service_date": "2024-01-10",
                        "procedure_code": "99213",
                        "line_charge": 150.00,
                        "place_of_service_code": "11"
                    }
                ],
                "diagnoses": [
                    {
                        "sequence": 1,
                        "icd10_code": "J45.901",
                        "is_primary": True
                    }
                ]
            }
        }
    )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return self.model_dump(exclude_none=True)

    def to_json_str(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json(exclude_none=True, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "CanonicalClaim":
        """Create from dictionary"""
        return cls(**data)

    @classmethod
    def from_json_str(cls, json_str: str) -> "CanonicalClaim":
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_json_file(cls, file_path: str) -> "CanonicalClaim":
        """Load from JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save_to_file(self, file_path: str) -> None:
        """Save to JSON file"""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(self.to_json_str())
