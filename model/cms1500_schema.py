"""
CMS-1500 Form Schema - Complete claim form specification
Boxes 1-33 as defined by CMS
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date


@dataclass
class Subscriber:
    """Box 1: Insurance type (1a-1b)"""
    insurance_type: str  # "Medicare", "Medicaid", "TRICARE", "Champus", "Group Health", "FECA", "Other"
    
    
@dataclass
class SubscriberInfo:
    """Boxes 1a-1d: Subscriber information"""
    name: str
    dob: date
    gender: str  # "M" or "F"
    subscriber_id: str
    group_name: Optional[str] = None
    group_number: Optional[str] = None


@dataclass
class PatientInfo:
    """Boxes 2-5: Patient information"""
    first_name: str
    last_name: str
    dob: date
    gender: str  # "M" or "F"
    relationship_to_subscriber: str  # "Self", "Spouse", "Child", "Other"


@dataclass
class InsuranceInfo:
    """Boxes 4-7: Insurance information"""
    insured_name: Optional[str] = None
    insured_dob: Optional[date] = None
    insured_gender: Optional[str] = None
    group_name: Optional[str] = None
    group_number: Optional[str] = None
    other_insurance_name: Optional[str] = None
    other_insurance_plan: Optional[str] = None


@dataclass
class AuthorizationInfo:
    """Boxes 10-11: Conditions applicable to claim"""
    employment_related: bool = False
    auto_accident: bool = False
    other_accident: bool = False
    accident_state: Optional[str] = None
    condition_codes: List[str] = field(default_factory=list)


@dataclass
class AuthorizationNumber:
    """Box 23: Prior authorization or referral number"""
    auth_number: Optional[str] = None


@dataclass
class ServiceLocation:
    """Boxes 32-33: Service location information"""
    facility_name: Optional[str] = None
    facility_npi: Optional[str] = None
    facility_address: Optional[str] = None
    facility_city: Optional[str] = None
    facility_state: Optional[str] = None
    facility_zip: Optional[str] = None


@dataclass
class ProviderInfo:
    """Boxes 24j-33: Provider information"""
    npi: str
    tax_id: str
    provider_last_name: str
    provider_first_name: Optional[str] = None
    provider_middle_initial: Optional[str] = None
    provider_credentials: Optional[str] = None
    provider_specialty: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


@dataclass
class DiagnosisCode:
    """Box 21: Diagnosis codes (ICD-10)"""
    code: str
    primary: bool = False
    sequence_number: int = 0


@dataclass
class ServiceLine:
    """Box 24: Service line detail (repeatable)"""
    line_number: int
    from_date: date
    to_date: date
    place_of_service: str  # "11" (office), "21" (inpatient), etc.
    emg: bool  # Emergency
    procedure_code: str  # CPT/HCPCS code
    modifier_1: Optional[str] = None
    modifier_2: Optional[str] = None
    modifier_3: Optional[str] = None
    modifier_4: Optional[str] = None
    diagnosis_pointer: str = "1"  # Reference to diagnosis box 21
    charges: float = 0.0
    units: int = 1
    tos: Optional[str] = None  # Type of service


@dataclass
class BillingInfo:
    """Boxes 25-31: Billing information"""
    federal_tax_id: str
    federal_tax_id_type: str  # "EIN" or "SSN"
    accept_assignment: bool = True
    total_charges: float = 0.0
    total_paid: float = 0.0
    balance_due: float = 0.0
    remark_codes: List[str] = field(default_factory=list)


@dataclass
class CMS1500:
    """Complete CMS-1500 form"""
    # Box 1: Insurance type
    subscriber: Subscriber
    
    # Boxes 1a-1d: Subscriber info
    subscriber_info: SubscriberInfo
    
    # Boxes 2-5: Patient info
    patient_info: PatientInfo
    
    # Boxes 4-7: Insurance info
    insurance_info: InsuranceInfo
    
    # Boxes 10-11: Conditions
    authorization_info: AuthorizationInfo
    
    # Box 23: Auth/referral number
    authorization_number: AuthorizationNumber
    
    # Boxes 24a-24j: Service lines
    service_lines: List[ServiceLine] = field(default_factory=list)
    
    # Box 21: Diagnoses
    diagnoses: List[DiagnosisCode] = field(default_factory=list)
    
    # Boxes 25-31: Billing info
    billing_info: BillingInfo = field(default_factory=lambda: BillingInfo(federal_tax_id="", federal_tax_id_type="EIN"))
    
    # Boxes 32-33: Service location
    service_location: ServiceLocation = field(default_factory=ServiceLocation)
    
    # Provider info
    provider_info: ProviderInfo = field(default_factory=lambda: ProviderInfo(npi="", tax_id="", provider_last_name=""))
    
    # Claim info
    claim_number: Optional[str] = None
    claim_frequency: str = "1"  # "1" = original
    
    def is_complete(self) -> bool:
        """Validate that all required fields are present"""
        required_fields = [
            self.subscriber.insurance_type,
            self.subscriber_info.name,
            self.patient_info.first_name,
            self.patient_info.last_name,
            self.provider_info.npi,
            self.provider_info.tax_id,
        ]
        return all(required_fields) and len(self.service_lines) > 0 and len(self.diagnoses) > 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "subscriber": {
                "insurance_type": self.subscriber.insurance_type,
            },
            "subscriber_info": {
                "name": self.subscriber_info.name,
                "dob": str(self.subscriber_info.dob),
                "gender": self.subscriber_info.gender,
                "subscriber_id": self.subscriber_info.subscriber_id,
                "group_name": self.subscriber_info.group_name,
                "group_number": self.subscriber_info.group_number,
            },
            "patient_info": {
                "first_name": self.patient_info.first_name,
                "last_name": self.patient_info.last_name,
                "dob": str(self.patient_info.dob),
                "gender": self.patient_info.gender,
                "relationship": self.patient_info.relationship_to_subscriber,
            },
            "provider_info": {
                "npi": self.provider_info.npi,
                "tax_id": self.provider_info.tax_id,
                "last_name": self.provider_info.provider_last_name,
                "first_name": self.provider_info.provider_first_name,
                "phone": self.provider_info.phone,
            },
            "service_lines": [
                {
                    "line_number": sl.line_number,
                    "from_date": str(sl.from_date),
                    "to_date": str(sl.to_date),
                    "place_of_service": sl.place_of_service,
                    "procedure_code": sl.procedure_code,
                    "modifiers": [sl.modifier_1, sl.modifier_2, sl.modifier_3, sl.modifier_4],
                    "charges": sl.charges,
                    "units": sl.units,
                }
                for sl in self.service_lines
            ],
            "diagnoses": [
                {"code": d.code, "primary": d.primary, "sequence": d.sequence_number}
                for d in self.diagnoses
            ],
            "billing_info": {
                "total_charges": self.billing_info.total_charges,
                "total_paid": self.billing_info.total_paid,
                "balance_due": self.billing_info.balance_due,
            },
            "claim_number": self.claim_number,
        }
    
    def summary(self) -> str:
        """Generate human-readable summary"""
        lines = [
            "=== CMS-1500 CLAIM ===",
            f"Patient: {self.patient_info.first_name} {self.patient_info.last_name}",
            f"DOB: {self.patient_info.dob}",
            f"Provider: {self.provider_info.provider_last_name}, {self.provider_info.provider_first_name}",
            f"NPI: {self.provider_info.npi}",
            f"Service Lines: {len(self.service_lines)}",
            f"Diagnoses: {len(self.diagnoses)}",
            f"Total Charges: ${self.billing_info.total_charges:.2f}",
            f"Complete: {self.is_complete()}",
        ]
        return "\n".join(lines)
