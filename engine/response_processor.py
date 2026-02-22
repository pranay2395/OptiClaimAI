"""
Response Processor - Converts raw validation results to AI-powered insights
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
import csv

class KnowledgeLoader:
    """Loads and manages knowledge base for AI context"""
    
    def __init__(self):
        self.code_sets_path = Path(__file__).parent / 'code_sets'
        self.rules_path = Path(__file__).parent / 'rules'
        self.cpt_codes = {}
        self.icd10_codes = {}
        self.hcpcs_codes = {}
        self.validation_rules = {}
        self._load_knowledge_base()
    
    def _load_knowledge_base(self):
        """Load all knowledge base files"""
        try:
            # Load CPT codes
            cpt_file = self.code_sets_path / 'cpt.csv'
            if cpt_file.exists():
                with open(cpt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('code'):
                            self.cpt_codes[row['code']] = row.get('description', row['code'])
                            if len(self.cpt_codes) > 500:  # Limit for performance
                                break
            
            # Load ICD-10 codes
            icd10_file = self.code_sets_path / 'icd10.csv'
            if icd10_file.exists():
                with open(icd10_file, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('code'):
                            self.icd10_codes[row['code']] = row.get('description', row['code'])
                            if len(self.icd10_codes) > 500:  # Limit for performance
                                break
            
            # Load HCPCS codes
            hcpcs_file = self.code_sets_path / 'hcpcs_level2.csv'
            if hcpcs_file.exists():
                with open(hcpcs_file, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('code'):
                            self.hcpcs_codes[row['code']] = row.get('description', row['code'])
                            if len(self.hcpcs_codes) > 500:  # Limit for performance
                                break
            
            # Load validation rules
            rules_file = self.rules_path / 'dhcs_rules_comprehensive.json'
            if rules_file.exists():
                with open(rules_file, 'r') as f:
                    self.validation_rules = json.load(f)
        
        except Exception as e:
            print(f"Warning: Could not load knowledge base: {e}")
    
    def get_code_description(self, code: str, code_type: str = 'cpt') -> str:
        """Get description for a medical code"""
        if code_type.lower() == 'cpt':
            return self.cpt_codes.get(code, code)
        elif code_type.lower() == 'icd10':
            return self.icd10_codes.get(code, code)
        elif code_type.lower() == 'hcpcs':
            return self.hcpcs_codes.get(code, code)
        return code
    
    def get_rule_description(self, rule_id: str) -> str:
        """Get description for a validation rule"""
        return self.validation_rules.get(rule_id, rule_id)
    
    def get_context_summary(self) -> str:
        """Get summary of loaded knowledge base for AI prompt"""
        return f"""
Available Knowledge Base Summary:
- CPT Codes: {len(self.cpt_codes)} loaded (medical procedures)
- ICD-10 Codes: {len(self.icd10_codes)} loaded (diagnoses)
- HCPCS Codes: {len(self.hcpcs_codes)} loaded (healthcare procedures)
- Validation Rules: {len(self.validation_rules)} loaded

Use this context when explaining claim validation issues.
"""


class ResponseProcessor:
    """Processes validation results for AI consumption"""
    
    def __init__(self):
        self.knowledge_loader = KnowledgeLoader()
    
    def process_validation_results(self, 
                                   validation_results: List[Dict],
                                   parsed_claims: Dict) -> Dict[str, Any]:
        """
        Convert raw validation results into structured insights
        
        Args:
            validation_results: Output from ClaimValidator.validate_all()
            parsed_claims: Parsed claim data from EDI parser
        
        Returns:
            Structured insight data ready for AI processing
        """
        
        insights = {
            'summary': self._generate_summary(validation_results, parsed_claims),
            'error_analysis': self._analyze_errors(validation_results),
            'warning_analysis': self._analyze_warnings(validation_results),
            'claim_risk_assessment': self._assess_claim_risks(validation_results),
            'recommendations': self._generate_recommendations(validation_results),
            'code_explanations': self._get_code_explanations(parsed_claims),
            'ai_prompt_context': self._build_ai_prompt_context(validation_results, parsed_claims)
        }
        
        return insights
    
    def _generate_summary(self, validation_results: List[Dict], parsed_claims: Dict) -> Dict:
        """Generate summary statistics"""
        total_claims = len(validation_results)
        claims_with_errors = len([v for v in validation_results if v.get('errors')])
        claims_with_warnings = len([v for v in validation_results if v.get('warnings')])
        total_errors = sum(len(v.get('errors', [])) for v in validation_results)
        total_warnings = sum(len(v.get('warnings', [])) for v in validation_results)
        
        return {
            'total_claims': total_claims,
            'claims_with_errors': claims_with_errors,
            'claims_with_warnings': claims_with_warnings,
            'error_rate_percent': round((claims_with_errors / total_claims * 100) if total_claims > 0 else 0, 2),
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'valid_claims': total_claims - claims_with_errors
        }
    
    def _analyze_errors(self, validation_results: List[Dict]) -> Dict:
        """Categorize and analyze errors"""
        error_categories = {}
        error_details = []
        
        for result in validation_results:
            for error in result.get('errors', []):
                error_type = error.get('type', 'Unknown')
                error_categories[error_type] = error_categories.get(error_type, 0) + 1
                
                error_details.append({
                    'claim_id': result.get('claim_id'),
                    'type': error_type,
                    'message': error.get('message'),
                    'field': error.get('field'),
                    'value': error.get('value')
                })
        
        return {
            'total_unique_error_types': len(error_categories),
            'error_frequency': error_categories,
            'top_errors': sorted(error_categories.items(), key=lambda x: x[1], reverse=True)[:5],
            'detailed_errors': error_details[:50]  # Limit to first 50
        }
    
    def _analyze_warnings(self, validation_results: List[Dict]) -> Dict:
        """Analyze warnings"""
        warning_categories = {}
        
        for result in validation_results:
            for warning in result.get('warnings', []):
                warning_type = warning.get('type', 'Unknown')
                warning_categories[warning_type] = warning_categories.get(warning_type, 0) + 1
        
        return {
            'total_unique_warning_types': len(warning_categories),
            'warning_frequency': warning_categories,
            'top_warnings': sorted(warning_categories.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def _assess_claim_risks(self, validation_results: List[Dict]) -> List[Dict]:
        """Assess rejection risk for each claim"""
        risk_assessments = []
        
        for result in validation_results:
            errors = len(result.get('errors', []))
            warnings = len(result.get('warnings', []))
            
            # Calculate risk score (0-100)
            error_score = min(errors * 15, 70)  # Max 70 from errors
            warning_score = min(warnings * 5, 30)  # Max 30 from warnings
            risk_score = error_score + warning_score
            
            if risk_score >= 70:
                risk_level = 'HIGH'
                action = 'REJECT or require significant corrections'
            elif risk_score >= 40:
                risk_level = 'MEDIUM'
                action = 'Review carefully before submission'
            else:
                risk_level = 'LOW'
                action = 'Safe to submit'
            
            risk_assessments.append({
                'claim_id': result.get('claim_id'),
                'risk_score': risk_score,
                'risk_level': risk_level,
                'recommended_action': action,
                'error_count': errors,
                'warning_count': warnings
            })
        
        return risk_assessments
    
    def _generate_recommendations(self, validation_results: List[Dict]) -> List[str]:
        """Generate actionable recommendations"""
        recs = set()
        
        for result in validation_results:
            for error in result.get('errors', []):
                error_type = error.get('type', '').lower()
                
                if 'required' in error_type:
                    recs.add("Fill all required fields before submission")
                elif 'format' in error_type:
                    recs.add("Verify data formats match X12 standards")
                elif 'npi' in error_type:
                    recs.add("Validate NPI numbers using NPPES lookup")
                elif 'date' in error_type:
                    recs.add("Ensure all dates are in correct format (YYYYMMDD)")
                elif 'amount' in error_type:
                    recs.add("Review and correct claim amounts")
                elif 'code' in error_type:
                    recs.add("Verify medical codes (CPT, ICD-10) are current and valid")
        
        return list(recs)
    
    def _get_code_explanations(self, parsed_claims: Dict) -> Dict[str, str]:
        """Get explanations for medical codes in claims"""
        explanations = {}
        
        try:
            for claim in parsed_claims.get('claims', [])[:5]:  # Limit to first 5 claims
                claim_codes = {}
                
                # Extract procedure codes
                if 'procedures' in claim:
                    for proc in claim['procedures']:
                        code = proc.get('code', '')
                        if code:
                            desc = self.knowledge_loader.get_code_description(code, 'cpt')
                            claim_codes[code] = desc
                
                # Extract diagnosis codes
                if 'diagnosis' in claim:
                    for diag in claim['diagnosis']:
                        code = diag.get('code', '')
                        if code:
                            desc = self.knowledge_loader.get_code_description(code, 'icd10')
                            claim_codes[code] = desc
                
                if claim_codes:
                    explanations[claim.get('claim_id', 'Unknown')] = claim_codes
        
        except Exception as e:
            print(f"Warning: Could not extract code explanations: {e}")
        
        return explanations
    
    def _build_ai_prompt_context(self, validation_results: List[Dict], parsed_claims: Dict) -> str:
        """Build context for AI analysis prompt"""
        
        summary = self._generate_summary(validation_results, parsed_claims)
        errors = self._analyze_errors(validation_results)
        top_errors = errors.get('top_errors', [])
        
        context = f"""
# Claims Validation Analysis Report

## Summary
- Total Claims: {summary['total_claims']}
- Valid Claims: {summary['valid_claims']}
- Claims with Errors: {summary['claims_with_errors']} ({summary['error_rate_percent']}% error rate)
- Total Issues Found: {summary['total_errors']} errors + {summary['total_warnings']} warnings

## Top Error Types (Most Frequent)
{chr(10).join([f"- {error_type}: {count} occurrences" for error_type, count in top_errors])}

## Knowledge Base Context
{self.knowledge_loader.get_context_summary()}

## Analysis Task
Please analyze these healthcare claims validation results and provide:
1. **Root Cause Analysis**: Why are these errors occurring?
2. **Pattern Recognition**: What patterns do you see in the validation failures?
3. **Rejection Risk**: Which claims are at highest risk of rejection?
4. **Corrective Actions**: Step-by-step fixes for the most common issues
5. **Compliance Insights**: HIPAA and X12 compliance implications
6. **Priority Items**: What should the billing team fix first?

Use your medical coding knowledge and healthcare regulations expertise.
"""
        
        return context


def get_processor() -> ResponseProcessor:
    """Get singleton instance of response processor"""
    if not hasattr(get_processor, '_instance'):
        get_processor._instance = ResponseProcessor()
    return get_processor._instance


if __name__ == "__main__":
    # Test the processor
    processor = ResponseProcessor()
    
    # Sample test data
    test_results = [
        {
            'claim_id': 'CLM001',
            'errors': [
                {'type': 'missing_required_field', 'message': 'NPI is required', 'field': 'provider_npi'},
                {'type': 'invalid_format', 'message': 'Date must be YYYYMMDD', 'field': 'service_date'}
            ],
            'warnings': [
                {'type': 'suspicious_amount', 'message': 'Amount seems high for procedure'},
                {'type': 'old_code', 'message': 'Using deprecated ICD-10 code'}
            ]
        },
        {
            'claim_id': 'CLM002',
            'errors': [],
            'warnings': [
                {'type': 'unusual_frequency', 'message': 'Procedure done very frequently'}
            ]
        }
    ]
    
    test_claims = {
        'claims': [
            {
                'claim_id': 'CLM001',
                'procedures': [{'code': '99213'}],
                'diagnosis': [{'code': 'J00'}]
            }
        ]
    }
    
    insights = processor.process_validation_results(test_results, test_claims)
    print(json.dumps(insights, indent=2, default=str))
