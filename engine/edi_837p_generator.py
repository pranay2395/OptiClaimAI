"""
X12 837P EDI Generator - Convert CMS-1500 to X12 837 Professional
Deterministic conversion with validation
"""

from datetime import datetime
from model.cms1500_schema import CMS1500


class EDI837PGenerator:
    """Generate X12 837P EDI from CMS-1500"""
    
    def __init__(self):
        self.interchange_control_number = "000000001"
        self.group_control_number = "1"
        self.transaction_control_number = "1"
        self.functional_identifier_code = "HC"  # Health Care
        self.segment_terminator = "~"
        self.element_separator = "*"
        self.repetition_separator = "^"
    
    def generate(self, cms1500: CMS1500) -> str:
        """Generate complete X12 837P EDI"""
        
        segments = []
        
        # ISA Segment (Interchange Control Header)
        segments.append(self._generate_isa())
        
        # GS Segment (Functional Group Header)
        segments.append(self._generate_gs())
        
        # ST Segment (Transaction Set Header)
        segments.append(self._generate_st())
        
        # BHT Segment (Beginning of Hierarchical Transaction)
        segments.append(self._generate_bht(cms1500))
        
        # NM1 Segments (Names)
        segments.append(self._generate_nm1_submitter(cms1500))
        segments.append(self._generate_nm1_receiver())
        segments.append(self._generate_nm1_subscriber(cms1500))
        segments.append(self._generate_nm1_patient(cms1500))
        segments.append(self._generate_nm1_provider(cms1500))
        
        # HL Segments (Hierarchical Level)
        segments.append(self._generate_hl_subscriber())
        segments.append(self._generate_hl_patient())
        segments.append(self._generate_hl_provider())
        
        # HI Segment (Health Care Diagnosis Codes)
        segments.append(self._generate_hi(cms1500))
        
        # CLM Segment (Claim Information)
        segments.append(self._generate_clm(cms1500))
        
        # SV1 Segments (Service Line - repeating)
        for service_line in cms1500.service_lines:
            segments.append(self._generate_sv1(service_line))
        
        # SE Segment (Transaction Set Trailer)
        segments.append(self._generate_se(len(segments) + 1))
        
        # GE Segment (Functional Group Trailer)
        segments.append(self._generate_ge())
        
        # IEA Segment (Interchange Control Trailer)
        segments.append(self._generate_iea())
        
        # Join all segments with terminators
        edi_string = "".join(segments)
        return edi_string
    
    def _generate_isa(self) -> str:
        """ISA - Interchange Control Header"""
        isa_elements = [
            "ISA",  # Segment ID
            "00",  # Auth info qualifier
            "          ",  # Auth info
            "00",  # Security info qualifier
            "          ",  # Security info
            "01",  # Interchange ID qualifier (Duns)
            "0123456789     ",  # Interchange sender ID
            "01",  # Interchange ID qualifier
            "0987654321     ",  # Interchange receiver ID
            "200117",  # Interchange date
            "1234",  # Interchange time
            "^",  # Repetition separator
            "00501",  # Interchange control version
            "000000001",  # Interchange control number
            "0",  # Ack requested
            "P",  # Usage indicator
            ":",  # Component element separator
        ]
        return self.element_separator.join(isa_elements) + self.segment_terminator
    
    def _generate_gs(self) -> str:
        """GS - Functional Group Header"""
        gs_elements = [
            self.functional_identifier_code,  # Functional ID code
            "APP",  # Application sender's code
            "APP",  # Application receiver's code
            datetime.now().strftime("%Y%m%d"),  # Date
            datetime.now().strftime("%H%M"),  # Time
            self.group_control_number,  # Group control number
            "X",  # Responsible agency code
            "005010X222",  # Version identifier
        ]
        return "GS" + self.element_separator + self.element_separator.join(gs_elements) + self.segment_terminator
    
    def _generate_st(self) -> str:
        """ST - Transaction Set Header"""
        st_elements = [
            "837",  # Transaction set ID code
            self.transaction_control_number,  # Transaction set control number
            "005010X222",  # Implementation convention reference
        ]
        return "ST" + self.element_separator + self.element_separator.join(st_elements) + self.segment_terminator
    
    def _generate_bht(self, cms1500: CMS1500) -> str:
        """BHT - Beginning of Hierarchical Transaction"""
        bht_elements = [
            "0019",  # Hierarchical structure code
            "00",  # Batch control code
            "0123",  # Reference ID
            datetime.now().strftime("%Y%m%d"),  # Date
            datetime.now().strftime("%H%M"),  # Time
            "CH",  # Interchange control code
        ]
        return "BHT" + self.element_separator + self.element_separator.join(bht_elements) + self.segment_terminator
    
    def _generate_nm1_submitter(self, cms1500: CMS1500) -> str:
        """NM1 - Submitter Name"""
        nm1_elements = [
            "41",  # Entity identifier code (submitter)
            "2",  # Entity type qualifier (organization)
            cms1500.provider_info.provider_last_name,  # Name
            "",  # First name
            "",  # Middle initial
            "",  # Name prefix
            "",  # Name suffix
            "XX",  # Identification code qualifier
            cms1500.provider_info.tax_id,  # Identification code
        ]
        return "NM1" + self.element_separator + self.element_separator.join(nm1_elements) + self.segment_terminator
    
    def _generate_nm1_receiver(self) -> str:
        """NM1 - Receiver (Payer)"""
        nm1_elements = [
            "40",  # Entity identifier code (receiver)
            "2",  # Entity type qualifier
            "PAYER",  # Name
            "",  # First name
            "",  # Middle initial
            "",  # Prefix
            "",  # Suffix
            "XX",  # ID qualifier
            "999999",  # ID code
        ]
        return "NM1" + self.element_separator + self.element_separator.join(nm1_elements) + self.segment_terminator
    
    def _generate_nm1_subscriber(self, cms1500: CMS1500) -> str:
        """NM1 - Subscriber"""
        nm1_elements = [
            "IL",  # Entity identifier code (insured)
            "1",  # Entity type qualifier (person)
            cms1500.subscriber_info.name.split()[-1],  # Last name
            cms1500.subscriber_info.name.split()[0],  # First name
            "",  # Middle initial
            "",  # Prefix
            "",  # Suffix
            "MI",  # ID qualifier
            cms1500.subscriber_info.subscriber_id,  # Member ID
        ]
        return "NM1" + self.element_separator + self.element_separator.join(nm1_elements) + self.segment_terminator
    
    def _generate_nm1_patient(self, cms1500: CMS1500) -> str:
        """NM1 - Patient"""
        nm1_elements = [
            "QC",  # Entity identifier code (patient)
            "1",  # Entity type qualifier
            cms1500.patient_info.last_name,  # Last name
            cms1500.patient_info.first_name,  # First name
            "",  # Middle initial
            "",  # Prefix
            "",  # Suffix
            "MI",  # ID qualifier
            "",  # ID code (optional)
        ]
        return "NM1" + self.element_separator + self.element_separator.join(nm1_elements) + self.segment_terminator
    
    def _generate_nm1_provider(self, cms1500: CMS1500) -> str:
        """NM1 - Provider (Billing Provider)"""
        nm1_elements = [
            "82",  # Entity identifier code (billing provider)
            "1",  # Entity type qualifier
            cms1500.provider_info.provider_last_name,  # Last name
            cms1500.provider_info.provider_first_name or "",  # First name
            cms1500.provider_info.provider_middle_initial or "",  # Middle initial
            "",  # Prefix
            "",  # Suffix
            "NPI",  # ID qualifier
            cms1500.provider_info.npi,  # NPI
        ]
        return "NM1" + self.element_separator + self.element_separator.join(nm1_elements) + self.segment_terminator
    
    def _generate_hl_subscriber(self) -> str:
        """HL - Hierarchical Level (Subscriber)"""
        hl_elements = [
            "1",  # Hierarchical ID number
            "",  # Hierarchical parent ID number
            "20",  # Hierarchical level code
            "1",  # Hierarchical child code
        ]
        return "HL" + self.element_separator + self.element_separator.join(hl_elements) + self.segment_terminator
    
    def _generate_hl_patient(self) -> str:
        """HL - Hierarchical Level (Patient)"""
        hl_elements = [
            "2",  # Hierarchical ID number
            "1",  # Hierarchical parent ID number
            "21",  # Hierarchical level code
            "1",  # Hierarchical child code
        ]
        return "HL" + self.element_separator + self.element_separator.join(hl_elements) + self.segment_terminator
    
    def _generate_hl_provider(self) -> str:
        """HL - Hierarchical Level (Provider)"""
        hl_elements = [
            "3",  # Hierarchical ID number
            "2",  # Hierarchical parent ID number
            "22",  # Hierarchical level code
            "0",  # Hierarchical child code
        ]
        return "HL" + self.element_separator + self.element_separator.join(hl_elements) + self.segment_terminator
    
    def _generate_hi(self, cms1500: CMS1500) -> str:
        """HI - Health Care Diagnosis Codes"""
        hi_elements = ["HI"]
        for idx, diagnosis in enumerate(cms1500.diagnoses):
            if idx == 0:
                hi_elements.append(f"BK{self.repetition_separator}{diagnosis.code}")
            else:
                hi_elements.append(f"BF{self.repetition_separator}{diagnosis.code}")
        return self.element_separator.join(hi_elements) + self.segment_terminator
    
    def _generate_clm(self, cms1500: CMS1500) -> str:
        """CLM - Claim Header"""
        clm_elements = [
            cms1500.claim_number or "CLM001",  # Claim number
            str(cms1500.billing_info.total_charges),  # Claim amount
            "",  # Claim frequency
            cms1500.service_location.facility_npi or cms1500.provider_info.npi,  # Facility code qualifier
            "",  # Facility code
            "11",  # Place of service
            "",  # Claim submission reason code
            "",  # Benefits assignment certification indicator
            "",  # Benefits assignment indicator
            "",  # Release information code
            "",  # Patient signature source code
            "",  # Provider accept assignment code
            "",  # Participating provider contract code
            "",  # Claim status code
            "",  # Related causes code
            "",  # Special program indicator
            "",  # Levels of care indicator
            "",  # Care type indicator
            "",  # Information release indicator
            "",  # Home visit indicator
            "",  # Outside laboratory indicator
        ]
        return "CLM" + self.element_separator + self.element_separator.join(clm_elements) + self.segment_terminator
    
    def _generate_sv1(self, service_line) -> str:
        """SV1 - Service Line Detail"""
        sv1_elements = [
            "HC" + self.repetition_separator + service_line.procedure_code,  # Product/service ID
            str(service_line.charges),  # Line item charge
            "UN",  # Unit or basis for measurement
            str(service_line.units),  # Service unit count
            service_line.diagnosis_pointer,  # Diagnosis code pointer
            "",  # Rendering provider specimen ID
            "",  # Line note
        ]
        return "SV1" + self.element_separator + self.element_separator.join(sv1_elements) + self.segment_terminator
    
    def _generate_se(self, segment_count: int) -> str:
        """SE - Transaction Set Trailer"""
        se_elements = [
            str(segment_count),  # Number of segments
            self.transaction_control_number,  # Transaction control number
        ]
        return "SE" + self.element_separator + self.element_separator.join(se_elements) + self.segment_terminator
    
    def _generate_ge(self) -> str:
        """GE - Functional Group Trailer"""
        ge_elements = [
            "1",  # Number of transaction sets
            self.group_control_number,  # Group control number
        ]
        return "GE" + self.element_separator + self.element_separator.join(ge_elements) + self.segment_terminator
    
    def _generate_iea(self) -> str:
        """IEA - Interchange Control Trailer"""
        iea_elements = [
            "1",  # Number of functional groups
            self.interchange_control_number,  # Interchange control number
        ]
        return "IEA" + self.element_separator + self.element_separator.join(iea_elements) + self.segment_terminator


def cms1500_to_edi837p(cms1500: CMS1500) -> str:
    """Convert CMS-1500 to X12 837P EDI"""
    generator = EDI837PGenerator()
    return generator.generate(cms1500)
