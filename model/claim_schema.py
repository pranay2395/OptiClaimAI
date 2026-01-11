"""
Canonical Claim Schema - Single source of truth for all claim data
"""

from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict
from datetime import date


@dataclass
class Patient:
    """Patient information"""
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None  # M/F
    insurance_id: Optional[str] = None
    group_number: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    def is_complete(self) -> bool:
        """Check if patient has required fields"""
        return bool(self.first_name and self.last_name and self.date_of_birth and self.insurance_id)


@dataclass
class Provider:
    """Healthcare provider"""
    first_name: str
    last_name: str
    npi: str
    tax_id: Optional[str] = None
    specialty: Optional[str] = None
    facility_name: Optional[str] = None
    phone: Optional[str] = None

    def is_complete(self) -> bool:
        """Check if provider has required fields"""
        return bool(self.first_name and self.last_name and self.npi and len(self.npi) == 10)


@dataclass
class Diagnosis:
    """Diagnosis code (ICD-10)"""
    code: str  # ICD-10 code (e.g., "M54.5")
    description: Optional[str] = None
    primary: bool = True


@dataclass
class Procedure:
    """Procedure with charges (CPT)"""
    code: str  # CPT code (e.g., "99213")
    description: Optional[str] = None
    units: float = 1.0
    charge: float = 0.0
    modifiers: List[str] = field(default_factory=list)  # e.g., ["25"]


@dataclass
class Claim:
    """Complete claim - canonical representation"""
    patient: Patient
    provider: Provider
    diagnoses: List[Diagnosis]
    procedures: List[Procedure]
    service_date: Optional[date] = None
    claim_amount: float = 0.0
    claim_id: Optional[str] = None
    payer_name: Optional[str] = None
    place_of_service: Optional[str] = None  # "11" = office, "21" = inpatient
    
    def __post_init__(self):
        """Calculate total claim amount if not set"""
        if self.claim_amount == 0 and self.procedures:
            self.claim_amount = sum(p.charge for p in self.procedures)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for downstream processing"""
        return asdict(self)
    
    def summary(self) -> str:
        """Human-readable summary"""
        return f"""
**Patient:** {self.patient.first_name} {self.patient.last_name} (DOB: {self.patient.date_of_birth})
**Provider:** {self.provider.first_name} {self.provider.last_name} (NPI: {self.provider.npi})
**Service Date:** {self.service_date}
**Total Charge:** ${self.claim_amount:,.2f}
**Diagnoses:** {', '.join(d.code for d in self.diagnoses) if self.diagnoses else 'None'}
**Procedures:** {len(self.procedures)} procedure(s)
""".strip()
