"""Test v3 validation logic"""
from engine.validate_cms1500 import validate_cms1500, build_cms1500_object
from datetime import date

# Test 1: Empty data
is_valid, errors, warnings = validate_cms1500({})
print("Test 1: Empty form")
print(f"  Valid: {is_valid}, Errors: {len(errors)}")
assert not is_valid
assert len(errors) > 0
print("  ✅ Passed")

# Test 2: Minimal valid data
data = {
    'subscriber_name': 'John Doe',
    'subscriber_dob': date(1950, 1, 1),
    'subscriber_gender': 'M',
    'subscriber_id': 'ID123',
    'patient_first': 'John',
    'patient_last': 'Doe',
    'patient_dob': date(1950, 1, 1),
    'patient_gender': 'M',
    'relationship': 'Self',
    'provider_npi': '1234567890',
    'provider_first': 'Jane',
    'provider_last': 'Smith',
    'federal_tax_id': '12-3456789',
    'tax_id_type': 'EIN',
    'diagnoses': [{'code': 'M79.3', 'primary': True, 'sequence_number': 1}],
    'service_lines': [
        {
            'line_number': 1,
            'from_date': date(2026, 1, 10),
            'to_date': date(2026, 1, 10),
            'place_of_service': '11',
            'procedure_code': '99213',
            'charges': 100.0,
            'units': 1,
            'diagnosis_pointer': '1',
        }
    ]
}

is_valid, errors, warnings = validate_cms1500(data)
print("\nTest 2: Minimal valid data")
print(f"  Valid: {is_valid}, Errors: {len(errors)}, Warnings: {len(warnings)}")
assert is_valid
assert len(errors) == 0
print("  ✅ Passed")

# Test 3: Build CMS1500 object
print("\nTest 3: Build CMS1500 object from valid data")
cms1500 = build_cms1500_object(data)
assert cms1500 is not None
assert cms1500.subscriber_info.name == 'John Doe'
assert len(cms1500.service_lines) == 1
print("  ✅ Passed")

print("\n✅ All validation tests passed")
