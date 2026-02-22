"""
Display validation results with AI-powered explanations
"""

import streamlit as st
from model.claim_schema import Claim
from engine.output_formatter import OutputFormatter

# Lazy import Ollama
try:
    from engine.ollama_wrapper import get_ollama
except ImportError:
    get_ollama = None


def render_results(claim: Claim, validation_result: dict):
    """Display claim validation results with AI explanations"""
    
    st.success("✅ Claim Processed Successfully")
    st.divider()
    
    # Claim Summary
    st.subheader("📊 Claim Summary")
    st.markdown(OutputFormatter.format_claim_summary(claim))
    
    st.divider()
    
    # Denial Risk at top
    st.subheader("📈 Denial Risk Assessment")
    
    risk_data = OutputFormatter.format_denial_risk(
        validation_result['denial_risk_score'],
        validation_result['denial_risk_level'],
        validation_result['issue_count']
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Risk Level", f"{risk_data['color']} {risk_data['level']}")
    with col2:
        st.metric("Risk Score", f"{risk_data['score']}%")
    with col3:
        st.metric("Valid for Submit", "✅ YES" if validation_result['is_valid'] else "❌ NO")
    
    st.info(risk_data['recommendation'])
    
    st.divider()
    
    # Issues
    st.subheader("⚠️ Validation Issues")
    
    if validation_result['issue_count'] == 0:
        st.success("✨ No issues found! This claim is ready to submit.")
    else:
        issues_grouped = OutputFormatter.format_issues_for_display(validation_result['issues'])
        
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            if issues_grouped[severity]:
                # Get severity icon
                icon_map = {
                    'CRITICAL': '🔴',
                    'HIGH': '🟠',
                    'MEDIUM': '🟡',
                    'LOW': '🟢',
                }
                icon = icon_map.get(severity, '⚪')
                
                with st.expander(
                    f"{icon} {severity} ({len(issues_grouped[severity])} issue(s))",
                    expanded=(severity in ['CRITICAL', 'HIGH'])
                ):
                    for idx, issue in enumerate(issues_grouped[severity]):
                        # Issue message
                        st.markdown(f"**{issue.get('message', 'Unknown issue')}**")
                        
                        if issue.get('field'):
                            st.caption(f"Field: `{issue['field']}`")
                        
                        # AI Explanation button
                        col1, col2 = st.columns([3, 1])
                        with col2:
                            if st.button(
                                "💡 Explain",
                                key=f"explain_{severity}_{idx}",
                                help="Get AI explanation for this issue"
                            ):
                                with st.spinner("Getting AI explanation..."):
                                    if get_ollama:
                                        ollama = get_ollama()
                                        if ollama.is_available():
                                            # Build simple prompt for explanation
                                            prompt = f"""Explain this healthcare claims issue in 2-3 sentences:
Issue: {issue.get('message', '')}
Code: {issue.get('code', '')}
How to fix: {issue.get('why_failed', '')}

Keep it simple and actionable."""
                                            explanation = ollama.generate(
                                                prompt=prompt,
                                                model="llama3.1"
                                            )
                                            if explanation:
                                                st.info(f"**AI Explanation:** {explanation}")
                                            else:
                                                st.caption("*(AI explanation unavailable)*")
                                        else:
                                            st.caption("*(Ollama not running - use Chat mode to configure)*")
                                    else:
                                        st.caption("*(AI not available)*")
                        
                        st.divider()
    
    # Get fix guidance
    if validation_result['issue_count'] > 0:
        st.divider()
        if st.button("💡 Get AI Guidance on Fixing Issues", type="secondary", use_container_width=True):
            with st.spinner("Generating fix guidance..."):
                if get_ollama:
                    ollama = get_ollama()
                    if ollama.is_available():
                        # Build fix guidance prompt
                        issues_text = "\n".join([f"- {issue.get('message', '')}" for issue in validation_result['issues'][:5]])
                        prompt = f"""As a healthcare billing expert, provide 3-5 practical fixes for these claim issues:

{issues_text}

For claim:
{OutputFormatter.format_claim_summary(claim)}

Provide actionable steps."""
                        guidance = ollama.generate(
                            prompt=prompt,
                            model="llama3.1"
                        )
                        if guidance:
                            st.success("**Fix Guidance:**")
                            st.markdown(guidance)
                        else:
                            st.info("*(AI guidance unavailable)*")
                    else:
                        st.info("*(Ollama not running - use Chat mode to configure)*")
                else:
                    st.info("*(AI not available)*")
    
    st.divider()
    
    # Export options
    st.subheader("📥 Export & Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 View Full Validation Rules", use_container_width=True):
            st.json(validation_result)
    
    with col2:
        if st.button("📄 Generate 837 Preview (Coming Soon)", use_container_width=True):
            st.info("EDI 837 generation will be available in next version")
    
    with col3:
        if st.button("💾 Save Claim", use_container_width=True):
            st.success("Claim saved to session!")
