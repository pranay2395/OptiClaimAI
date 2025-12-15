Engine v2 — Quick start

Directory layout:

engine/
  src/
    parser.py
    rule_engine.py
    run_rules.py
  rules/
    dhcs_rules_v2.json
  code_sets/
    cpt.csv
    icd10.csv
    npi_enrollment.csv
  samples/
    sample_837_prof.txt
    sample_837_inst.txt
  tests/
    test_rule_engine.py

Quick run (from repo root):

# Run rule runner against professional sample
python engine/src/run_rules.py engine/samples/sample_837_prof.txt

# Run rule runner against institutional sample
python engine/src/run_rules.py engine/samples/sample_837_inst.txt

# Run tests (ensure pytest installed)
pytest -q engine/tests

Notes:
- This is a lightweight programmatic rule engine for local testing and experimentation.
- The parsers and rule handlers are intentionally simple and intended for extension.
