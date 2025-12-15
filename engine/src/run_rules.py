"""Command-line runner: parse a sample 837 and run rules against it.
Usage: python run_rules.py ../samples/sample_837_prof.txt
"""
import sys
import json
from pathlib import Path

# allow running from engine/src directory or project root
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE.joinpath('src')))

# import modules directly from the added src path
import parser
import rule_engine


def main():
    if len(sys.argv) < 2:
        print('Usage: python run_rules.py ../samples/sample_837_prof.txt')
        sys.exit(2)
    sample_path = Path(sys.argv[1])
    if not sample_path.exists():
        print('Sample file not found:', sample_path)
        sys.exit(2)
    raw = sample_path.read_text(encoding='utf-8')
    parsed = parser.parse_837(raw)
    rules_path = BASE.joinpath('rules','dhcs_rules_v2.json')
    rules = rule_engine.load_rules(str(rules_path))
    findings = rule_engine.evaluate_rules(parsed, rules)
    out = {'sample': str(sample_path), 'parsed_summary': {'transaction_type': parsed.get('transaction_type'), 'claim_count': len(parsed.get('claims', []))}, 'findings': findings}
    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    main()
