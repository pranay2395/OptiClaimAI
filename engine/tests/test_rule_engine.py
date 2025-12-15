import json
from pathlib import Path
import sys

# ensure src is importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT.joinpath('src')))

from src.parser import parse_837
from src.rule_engine import load_rules, evaluate_rules


def test_professional_sample_finds_clm_and_diag():
    sample = ROOT.joinpath('samples','sample_837_prof.txt').read_text(encoding='utf-8')
    parsed = parse_837(sample)
    rules = load_rules(str(ROOT.joinpath('rules','dhcs_rules_v2.json')))
    findings = evaluate_rules(parsed, rules)
    # Expect at least one finding (e.g., txn_is professional or diagnosis present)
    assert isinstance(findings, list)
    assert any(f.get('id') for f in findings)
