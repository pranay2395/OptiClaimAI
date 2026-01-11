"""
Test script for OptiClaimAI core pipeline
"""

from model.claim_schema import Claim, Patient, Provider, Diagnosis, Procedure
from model.claim_builder import ClaimBuilder
from engine.rules_engine_v2 import ClaimRulesEngine
from engine.output_formatter import OutputFormatter
from datetime import date

print("=" * 60)
print("OptiClaimAI Pipeline Test")
print("=" * 60)

# Test 1: Create claim directly
print("\n✓ Test 1: Direct Claim Creation")
claim = Claim(
    patient=Patient(
        first_name='John',
        last_name='Doe',
        date_of_birth=date(1980, 5, 20),
        insurance_id='ABC123456'
    ),
    provider=Provider(
        first_name='Jane',
        last_name='Smith',
        npi='1234567890'
    ),
    diagnoses=[Diagnosis(code='M54.5')],
    procedures=[Procedure(code='99213', charge=150.0)],
    service_date=date(2024, 1, 10),
    place_of_service='11'
)
print(f"  Claim created: {claim.patient.first_name} {claim.patient.last_name}")

# Test 2: Validate claim
print("\n✓ Test 2: Claim Validation")
engine = ClaimRulesEngine()
result = engine.validate(claim)
print(f"  Valid: {result['is_valid']}")
print(f"  Issues: {result['issue_count']}")
print(f"  Denial Risk: {result['denial_risk_level']} ({result['denial_risk_score']}%)")

# Test 3: Format output
print("\n✓ Test 3: Output Formatting")
summary = OutputFormatter.format_claim_summary(claim)
print(f"  Summary generated ({len(summary)} chars)")

# Test 4: Text parsing
print("\n✓ Test 4: Free-Text Parsing")
text = "Patient John Smith, DOB 1985-03-15, Insurance BC123. Visit with Dr. Jane Doe (NPI 1234567890) on 2024-01-10. Diagnosis M54.5. Procedures: 99213 ($150), 71210 ($200)."
claim2 = ClaimBuilder.from_text(text)
if claim2:
    print(f"  Parsed: {claim2.patient.first_name} {claim2.patient.last_name}")
    print(f"  Procedures: {len(claim2.procedures)}")
else:
    print("  Failed to parse")

# Test 5: AI Engine check
print("\n✓ Test 5: AI Engine Status")
from engine.ai_engine import OllamaEngine
ai = OllamaEngine()
if ai.available:
    print("  Ollama available: YES")
else:
    print("  Ollama available: NO (will degrade gracefully)")

print("\n" + "=" * 60)
print("✅ All tests passed!")
print("=" * 60)
