"""
Claims Analytics Engine
Generates analytics and insights from parsed claims
"""

from typing import Dict, List
import statistics

class ClaimsAnalytics:
    """Analytics engine for claims data"""

    def __init__(self):
        self.parsed_data = None
        self.validation_results = None

    def analyze(self, parsed_data: Dict, validation_results: List[Dict]) -> Dict:
        """
        Generate comprehensive analytics from claims data

        Args:
            parsed_data: Parsed claims from EDI file
            validation_results: Validation results for claims

        Returns:
            Dictionary containing analytics data
        """
        self.parsed_data = parsed_data
        self.validation_results = validation_results

        claims = parsed_data.get('claims', [])

        if not claims:
            return self._empty_analytics()

        analytics = {
            # Basic metrics
            'total_claims': len(claims),
            'total_claim_amount': self._calculate_total_amount(claims),
            'average_claim_amount': self._calculate_average_amount(claims),
            'min_claim_amount': self._calculate_min_amount(claims),
            'max_claim_amount': self._calculate_max_amount(claims),

            # Claim details
            'claim_ids': [c.get('claim_id', f'Claim_{i}') for i, c in enumerate(claims)],
            'claim_amounts': [c.get('claim_amount', 0) for c in claims],

            # Service analysis
            'service_types': self._analyze_service_types(claims),
            'procedure_codes': self._analyze_procedure_codes(claims),

            # Diagnosis analysis
            'diagnosis_codes': self._analyze_diagnoses(claims),

            # Denial risk
            'denial_risks': self._calculate_denial_risks(claims, validation_results),
            'high_denial_risk_count': 0,  # Will be calculated

            # Provider analysis
            'providers': self._analyze_providers(claims),

            # Date analysis
            'date_range': self._analyze_dates(claims)
        }

        # Count high risk claims
        analytics['high_denial_risk_count'] = sum(
            1 for risk in analytics['denial_risks']
            if risk.get('risk_level') == 'High'
        )

        return analytics

    def _empty_analytics(self) -> Dict:
        """Return empty analytics structure"""
        return {
            'total_claims': 0,
            'total_claim_amount': 0.0,
            'average_claim_amount': 0.0,
            'min_claim_amount': 0.0,
            'max_claim_amount': 0.0,
            'claim_ids': [],
            'claim_amounts': [],
            'service_types': {},
            'procedure_codes': {},
            'diagnosis_codes': {},
            'denial_risks': [],
            'high_denial_risk_count': 0,
            'providers': {},
            'date_range': {'start': None, 'end': None}
        }

    def _calculate_total_amount(self, claims: List[Dict]) -> float:
        """Calculate total claim amount"""
        return sum(c.get('claim_amount', 0) for c in claims)

    def _calculate_average_amount(self, claims: List[Dict]) -> float:
        """Calculate average claim amount"""
        amounts = [c.get('claim_amount', 0) for c in claims if c.get('claim_amount', 0) > 0]
        return statistics.mean(amounts) if amounts else 0.0

    def _calculate_min_amount(self, claims: List[Dict]) -> float:
        """Calculate minimum claim amount"""
        amounts = [c.get('claim_amount', 0) for c in claims if c.get('claim_amount', 0) > 0]
        return min(amounts) if amounts else 0.0

    def _calculate_max_amount(self, claims: List[Dict]) -> float:
        """Calculate maximum claim amount"""
        amounts = [c.get('claim_amount', 0) for c in claims if c.get('claim_amount', 0) > 0]
        return max(amounts) if amounts else 0.0

    def _analyze_service_types(self, claims: List[Dict]) -> Dict:
        """Analyze service types from claims"""
        service_types = {}
        for claim in claims:
            service_lines = claim.get('service_lines', [])
            for line in service_lines:
                # Extract service type from procedure code or description
                proc_code = line.get('procedure_code', '')
                if proc_code:
                    # Categorize by first character or common patterns
                    if proc_code.startswith('99'):
                        svc_type = 'Evaluation & Management'
                    elif proc_code.startswith('7'):
                        svc_type = 'Radiology'
                    elif proc_code.startswith('8'):
                        svc_type = 'Pathology'
                    elif proc_code.startswith('9'):
                        svc_type = 'Medicine'
                    else:
                        svc_type = 'Other'

                    service_types[svc_type] = service_types.get(svc_type, 0) + 1
        return service_types

    def _analyze_procedure_codes(self, claims: List[Dict]) -> Dict:
        """Analyze procedure codes"""
        proc_codes = {}
        for claim in claims:
            service_lines = claim.get('service_lines', [])
            for line in service_lines:
                code = line.get('procedure_code', '')
                if code:
                    proc_codes[code] = proc_codes.get(code, 0) + 1
        return proc_codes

    def _analyze_diagnoses(self, claims: List[Dict]) -> Dict:
        """Analyze diagnosis codes"""
        diagnoses = {}
        for claim in claims:
            diag_codes = claim.get('diagnoses', [])
            for diag in diag_codes:
                code = diag.get('code', '')
                if code:
                    diagnoses[code] = diagnoses.get(code, 0) + 1
        return diagnoses

    def _calculate_denial_risks(self, claims: List[Dict], validation_results: List[Dict]) -> List[Dict]:
        """Calculate denial risks based on validation results"""
        denial_risks = []

        for i, claim in enumerate(claims):
            claim_id = claim.get('claim_id', f'Claim_{i+1}')
            validation_result = validation_results[i] if i < len(validation_results) else {}

            errors = validation_result.get('errors', [])
            warnings = validation_result.get('warnings', [])

            # Calculate risk score based on errors and warnings
            risk_score = len(errors) * 10 + len(warnings) * 2

            # Determine risk level
            if risk_score >= 20:
                risk_level = 'High'
            elif risk_score >= 10:
                risk_level = 'Medium'
            else:
                risk_level = 'Low'

            # Compile risk factors
            risk_factors = []
            if errors:
                risk_factors.extend([f"Error: {e}" for e in errors[:3]])  # Top 3 errors
            if warnings:
                risk_factors.extend([f"Warning: {w}" for w in warnings[:2]])  # Top 2 warnings

            denial_risks.append({
                'claim_id': claim_id,
                'risk_level': risk_level,
                'risk_score': risk_score,
                'risk_factors': risk_factors,
                'error_count': len(errors),
                'warning_count': len(warnings)
            })

        return denial_risks

    def _analyze_providers(self, claims: List[Dict]) -> Dict:
        """Analyze providers from claims"""
        providers = {}
        for claim in claims:
            provider = claim.get('provider', {})
            provider_id = provider.get('id_number', 'Unknown')
            if provider_id != 'Unknown':
                providers[provider_id] = providers.get(provider_id, 0) + 1
        return providers

    def _analyze_dates(self, claims: List[Dict]) -> Dict:
        """Analyze date ranges from claims"""
        dates = []
        for claim in claims:
            service_date = claim.get('service_date')
            if service_date:
                try:
                    # Assume MMDDYY format
                    dates.append(service_date)
                except:
                    pass

        if dates:
            return {
                'start': min(dates),
                'end': max(dates),
                'count': len(dates)
            }
        return {'start': None, 'end': None, 'count': 0}
