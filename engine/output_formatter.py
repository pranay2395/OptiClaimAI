"""
Format validation results and claim data for human consumption
"""

from typing import Dict, List
from model.claim_schema import Claim


class OutputFormatter:
    """Format validation results for human consumption"""
    
    @staticmethod
    def format_claim_summary(claim: Claim) -> str:
        """Create human-readable claim summary"""
        diagnoses_str = ', '.join(d.code for d in claim.diagnoses) if claim.diagnoses else 'None'
        procedures_str = ', '.join(p.code for p in claim.procedures) if claim.procedures else 'None'
        
        return f"""**Patient:** {claim.patient.first_name} {claim.patient.last_name} (DOB: {claim.patient.date_of_birth})
**Insurance ID:** {claim.patient.insurance_id or 'Not provided'}
**Provider:** {claim.provider.first_name} {claim.provider.last_name} (NPI: {claim.provider.npi})
**Service Date:** {claim.service_date or 'Not provided'}
**Total Charge:** ${claim.claim_amount:,.2f}
**Diagnoses:** {diagnoses_str}
**Procedures:** {procedures_str} ({len(claim.procedures)} procedure(s))"""
    
    @staticmethod
    def format_issues_for_display(issues: List[Dict]) -> Dict[str, List[Dict]]:
        """Group issues by severity for organized display"""
        grouped = {
            'CRITICAL': [],
            'HIGH': [],
            'MEDIUM': [],
            'LOW': [],
            'INFO': [],
        }
        
        for issue in issues:
            # Extract severity key from formatted string like "🔴 CRITICAL"
            severity_str = issue.get('severity', 'INFO')
            severity_key = severity_str.split()[-1] if ' ' in severity_str else severity_str
            
            if severity_key in grouped:
                grouped[severity_key].append(issue)
        
        return grouped
    
    @staticmethod
    def format_fix_guidance(issue: Dict, ai_explanation: str = None) -> str:
        """Format fix guidance for a single issue"""
        guidance = f"**Issue:** {issue.get('message', 'Unknown issue')}"
        
        if issue.get('field'):
            guidance += f"\n**Field:** {issue['field']}"
        
        if ai_explanation:
            guidance += f"\n\n**AI Guidance:**\n{ai_explanation}"
        
        return guidance
    
    @staticmethod
    def get_risk_color(risk_level: str) -> str:
        """Get emoji color code for risk level"""
        mapping = {
            'VERY HIGH': '🔴',
            'HIGH': '🟠',
            'MEDIUM': '🟡',
            'LOW': '🟢',
        }
        return mapping.get(risk_level, '⚪')
    
    @staticmethod
    def format_denial_risk(risk_score: int, risk_level: str, issue_count: int) -> Dict:
        """Format denial risk information"""
        if risk_score >= 70:
            risk_level = "VERY HIGH"
            recommendation = "⛔ Do NOT submit without fixes"
        elif risk_score >= 50:
            risk_level = "HIGH"
            recommendation = "⚠️ Likely to be denied - fix issues first"
        elif risk_score >= 30:
            risk_level = "MEDIUM"
            recommendation = "⚠️ May be denied - consider fixes"
        else:
            risk_level = "LOW"
            recommendation = "✅ Good to submit, but review outstanding issues"
        
        return {
            'score': risk_score,
            'level': risk_level,
            'color': OutputFormatter.get_risk_color(risk_level),
            'recommendation': recommendation,
            'issue_count': issue_count,
        }
