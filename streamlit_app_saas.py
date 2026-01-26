"""
OptiClaimAI - Premium SaaS Edition
100% Paid Platform - No Free Access to Core Features
"""

import streamlit as st
import json
from pathlib import Path
from datetime import datetime, date
import sys
from typing import Optional, Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from services.auth import AuthService, ensure_db_initialized
from services.billing import BillingService
from services.database import (
    User, Subscription, SubscriptionTier, 
    get_tier_limits, check_usage_limit, log_usage, get_monthly_usage
)
from model.canonical_claim import CanonicalClaim, ClaimMetadata
from services.validation_engine import ValidationEngine, ValidationSeverity
from services.ai_engine import AIEngine
from services.npi_lookup import get_npi_service
from services.edi_bridge import get_edi_service
from services.pdf_parser import PDFClaimParser

# ============= PAGE CONFIG =============

st.set_page_config(
    page_title="OptiClaimAI - Premium Claims Intelligence",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
ensure_db_initialized()

# ============= SESSION STATE INIT =============

def init_session():
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "user_data" not in st.session_state:
        st.session_state.user_data = None
    if "canonical_claim" not in st.session_state:
        st.session_state.canonical_claim = None
    if "validation_result" not in st.session_state:
        st.session_state.validation_result = None
    if "ai_explanation" not in st.session_state:
        st.session_state.ai_explanation = None
    if "edi_output" not in st.session_state:
        st.session_state.edi_output = None
    if "npi_lookup_result" not in st.session_state:
        st.session_state.npi_lookup_result = None

init_session()

# ============= AUTHENTICATION GUARD =============

def require_login():
    """Redirect to login if not authenticated"""
    if not st.session_state.user_id:
        st.error("🔒 Access Denied - Please log in")
        show_login_page()
        st.stop()

def require_active_subscription():
    """Check if user has active subscription"""
    if not st.session_state.user_id:
        st.error("🔒 Please log in")
        st.stop()
    
    auth = AuthService()
    is_active = auth.verify_subscription_active(st.session_state.user_id)
    
    if not is_active:
        st.error("❌ Your subscription is inactive. Please upgrade to continue.")
        show_upgrade_prompt()
        st.stop()

def require_feature(feature: str):
    """Check if user has access to feature"""
    from services.database import has_feature
    
    if not has_feature(st.session_state.user_id, feature):
        tier = st.session_state.user_data.get("subscription", {}).get("tier", "basic")
        st.error(f"🔒 This feature is not available in {tier.upper()} tier. Upgrade to Pro.")
        return False
    return True

def check_usage_quota(action: str) -> bool:
    """Check if user has quota remaining for action"""
    is_allowed, message = check_usage_limit(st.session_state.user_id, action)
    
    if not is_allowed:
        st.error(f"❌ {message}")
        return False
    
    if "Warning" in message:
        st.warning(f"⚠️ {message}")
    
    return True

# ============= LOGIN PAGE =============

def show_login_page():
    """Landing page with login/register"""
    st.title("🏥 OptiClaimAI")
    st.markdown("### Premium Healthcare Claims Intelligence")
    st.markdown("Transform healthcare claims into compliant, insightful data")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        
        # Tab between login and register
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.subheader("Login to Your Account")
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("🔓 Login", use_container_width=True):
                if email and password:
                    success, user_id, message = AuthService.login(email, password)
                    if success:
                        st.session_state.user_id = user_id
                        st.session_state.user_data = AuthService.get_user_with_subscription(user_id)
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.warning("⚠️ Enter email and password")
        
        with tab2:
            st.subheader("Create Your Account")
            reg_email = st.text_input("Email", key="reg_email")
            reg_first = st.text_input("First Name", key="reg_first")
            reg_last = st.text_input("Last Name", key="reg_last")
            reg_password = st.text_input("Password (min 8 chars)", type="password", key="reg_password")
            reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
            
            if st.button("📝 Create Account", use_container_width=True):
                if not all([reg_email, reg_password, reg_confirm]):
                    st.warning("⚠️ Fill all required fields")
                elif len(reg_password) < 8:
                    st.warning("⚠️ Password must be at least 8 characters")
                elif reg_password != reg_confirm:
                    st.warning("⚠️ Passwords don't match")
                else:
                    success, message = AuthService.register(
                        reg_email, reg_password, reg_first, reg_last
                    )
                    if success:
                        st.success("✅ Account created! Log in to start.")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        
        st.markdown("---")
        
        # Pricing information
        st.subheader("💳 Pricing")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### BASIC - $49/month
            - 10 claims/month
            - Rule validation
            - Limited AI
            - EDI export
            """)
        
        with col2:
            st.markdown("""
            ### PRO - $149/month
            - Unlimited claims
            - Full AI access
            - NPI auto-fill
            - EDI upload & validation
            - Claim history
            """)

# ============= UPGRADE PROMPT =============

def show_upgrade_prompt():
    """Show upgrade/billing prompt"""
    st.warning("Your subscription is inactive or expired.")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("💳 Upgrade to Pro ($149/month)", use_container_width=True):
            checkout_url = BillingService.create_checkout_session(
                st.session_state.user_id,
                SubscriptionTier.PRO,
                success_url="http://localhost:8501?success=true",
                cancel_url="http://localhost:8501"
            )
            if checkout_url:
                st.markdown(f"[→ Complete Checkout]({checkout_url})")
            else:
                st.error("Payment processing unavailable")
    
    with col2:
        if st.button("💳 Upgrade to Basic ($49/month)", use_container_width=True):
            checkout_url = BillingService.create_checkout_session(
                st.session_state.user_id,
                SubscriptionTier.BASIC,
                success_url="http://localhost:8501?success=true",
                cancel_url="http://localhost:8501"
            )
            if checkout_url:
                st.markdown(f"[→ Complete Checkout]({checkout_url})")
            else:
                st.error("Payment processing unavailable")
    
    with col3:
        if st.button("📧 Contact Sales", use_container_width=True):
            st.info("Email: sales@opticlaimai.com")

# ============= MAIN APP =============

def show_main_app():
    """Main application after login"""
    
    # Header
    st.title("🏥 OptiClaimAI")
    
    # Sidebar
    with st.sidebar:
        st.subheader("👤 Account")
        
        user_data = st.session_state.user_data
        st.write(f"**{user_data.get('first_name', 'User')} {user_data.get('last_name', '')}**")
        st.write(f"Email: {user_data.get('email')}")
        
        # Subscription status
        if user_data.get("subscription"):
            sub = user_data["subscription"]
            st.markdown("---")
            st.subheader("📊 Subscription")
            
            if sub["is_active"]:
                st.success(f"🟢 {sub['tier'].upper()} (Active)")
                st.write(f"Days until renewal: {sub['days_until_renewal']}")
            else:
                st.error(f"🔴 {sub['tier'].upper()} (Inactive)")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💳 Manage Billing", use_container_width=True):
                    portal_url = BillingService.get_billing_portal_url(st.session_state.user_id)
                    if portal_url:
                        st.markdown(f"[→ Open Billing Portal]({portal_url})")
            
            with col2:
                if st.button("🆙 Upgrade", use_container_width=True):
                    show_upgrade_prompt()
        
        st.markdown("---")
        
        # Usage meter
        st.subheader("📈 Monthly Usage")
        
        limits = get_tier_limits(user_data.get("subscription", {}).get("tier", "basic"))
        
        claims_limit = limits.get("claims_per_month")
        claims_used = get_monthly_usage(st.session_state.user_id, "claim_created")
        
        if claims_limit:
            percent = (claims_used / claims_limit) * 100
            st.metric("Claims", f"{claims_used}/{claims_limit}", f"{int(percent)}%")
        else:
            st.metric("Claims", "Unlimited", "∞")
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.user_data = None
            st.rerun()
    
    # Check subscription
    require_active_subscription()
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Submit Claim",
        "✅ Validate & Export",
        "📊 Dashboard",
        "⚙️ Settings"
    ])
    
    with tab1:
        st.subheader("📋 Submit Healthcare Claim")
        
        # Check quota
        if not check_usage_quota("claim_created"):
            st.stop()
        
        # Upload option
        st.markdown("### 📤 Quick Upload")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "Upload claim PDF (auto-fills form)",
                type=["pdf"],
                label_visibility="collapsed"
            )
        
        with col2:
            if uploaded_file:
                st.success("✅ PDF ready")
        
        # Parse PDF if uploaded
        pdf_data = None
        auto_filled_fields = set()
        
        if uploaded_file:
            from services.pdf_parser import PDFClaimParser
            pdf_bytes = uploaded_file.read()
            with st.spinner("🔄 Parsing PDF..."):
                pdf_data = PDFClaimParser.parse_from_pdf_bytes(pdf_bytes)
            
            if pdf_data:
                # Track which fields have values from PDF
                auto_filled_fields = {k for k, v in pdf_data.items() if v}
                st.success(f"✅ PDF parsed! Auto-filled {len(auto_filled_fields)} fields.")
            else:
                st.info("ℹ️ This PDF appears to be scanned/image-based. Please fill the form manually or provide a text-based PDF.")
        
        st.markdown("---")
        st.markdown("### 📝 Claim Details")
        
        # Form with auto-filled values from PDF
        with st.form("claim_form"):
            
            # Patient section
            st.markdown("#### 👤 Patient Information")
            col1, col2, col3 = st.columns([2, 2, 1.5])
            
            with col1:
                pat_first = st.text_input(
                    "First Name *" + (" ✅" if "patient_first" in auto_filled_fields else ""),
                    value=pdf_data.get("patient_first") if pdf_data else "",
                    placeholder="John"
                )
            
            with col2:
                pat_last = st.text_input(
                    "Last Name *" + (" ✅" if "patient_last" in auto_filled_fields else ""),
                    value=pdf_data.get("patient_last") if pdf_data else "",
                    placeholder="Doe"
                )
            
            with col3:
                pat_dob = st.date_input(
                    "Date of Birth *",
                    value=None,
                    help="YYYY-MM-DD"
                )
                # Parse DOB from PDF if available
                if pdf_data and pdf_data.get("patient_dob"):
                    try:
                        from datetime import datetime
                        pat_dob = datetime.fromisoformat(pdf_data["patient_dob"]).date()
                    except:
                        pass
            
            col1, col2 = st.columns(2)
            
            with col1:
                pat_member = st.text_input(
                    "Member/Policy ID" + (" ✅" if "patient_member_id" in auto_filled_fields else ""),
                    value=pdf_data.get("patient_member_id") if pdf_data else "",
                    placeholder="MEM123456"
                )
            
            with col2:
                pat_gender = st.selectbox(
                    "Gender",
                    ["Select...", "M", "F", "U"],
                    index=0
                )
            
            st.markdown("---")
            
            # Provider section
            st.markdown("#### 👨‍⚕️ Provider Information")
            col1, col2, col3 = st.columns([1.5, 2, 2])
            
            with col1:
                prov_npi = st.text_input(
                    "NPI (10 digits) *" + (" ✅" if "provider_npi" in auto_filled_fields else ""),
                    value=pdf_data.get("provider_npi") if pdf_data else "",
                    placeholder="1234567890",
                    max_chars=10
                )
            
            with col2:
                prov_first = st.text_input(
                    "First Name",
                    value=pdf_data.get("provider_first") if pdf_data else "",
                    placeholder="Jane"
                )
            
            with col3:
                prov_last = st.text_input(
                    "Last Name",
                    value=pdf_data.get("provider_last") if pdf_data else "",
                    placeholder="Smith"
                )
            
            # NPI Lookup
            if prov_npi and len(prov_npi) == 10:
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button("🔍 Lookup", key="npi_lookup"):
                        npi_service = get_npi_service()
                        with st.spinner("Looking up NPI..."):
                            result = npi_service.lookup_npi(prov_npi)
                            st.session_state.npi_lookup_result = result
                
                if st.session_state.npi_lookup_result:
                    st.success("✅ Found!")
            
            st.markdown("---")
            
            # Service section
            st.markdown("#### 💊 Service Information")
            col1, col2, col3 = st.columns([1.5, 2, 1.5])
            
            with col1:
                svc_date = st.date_input(
                    "Service Date *",
                    help="When service was rendered"
                )
                # Parse from PDF
                if pdf_data and pdf_data.get("service_date"):
                    try:
                        from datetime import datetime
                        svc_date = datetime.fromisoformat(pdf_data["service_date"]).date()
                    except:
                        pass
            
            with col2:
                proc_code = st.text_input(
                    "CPT/HCPCS Code *" + (" ✅" if "procedure_code" in auto_filled_fields else ""),
                    value=pdf_data.get("procedure_code") if pdf_data else "",
                    placeholder="99213",
                    max_chars=10
                )
            
            with col3:
                place_of_service = st.selectbox(
                    "Place of Service",
                    ["11", "12", "21", "22", "23", "31", "41", "49", "71"],
                    help="11=Office, 12=Home, 21=ER, 22=Ambulance, 23=Urgent, 31=SNF, 41=Ambulatory, 49=Other, 71=State/Fed"
                )
            
            # Charges
            col1, col2, col3 = st.columns(3)
            
            with col1:
                units = st.number_input(
                    "Units",
                    min_value=0.0,
                    value=1.0,
                    step=0.5
                )
            
            with col2:
                unit_price = st.number_input(
                    "Unit Price ($)",
                    min_value=0.0,
                    value=0.0,
                    step=1.0
                )
            
            with col3:
                charge = st.number_input(
                    "Line Charge ($) *" + (" ✅" if "charge" in auto_filled_fields else ""),
                    min_value=0.0,
                    value=pdf_data.get("charge", 0.0) if pdf_data else 0.0,
                    step=1.0
                )
            
            st.markdown("---")
            
            # Diagnosis section
            st.markdown("#### 🏷️ Diagnosis")
            col1, col2 = st.columns([1.5, 2])
            
            with col1:
                diag_code = st.text_input(
                    "ICD-10 Code *" + (" ✅" if "diagnosis_code" in auto_filled_fields else ""),
                    value=pdf_data.get("diagnosis_code") if pdf_data else "",
                    placeholder="J45.901",
                    max_chars=10
                )
            
            with col2:
                diag_desc = st.text_input(
                    "Description",
                    placeholder="e.g., Unspecified asthma with (acute) exacerbation"
                )
            
            st.markdown("---")
            
            # Submit button
            col1, col2 = st.columns([1, 4])
            
            with col1:
                submitted = st.form_submit_button("✅ Submit Claim", use_container_width=True)
            
            with col2:
                st.caption("* = Required fields")
            
            if submitted:
                # Validate required fields
                errors = []
                if not pat_first:
                    errors.append("Patient first name required")
                if not pat_last:
                    errors.append("Patient last name required")
                if not pat_dob:
                    errors.append("Patient DOB required")
                if not prov_npi:
                    errors.append("Provider NPI required")
                if not proc_code:
                    errors.append("Procedure code required")
                if not charge or charge <= 0:
                    errors.append("Valid charge amount required")
                if not diag_code:
                    errors.append("Diagnosis code required")
                
                if errors:
                    st.error("❌ Please fix errors:")
                    for error in errors:
                        st.write(f"- {error}")
                else:
                    try:
                        from model.canonical_claim import Patient, Provider, ServiceLine, Diagnosis
                        
                        claim = CanonicalClaim(
                            patient=Patient(
                                first_name=pat_first,
                                last_name=pat_last,
                                date_of_birth=pat_dob,
                                gender=pat_gender if pat_gender != "Select..." else None,
                                member_id=pat_member if pat_member else None
                            ),
                            provider=Provider(
                                npi=prov_npi,
                                first_name=prov_first if prov_first else None,
                                last_name=prov_last if prov_last else None
                            ),
                            service_lines=[ServiceLine(
                                service_date=svc_date,
                                procedure_code=proc_code,
                                line_charge=charge,
                                units=units if units > 0 else None,
                                unit_price=unit_price if unit_price > 0 else None,
                                place_of_service_code=place_of_service
                            )],
                            diagnoses=[Diagnosis(
                                icd10_code=diag_code,
                                description=diag_desc if diag_desc else None,
                                is_primary=True
                            )],
                            metadata=ClaimMetadata(source="saas_portal", submission_date=date.today())
                        )
                        
                        st.session_state.canonical_claim = claim
                        log_usage(st.session_state.user_id, "claim_created")
                        st.success("✅ Claim created successfully!")
                        st.balloons()
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ Error creating claim: {str(e)}")
    
    with tab2:
        st.subheader("Validate & Export")
        
        if not st.session_state.canonical_claim:
            st.info("📌 Create a claim first")
        else:
            if st.button("🔍 Validate Claim", use_container_width=True):
                if not check_usage_quota("claim_validated"):
                    st.stop()
                
                engine = ValidationEngine()
                result = engine.validate_claim(st.session_state.canonical_claim.to_dict())
                st.session_state.validation_result = result
                log_usage(st.session_state.user_id, "claim_validated")
                st.rerun()
            
            if st.session_state.validation_result:
                result = st.session_state.validation_result
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    risk_color = "🔴" if result.denial_risk_level == "CRITICAL" else "🟠" if result.denial_risk_level == "HIGH" else "🟡" if result.denial_risk_level == "MEDIUM" else "🟢"
                    st.metric("Risk Level", f"{risk_color} {result.denial_risk_level}")
                with col2:
                    st.metric("Risk Score", f"{result.denial_risk_score:.0f}/100")
                with col3:
                    st.metric("Valid", "✅ Yes" if result.is_valid else "❌ No")
                
                # Issues
                high = [i for i in result.issues if i.severity == ValidationSeverity.HIGH]
                med = [i for i in result.issues if i.severity == ValidationSeverity.MEDIUM]
                low = [i for i in result.issues if i.severity == ValidationSeverity.LOW]
                
                if high:
                    st.markdown("### 🔴 Critical Issues")
                    for issue in high:
                        st.write(f"- **{issue.field}**: {issue.issue}")
                
                if med:
                    st.markdown("### 🟠 Medium Issues")
                    for issue in med:
                        st.write(f"- **{issue.field}**: {issue.issue}")
                
                # AI explanations (PRO tier only)
                if require_feature("ai_full"):
                    if st.button("💡 Explain Issues (AI)", use_container_width=True):
                        if not check_usage_quota("ai_called"):
                            st.stop()
                        
                        ai = AIEngine()
                        explanation = ai.explain_issues(
                            [i.to_dict() for i in result.issues],
                            st.session_state.canonical_claim.to_dict()
                        )
                        if explanation:
                            st.session_state.ai_explanation = explanation
                            log_usage(st.session_state.user_id, "ai_called")
                
                if st.session_state.ai_explanation:
                    st.markdown("### 💬 AI Analysis")
                    st.write(st.session_state.ai_explanation)
                
                # EDI export
                if st.button("📄 Export to EDI 837P", use_container_width=True):
                    if not check_usage_quota("edi_generated"):
                        st.stop()
                    
                    edi_service = get_edi_service()
                    edi_text, error = edi_service.generate_edi_837p(st.session_state.canonical_claim.to_dict())
                    
                    if edi_text:
                        st.session_state.edi_output = edi_text
                        log_usage(st.session_state.user_id, "edi_generated")
                        st.success("✅ EDI generated!")
                    else:
                        st.error(f"❌ {error}")
                
                if st.session_state.edi_output:
                    st.code(st.session_state.edi_output, language="text")
                    st.download_button(
                        "📥 Download EDI",
                        st.session_state.edi_output,
                        "claim.837",
                        "text/plain"
                    )
    
    with tab3:
        st.subheader("📊 Dashboard")
        st.write("Your claims and usage analytics")
        # TODO: Claims history, analytics charts
    
    with tab4:
        st.subheader("⚙️ Account Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Security")
            if st.button("🔐 Change Password"):
                st.info("Password change coming soon")
        
        with col2:
            st.markdown("### Support")
            st.write("📧 support@opticlaimai.com")

# ============= APP ROUTER =============

if st.session_state.user_id:
    show_main_app()
else:
    show_login_page()
