#!/usr/bin/env python
"""Quick test of consolidated OptiClaimAI modules."""
from engine.parser import parse_837
from engine.model import predict_denial
from pathlib import Path

sample = Path('data/sample_837/sample1.837')
if sample.exists():
    raw = sample.read_text()
    parsed = parse_837(raw)
    result = predict_denial(raw, parsed)
    
    print(f"✓ Claims parsed: {len(parsed.get('claims', []))}")
    print(f"✓ Transaction type: {parsed.get('transaction_type')}")
    print(f"✓ Issues found: {len(result.get('issues', []))}")
    for issue in result.get('issues', [])[:3]:
        print(f"  - {issue.get('issue_type')}: {issue.get('why_failed')}")
    print("\n✅ Consolidation successful!")
else:
    print("Sample file not found")
