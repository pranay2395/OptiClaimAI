"""
Enhanced Analytics - AI-powered claim insights with visualizations
"""

import json
from typing import Dict, List, Any, Tuple
import pandas as pd
from pathlib import Path

from engine.response_processor import ResponseProcessor
from engine.ollama_wrapper import get_ollama


class EnhancedAnalytics:
    """Advanced analytics with AI-powered insights"""
    
    def __init__(self):
        self.response_processor = ResponseProcessor()
        self.ollama = get_ollama()
    
    def analyze_claims(self, validation_results: List[Dict], parsed_claims: Dict) -> Dict[str, Any]:
        """
        Comprehensive claim analysis with AI insights
        
        Returns:
            Dictionary with insights, metrics, and recommendations
        """
        
        # Process validation results
        insights = self.response_processor.process_validation_results(
            validation_results, 
            parsed_claims
        )
        
        # Get AI-powered analysis
        if self.ollama.is_available():
            ai_analysis = self._get_ai_analysis(insights)
        else:
            ai_analysis = self._get_fallback_analysis(insights)
        
        # Generate visualizations data
        viz_data = self._prepare_visualization_data(insights, validation_results)
        
        return {
            'summary': insights['summary'],
            'error_analysis': insights['error_analysis'],
            'warning_analysis': insights['warning_analysis'],
            'risk_assessment': insights['claim_risk_assessment'],
            'recommendations': insights['recommendations'],
            'ai_insights': ai_analysis,
            'visualizations': viz_data,
            'code_explanations': insights['code_explanations']
        }
    
    def _get_ai_analysis(self, insights: Dict) -> Dict[str, str]:
        """Get AI-powered analysis from Ollama"""
        
        try:
            prompt = insights['ai_prompt_context']
            
            response = self.ollama.generate(
                prompt=prompt,
                model='llama3.1',  # Default model
                temperature=0.7
            )
            
            if response:
                return {
                    'full_analysis': response,
                    'source': 'AI Analysis (Ollama)',
                    'confidence': 'High' if len(response) > 500 else 'Medium'
                }
        
        except Exception as e:
            print(f"Error getting AI analysis: {e}")
        
        return self._get_fallback_analysis(insights)
    
    def _get_fallback_analysis(self, insights: Dict) -> Dict[str, str]:
        """Fallback analysis when AI is not available"""
        
        summary = insights['summary']
        errors = insights['error_analysis']
        
        analysis = f"""
CLAIMS VALIDATION ANALYSIS REPORT

OVERVIEW:
- Valid Claims: {summary['valid_claims']} out of {summary['total_claims']}
- Error Rejection Rate: {summary['error_rate_percent']}%
- Total Issues: {summary['total_errors']} errors, {summary['total_warnings']} warnings

TOP ISSUES:
"""
        
        for error_type, count in errors['top_errors']:
            analysis += f"\n- {error_type}: {count} occurrences"
        
        analysis += f"""

RECOMMENDED ACTIONS:
1. Review the {errors.get('total_unique_error_types', 0)} unique error types identified
2. Address the top {len(errors.get('top_errors', []))} most frequent issues first
3. Implement validation checks for missing required fields
4. Verify all medical codes against current standards
5. Test claims before final submission

COMPLIANCE NOTES:
- All claims must comply with X12 837P EDI standards
- NPI numbers must be validated through NPPES lookup
- Date formats must be YYYYMMDD per X12 standards
- Medical codes should use current CPT, ICD-10, or HCPCS codes
"""
        
        return {
            'full_analysis': analysis,
            'source': 'Rule-Based Analysis',
            'confidence': 'Medium'
        }
    
    def _prepare_visualization_data(self, insights: Dict, validation_results: List[Dict]) -> Dict:
        """Prepare data for visualizations"""
        
        viz_data = {}
        
        # Error frequency data
        error_freq = insights['error_analysis']['error_frequency']
        if error_freq:
            viz_data['error_distribution'] = {
                'labels': list(error_freq.keys()),
                'values': list(error_freq.values()),
                'type': 'bar'
            }
        
        # Warning frequency data
        warning_freq = insights['warning_analysis']['warning_frequency']
        if warning_freq:
            viz_data['warning_distribution'] = {
                'labels': list(warning_freq.keys()),
                'values': list(warning_freq.values()),
                'type': 'bar'
            }
        
        # Risk level distribution
        risk_assessments = insights['claim_risk_assessment']
        risk_levels = {}
        for assessment in risk_assessments:
            level = assessment['risk_level']
            risk_levels[level] = risk_levels.get(level, 0) + 1
        
        if risk_levels:
            viz_data['risk_distribution'] = {
                'labels': list(risk_levels.keys()),
                'values': list(risk_levels.values()),
                'type': 'pie',
                'colors': ['#d32f2f', '#f57c00', '#388e3c']  # Red, Orange, Green
            }
        
        # Top errors over time (simulated)
        top_errors = insights['error_analysis']['top_errors']
        if top_errors:
            viz_data['top_errors_chart'] = {
                'labels': [e[0] for e in top_errors],
                'values': [e[1] for e in top_errors],
                'type': 'horizontal_bar'
            }
        
        # Claim status summary
        summary = insights['summary']
        viz_data['claim_status'] = {
            'valid': summary['valid_claims'],
            'errors': summary['claims_with_errors'],
            'warnings': summary['claims_with_warnings'],
            'total': summary['total_claims']
        }
        
        return viz_data
    
    def get_claim_explanation(self, claim_id: str, parsed_claim: Dict) -> str:
        """Get AI-powered explanation for a specific claim"""
        
        if not self.ollama.is_available():
            return "AI service not available. Please check Ollama connection."
        
        try:
            prompt = f"""Explain this healthcare claim in simple terms:

Claim ID: {claim_id}
Data: {json.dumps(parsed_claim, indent=2)}

Provide:
1. What procedure/service is being billed?
2. Who is the service provider?
3. What insurance is being billed?
4. Any concerns or red flags?
5. Expected reimbursement status"""
            
            response = self.ollama.generate(
                prompt=prompt,
                model='llama3.1',
                temperature=0.7
            )
            
            return response if response else "Could not generate explanation"
        
        except Exception as e:
            return f"Error generating explanation: {e}"
    
    def get_rejection_analysis(self, validation_errors: List[Dict]) -> str:
        """AI-powered analysis of why claims might be rejected"""
        
        if not self.ollama.is_available():
            return "AI service not available. Please check Ollama connection."
        
        try:
            prompt = f"""Analyze these claim validation errors and explain why the claim will likely be rejected:

Errors: {json.dumps(validation_errors, indent=2)}

For each error:
1. Explain the specific requirement that's violated
2. Why payers care about this requirement
3. How to fix it
4. Estimated rejection rate if not fixed"""
            
            response = self.ollama.generate(
                prompt=prompt,
                model='llama3.1',
                temperature=0.7
            )
            
            return response if response else "Could not generate analysis"
        
        except Exception as e:
            return f"Error generating analysis: {e}"
    
    def generate_recommendations(self, insights: Dict) -> List[Dict]:
        """Generate prioritized recommendations"""
        
        recommendations = []
        summary = insights['summary']
        errors = insights['error_analysis']
        
        # Priority 1: Critical errors requiring immediate attention
        if summary['error_rate_percent'] > 50:
            recommendations.append({
                'priority': 1,
                'severity': 'CRITICAL',
                'title': 'High Error Rate Detected',
                'description': f"{summary['error_rate_percent']}% of claims have errors. Review validation settings.",
                'action': 'Review all validation errors before submission'
            })
        
        # Priority 2: Top error types
        for idx, (error_type, count) in enumerate(errors['top_errors'][:3]):
            recommendations.append({
                'priority': 2,
                'severity': 'HIGH',
                'title': f"Address {error_type}",
                'description': f"This error occurs {count} times. Implement fixes across claims.",
                'action': f"Fix {error_type} in all affected claims"
            })
        
        # Priority 3: General improvements
        if summary['total_warnings'] > 0:
            recommendations.append({
                'priority': 3,
                'severity': 'MEDIUM',
                'title': 'Reduce Warnings',
                'description': f"{summary['total_warnings']} warnings may cause processing delays.",
                'action': 'Review and address non-critical warnings'
            })
        
        return recommendations
    
    def export_report(self, analysis: Dict, format_type: str = 'json') -> str:
        """Export analysis report in various formats"""
        
        if format_type == 'json':
            return json.dumps(analysis, indent=2, default=str)
        
        elif format_type == 'markdown':
            return self._format_markdown_report(analysis)
        
        elif format_type == 'csv':
            return self._format_csv_report(analysis)
        
        else:
            return "Unsupported format"
    
    def _format_markdown_report(self, analysis: Dict) -> str:
        """Format analysis as markdown"""
        
        summary = analysis['summary']
        risks = analysis['risk_assessment']
        
        report = f"""# Claims Validation Report

## Executive Summary
- **Total Claims Analyzed**: {summary['total_claims']}
- **Valid Claims**: {summary['valid_claims']}
- **Claims with Errors**: {summary['claims_with_errors']}
- **Error Rate**: {summary['error_rate_percent']}%
- **Total Errors**: {summary['total_errors']}
- **Total Warnings**: {summary['total_warnings']}

## Risk Assessment

| Claim ID | Error Count | Warning Count | Risk Level | Action |
|----------|-------------|---------------|-----------|--------|
"""
        
        for risk in risks[:10]:  # Show top 10
            report += f"| {risk['claim_id']} | {risk['error_count']} | {risk['warning_count']} | {risk['risk_level']} | {risk['recommended_action']} |\n"
        
        report += f"""

## Recommendations
"""
        
        for rec in analysis['recommendations'][:5]:
            report += f"- **{rec}**\n"
        
        report += f"""

## AI Analysis

{analysis.get('ai_insights', {}).get('full_analysis', 'No AI analysis available')}

---
*Generated by OptiClaimAI v5*
"""
        
        return report
    
    def _format_csv_report(self, analysis: Dict) -> str:
        """Format analysis as CSV"""
        
        risks = analysis['risk_assessment']
        lines = ['Claim ID,Error Count,Warning Count,Risk Level,Action']
        
        for risk in risks:
            lines.append(
                f"{risk['claim_id']},{risk['error_count']},{risk['warning_count']},"
                f"{risk['risk_level']},{risk['recommended_action']}"
            )
        
        return '\n'.join(lines)


def get_analytics() -> EnhancedAnalytics:
    """Get singleton instance of analytics"""
    if not hasattr(get_analytics, '_instance'):
        get_analytics._instance = EnhancedAnalytics()
    return get_analytics._instance


if __name__ == "__main__":
    # Test the analytics
    analytics = EnhancedAnalytics()
    
    # Sample data
    test_results = [
        {
            'claim_id': 'CLM001',
            'errors': [
                {'type': 'missing_npi', 'message': 'NPI required'},
                {'type': 'invalid_date', 'message': 'Date format wrong'}
            ],
            'warnings': []
        }
    ]
    
    test_claims = {'claims': []}
    
    analysis = analytics.analyze_claims(test_results, test_claims)
    print(json.dumps(analysis, indent=2, default=str))
