"""
EDI Bridge Service
EdiFabric microservice for 837P generation and validation.
Handles canonical claim to EDI 837P conversion and round-trip validation.
"""

import json
import subprocess
import tempfile
import os
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime


class EDIBridgeService:
    """
    EDI generation and validation service.
    
    This service interfaces with EdiFabric for:
    - Converting canonical claims to 837P EDI format
    - Parsing and validating 837P files
    - Round-trip validation (837P → canonical → 837P)
    """
    
    def __init__(self, edifabric_path: Optional[str] = None):
        """
        Initialize EDI bridge.
        
        Args:
            edifabric_path: Path to EdiFabric executable or library
        """
        self.edifabric_path = edifabric_path or os.getenv(
            "EDIFABRIC_PATH",
            "C:\\Program Files\\EdiFabric\\bin\\EdiFabric.exe"
        )
        self.temp_dir = Path(tempfile.gettempdir()) / "opticlaimai_edi"
        self.temp_dir.mkdir(exist_ok=True)
    
    def is_available(self) -> bool:
        """Check if EdiFabric is available"""
        if not self.edifabric_path:
            return False
        
        # For .NET DLL, check if file exists
        if self.edifabric_path.endswith(".dll"):
            return Path(self.edifabric_path).exists()
        
        # For executable
        return Path(self.edifabric_path).exists()
    
    def generate_edi_837p(self, canonical_claim: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate EDI 837P from canonical claim.
        
        Args:
            canonical_claim: Claim in canonical JSON format
        
        Returns:
            Tuple of (edi_text, error_message)
        """
        # For now, return a basic implementation
        # In production, this would call EdiFabric library or subprocess
        
        try:
            # Create temporary file with canonical claim
            claim_file = self.temp_dir / f"claim_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            with open(claim_file, 'w') as f:
                json.dump(canonical_claim, f, indent=2, default=str)
            
            # If EdiFabric is available, use it
            if self.is_available():
                return self._generate_via_edifabric(canonical_claim, str(claim_file))
            
            # Otherwise, generate basic EDI structure
            return self._generate_basic_837p(canonical_claim), None
        
        except Exception as e:
            return None, f"EDI generation error: {str(e)}"
    
    def parse_edi_837p(self, edi_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Parse EDI 837P file and return validation results.
        
        Args:
            edi_text: Raw EDI 837P text
        
        Returns:
            Tuple of (parsed_claim_dict, error_message)
        """
        try:
            # Create temporary EDI file
            edi_file = self.temp_dir / f"edi_{datetime.now().strftime('%Y%m%d%H%M%S')}.837"
            with open(edi_file, 'w') as f:
                f.write(edi_text)
            
            # If EdiFabric available, use it
            if self.is_available():
                return self._parse_via_edifabric(str(edi_file))
            
            # Otherwise, return basic parsing
            return self._parse_basic_837p(edi_text), None
        
        except Exception as e:
            return None, f"EDI parsing error: {str(e)}"
    
    def validate_edi_837p(self, edi_text: str) -> Dict[str, Any]:
        """
        Validate EDI 837P compliance.
        
        Returns dict with:
        - is_valid: bool
        - errors: list of validation errors
        - warnings: list of validation warnings
        - segments: parsed segment structure
        """
        try:
            # Create temporary EDI file
            edi_file = self.temp_dir / f"edi_validate_{datetime.now().strftime('%Y%m%d%H%M%S')}.837"
            with open(edi_file, 'w') as f:
                f.write(edi_text)
            
            # Basic validation
            errors = []
            warnings = []
            
            # Check for required segments
            segments = edi_text.split("~")
            segment_types = [s[:3] for s in segments if s]
            
            required_segments = ["ISA", "GS", "ST", "BHT", "NM1", "CLM", "SVC"]
            missing = [s for s in required_segments if s not in segment_types]
            
            if missing:
                errors.append(f"Missing required segments: {', '.join(missing)}")
            
            # Check segment counts
            if segment_types.count("ISA") != 1:
                errors.append("ISA segment should appear exactly once")
            if segment_types.count("GS") != 1:
                errors.append("GS segment should appear exactly once")
            
            return {
                "is_valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "segments": segment_types,
                "segment_count": len(segment_types),
            }
        
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [str(e)],
                "warnings": [],
                "segments": [],
            }
    
    def _generate_via_edifabric(self, claim: Dict[str, Any], claim_file: str) -> Tuple[Optional[str], Optional[str]]:
        """Generate 837P using EdiFabric subprocess"""
        try:
            # This would call EdiFabric CLI or library
            # For now, stub implementation
            result = subprocess.run(
                [self.edifabric_path, "generate", "--input", claim_file, "--format", "837p"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout, None
            else:
                return None, f"EdiFabric error: {result.stderr}"
        
        except Exception as e:
            return None, f"EdiFabric error: {str(e)}"
    
    def _generate_basic_837p(self, claim: Dict[str, Any]) -> str:
        """
        Generate basic 837P structure.
        This is a fallback if EdiFabric is not available.
        """
        patient = claim.get("patient", {})
        provider = claim.get("provider", {})
        service_lines = claim.get("service_lines", [])
        diagnoses = claim.get("diagnoses", [])
        payer = claim.get("payer", {})
        
        # ISA Segment (Interchange Control Header)
        isa = "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *200101*1200*^*00501*000000001*0*T*:"
        
        # GS Segment (Functional Group Header)
        gs = "GS*HC*SENDER*RECEIVER*20200101*1200*1*X*005010X222A1"
        
        # ST Segment (Transaction Set Header)
        st = "ST*837*0001*005010X222A1"
        
        # BHT Segment (Beginning of Hierarchical Transaction)
        bht = "BHT*0019*00*0123*20200101*1200*CH"
        
        # NM1 Segments
        billing_provider = claim.get("billing_provider", {})
        nm1_billing = f"NM1*IL*1*{patient.get('last_name')}*{patient.get('first_name')}****MI*{patient.get('member_id', '')}"
        nm1_provider = f"NM1*1P*1*{provider.get('last_name')}*{provider.get('first_name')}****NPI*{provider.get('npi', '')}"
        
        # Build service lines
        svc_lines = []
        for idx, line in enumerate(service_lines, 1):
            svc = f"SVC*{line.get('procedure_code')}*{line.get('line_charge', 0)}"
            svc_lines.append(svc)
        
        # Segment terminator
        segments = [isa, gs, st, bht, nm1_billing, nm1_provider] + svc_lines
        edi = "~\n".join(segments) + "~"
        
        return edi
    
    def _parse_via_edifabric(self, edi_file: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Parse 837P using EdiFabric subprocess"""
        try:
            result = subprocess.run(
                [self.edifabric_path, "parse", "--input", edi_file, "--format", "837p"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                parsed = json.loads(result.stdout)
                return parsed, None
            else:
                return None, f"EdiFabric parse error: {result.stderr}"
        
        except Exception as e:
            return None, f"EdiFabric error: {str(e)}"
    
    def _parse_basic_837p(self, edi_text: str) -> Dict[str, Any]:
        """
        Parse basic 837P structure.
        Fallback if EdiFabric not available.
        """
        segments = edi_text.split("~")
        parsed = {
            "segments": [],
            "claims": [],
        }
        
        for segment in segments:
            if not segment.strip():
                continue
            
            fields = segment.split("*")
            segment_type = fields[0][:3]
            
            parsed["segments"].append({
                "type": segment_type,
                "fields": fields,
            })
        
        return parsed
    
    def cleanup(self) -> None:
        """Clean up temporary files"""
        try:
            if self.temp_dir.exists():
                for file in self.temp_dir.glob("*"):
                    file.unlink()
        except Exception as e:
            print(f"Cleanup error: {e}")


# Singleton instance
_edi_service = None

def get_edi_service() -> EDIBridgeService:
    """Get singleton EDI service instance"""
    global _edi_service
    if _edi_service is None:
        _edi_service = EDIBridgeService()
    return _edi_service
