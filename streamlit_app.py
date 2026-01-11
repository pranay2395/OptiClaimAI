import streamlit as st
import pandas as pd
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from engine.parser import EDI837Parser
from engine.validator import ClaimValidator
from engine.analytics import ClaimsAnalytics

# Page configuration
st.set_page_config(
    page_title="OptiClaimAI - 837 Claims Validator",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    """Initialize all session state variables"""
    if 'parsed_claims' not in st.session_state:
        st.session_state.parsed_claims = None
    if 'validation_results' not in st.session_state:
        st.session_state.validation_results = None
    if 'analytics_data' not in st.session_state:
        st.session_state.analytics_data = None
    if 'file_uploaded' not in st.session_state:
        st.session_state.file_uploaded = False
    if 'file_name' not in st.session_state:
        st.session_state.file_name = None
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False

def parse_uploaded_file(file_content: str, file_name: str) -> Optional[Dict]:
    """Parse uploaded EDI 837 file"""
    try:
        with st.spinner('🔄 Parsing EDI 837 file...'):
            parser = EDI837Parser()
            parsed_data = parser.parse(file_content)

            if not parsed_data or 'claims' not in parsed_data:
                st.error("❌ No claims found in file")
                return None

            st.success(f"✅ Successfully parsed {len(parsed_data['claims'])} claim(s)")
            return parsed_data

    except Exception as e:
        st.error(f"❌ Parsing Error: {str(e)}")
        return None

def validate_claims(parsed_data: Dict) -> Optional[List[Dict]]:
    """Validate parsed claims"""
    try:
        with st.spinner('🔍 Validating claims...'):
            validator = ClaimValidator()
            validation_results = validator.validate_all(parsed_data)

            total_errors = sum(len(result.get('errors', [])) for result in validation_results)
            total_warnings = sum(len(result.get('warnings', [])) for result in validation_results)

            if total_errors == 0:
                st.success(f"✅ All claims validated successfully ({total_warnings} warnings)")
            else:
                st.warning(f"⚠️ Validation complete: {total_errors} errors, {total_warnings} warnings")

            return validation_results

    except Exception as e:
        st.error(f"❌ Validation Error: {str(e)}")
        return None

def generate_analytics(parsed_data: Dict, validation_results: List[Dict]) -> Optional[Dict]:
    """Generate analytics from claims data"""
    try:
        with st.spinner('📊 Generating analytics...'):
            analytics_engine = ClaimsAnalytics()
            analytics_data = analytics_engine.analyze(parsed_data, validation_results)

            if analytics_data:
                st.success("✅ Analytics generated successfully")

            return analytics_data

    except Exception as e:
        st.error(f"❌ Analytics Error: {str(e)}")
        return None

def render_header():
    """Render application header"""
    st.markdown('<div class="main-header">🏥 OptiClaimAI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-Powered Pre-Submission Claims Validation for 837 EDI Files</div>', unsafe_allow_html=True)

    # PHI Warning
    st.markdown("""
        <div class="warning-box">
            <strong>⚠️ IMPORTANT:</strong>
            This is a demo application.
            Do NOT upload files containing real Protected Health Information (PHI).
            Use synthetic or de-identified data only.
        </div>
    """, unsafe_allow_html=True)

def render_upload_tab():
    """Render file upload tab"""
    st.header("📁 File Upload")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Upload 837 EDI File",
            type=['txt', 'edi', '837'],
            help="Upload a standard 837 Professional (837P) EDI file"
        )

        if uploaded_file is not None:
            file_content = uploaded_file.read().decode('utf-8')

            if st.button("🚀 Process File", type="primary", use_container_width=True):
                # Reset processing state
                st.session_state.processing_complete = False

                # Step 1: Parse
                parsed_data = parse_uploaded_file(file_content, uploaded_file.name)
                if parsed_data is None:
                    return

                st.session_state.parsed_claims = parsed_data
                st.session_state.file_name = uploaded_file.name
                st.session_state.file_uploaded = True

                # Step 2: Validate
                validation_results = validate_claims(parsed_data)
                if validation_results is None:
                    return

                st.session_state.validation_results = validation_results

                # Step 3: Generate Analytics
                analytics_data = generate_analytics(parsed_data, validation_results)
                if analytics_data is None:
                    return

                st.session_state.analytics_data = analytics_data
                st.session_state.processing_complete = True

                # Success message
                st.markdown("""
                    <div class="success-box">
                        <h4>✅ Processing Complete!</h4>
                        <p>Your file has been successfully processed.
                        Navigate to the <strong>Validation</strong> or <strong>Analytics</strong>
                        tabs to view results.</p>
                    </div>
                """, unsafe_allow_html=True)

                st.balloons()

    with col2:
        st.info("""
            **Supported Format:**
            - 837 Professional (837P)
            - Standard EDI X12 format
            - Version 5010

            **Sample Files:**
            Check the `data/sample_837/` folder for examples
        """)

    # Show current file status
    if st.session_state.file_uploaded:
        st.divider()
        st.subheader("📄 Current File Status")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File Name", st.session_state.file_name or "None")
        with col2:
            claims_count = len(st.session_state.parsed_claims.get('claims', [])) if st.session_state.parsed_claims else 0
            st.metric("Claims Found", claims_count)
        with col3:
            status = "✅ Processed" if st.session_state.processing_complete else "⏳ Pending"
            st.metric("Status", status)

def render_validation_tab():
    """Render validation results tab"""
    st.header("🔍 Validation Results")

    if not st.session_state.file_uploaded or st.session_state.validation_results is None:
        st.info("👆 Please upload and process a file first in the **Upload** tab")
        return

    validation_results = st.session_state.validation_results

    # Summary metrics
    st.subheader("📊 Validation Summary")
    col1, col2, col3, col4 = st.columns(4)

    total_claims = len(validation_results)
    total_errors = sum(len(r.get('errors', [])) for r in validation_results)
    total_warnings = sum(len(r.get('warnings', [])) for r in validation_results)
    clean_claims = sum(1 for r in validation_results if len(r.get('errors', [])) == 0)

    with col1:
        st.metric("Total Claims", total_claims)
    with col2:
        st.metric("Errors", total_errors, delta=None if total_errors == 0 else "Issues Found", delta_color="inverse")
    with col3:
        st.metric("Warnings", total_warnings)
    with col4:
        st.metric("Clean Claims", clean_claims)

    st.divider()

    # Detailed results per claim
    st.subheader("🔎 Detailed Results")

    for idx, result in enumerate(validation_results, 1):
        claim_id = result.get('claim_id', f'Claim {idx}')
        errors = result.get('errors', [])
        warnings = result.get('warnings', [])

        # Claim header
        status_icon = "✅" if len(errors) == 0 else "❌"
        with st.expander(f"{status_icon} {claim_id} - {len(errors)} errors, {len(warnings)} warnings"):

            if len(errors) == 0 and len(warnings) == 0:
                st.success("✅ This claim passed all validation checks")

            # Errors
            if errors:
                st.markdown("**🔴 Errors:**")
                for error in errors:
                    st.error(f"• {error}")

            # Warnings
            if warnings:
                st.markdown("**🟡 Warnings:**")
                for warning in warnings:
                    st.warning(f"• {warning}")

            # Claim details
            if st.checkbox(f"Show claim details for {claim_id}", key=f"details_{idx}"):
                st.json(result.get('claim_data', {}))

def render_analytics_tab():
    """Render analytics tab - THE KEY FIX"""
    st.header("📊 Claims Analytics")

    # CRITICAL FIX: Check for analytics data in session state
    if not st.session_state.file_uploaded or st.session_state.analytics_data is None:
        st.info("👆 Please upload and process a file first in the **Upload** tab")

        # Show sample data notice
        st.warning("""
            **Note:** No file has been processed yet.
            Upload a file in the Upload tab to see analytics for your claims.
        """)
        return

    # CRITICAL FIX: Use session state data, not default values
    analytics = st.session_state.analytics_data

    # Overview metrics
    st.subheader("📈 Overview Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Claims",
            analytics.get('total_claims', 0),
            help="Total number of claims in uploaded file"
        )
    with col2:
        total_amount = analytics.get('total_claim_amount', 0)
        st.metric(
            "Total Amount",
            f"${total_amount:,.2f}",
            help="Sum of all claim amounts"
        )
    with col3:
        avg_amount = analytics.get('average_claim_amount', 0)
        st.metric(
            "Average Amount",
            f"${avg_amount:,.2f}",
            help="Average claim amount"
        )
    with col4:
        denial_risk = analytics.get('high_denial_risk_count', 0)
        pct = (denial_risk / analytics.get('total_claims', 1)) * 100 if analytics.get('total_claims', 0) > 0 else 0
        st.metric(
            "High Denial Risk",
            denial_risk,
            delta=f"{pct:.1f}%",
            delta_color="inverse"
        )

    st.divider()

    # Distribution charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💰 Claim Amount Distribution")
        if 'claim_amounts' in analytics and len(analytics['claim_amounts']) > 0:
            df_amounts = pd.DataFrame({
                'Claim ID': analytics['claim_ids'],
                'Amount': analytics['claim_amounts']
            })
            st.bar_chart(df_amounts.set_index('Claim ID'))
        else:
            st.info("No claim amount data available")

    with col2:
        st.subheader("🏥 Service Types")
        if 'service_types' in analytics and analytics['service_types']:
            df_services = pd.DataFrame.from_dict(
                analytics['service_types'],
                orient='index',
                columns=['Count']
            )
            st.bar_chart(df_services)
        else:
            st.info("No service type data available")

    st.divider()

    # Denial risk analysis
    st.subheader("⚠️ Denial Risk Analysis")

    if 'denial_risks' in analytics and len(analytics['denial_risks']) > 0:
        df_risks = pd.DataFrame(analytics['denial_risks'])

        # Color code by risk level
        def risk_color(risk):
            if risk == 'High': return '🔴'
            elif risk == 'Medium': return '🟡'
            else: return '🟢'

        df_risks['Status'] = df_risks['risk_level'].apply(risk_color)

        st.dataframe(
            df_risks[['Status', 'claim_id', 'risk_level', 'risk_factors', 'risk_score']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✅ No high-risk claims identified")

    # Download results
    st.divider()
    st.subheader("📥 Export Results")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Download Analytics Report (CSV)", use_container_width=True):
            # Create CSV export
            csv_data = pd.DataFrame(analytics.get('denial_risks', []))
            st.download_button(
                "Download CSV",
                csv_data.to_csv(index=False),
                file_name=f"analytics_{st.session_state.file_name}.csv",
                mime="text/csv"
            )

    with col2:
        if st.button("Download Full JSON", use_container_width=True):
            import json
            st.download_button(
                "Download JSON",
                json.dumps(analytics, indent=2),
                file_name=f"analytics_{st.session_state.file_name}.json",
                mime="application/json"
            )

def main():
    """Main application entry point"""
    # Initialize session state
    initialize_session_state()

    # Render header
    render_header()

    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📁 Upload", "🔍 Validation", "📊 Analytics"])

    with tab1:
        render_upload_tab()

    with tab2:
        render_validation_tab()

    with tab3:
        render_analytics_tab()

    # Sidebar
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
            **OptiClaimAI** helps healthcare providers validate
            837 EDI claims before submission to reduce denials.

            **Features:**
            - Real-time EDI parsing
            - Comprehensive validation
            - Denial risk prediction
            - Analytics & reporting
        """)

        st.divider()

        if st.session_state.file_uploaded:
            st.success("✅ File Loaded")
            if st.button("🔄 Reset Application"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        else:
            st.info("📁 No file loaded")

if __name__ == "__main__":
    main()
