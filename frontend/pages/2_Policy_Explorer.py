import sys
from pathlib import Path
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from schema.policy import PolicyRepository, compare_versions
from utils.theme import configure_page, load_global_css, section_title, cyber_header
from components.cards import cyber_card, status_badge

configure_page("Policy Explorer | NIYAM-AI")
load_global_css()

cyber_header(
    "POLICY MANAGER",
    "Inspect, validate, version, and compare intent-governance policies"
)

status_badge("READ-ONLY REPOSITORY VISIBILITY", "info")

st.markdown("<br>", unsafe_allow_html=True)

# Initialize policy repository
repo = PolicyRepository()
all_policies = repo.list_policies()

tab1, tab2 = st.tabs(["Explore Policies", "Compare Versions"])

# ----------------------------------------------------
# TAB 1: EXPLORE POLICIES
# ----------------------------------------------------
with tab1:
    if not all_policies:
        st.warning("No policies found in the repository folder ('policies/').")
    else:
        col1, col2 = st.columns([1, 2.5])
        
        with col1:
            policy_id = st.selectbox("Select Policy", sorted(list(all_policies.keys())), key="exp_policy_select")
            
            versions = all_policies[policy_id]
            version_strs = [p.version for p in versions]
            version_str = st.radio("Select Version", version_strs, index=len(version_strs)-1, key="exp_version_select")
            
            # Find selected policy
            selected_policy = next(p for p in versions if p.version == version_str)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"**Status:**")
            st_color = "success" if selected_policy.status == "active" else "normal" if selected_policy.status == "draft" else "warning"
            status_badge(selected_policy.status.upper(), st_color)
            
        with col2:
            st.subheader(f"Policy: `{selected_policy.policy_id}` (v{selected_policy.version})")
            
            st.markdown(f"**Description:**  \n*{selected_policy.description}*")
            
            st.markdown("**Cryptographic Policy Hash:**")
            st.code(selected_policy.policy_hash, language="text")
            
            sub_col1, sub_col2 = st.columns(2)
            
            with sub_col1:
                st.markdown("### Allowed Tools ✅")
                if selected_policy.allowed_tools:
                    for tool in selected_policy.allowed_tools:
                        st.markdown(f"- `{tool}`")
                else:
                    st.caption("No allowed tools declared")
                    
            with sub_col2:
                st.markdown("### Forbidden Tools ❌")
                if selected_policy.forbidden_tools:
                    for tool in selected_policy.forbidden_tools:
                        st.markdown(f"- `{tool}`")
                else:
                    st.caption("No forbidden tools declared")
            
            st.markdown("### Constraints ⚙️")
            if selected_policy.constraints:
                st.json(selected_policy.constraints)
            else:
                st.caption("No constraints configured for this version")
                
            st.markdown("### Metadata 🏷️")
            if selected_policy.metadata:
                st.json(selected_policy.metadata)
            else:
                st.caption("No metadata available")

# ----------------------------------------------------
# TAB 2: COMPARE VERSIONS (DIFF)
# ----------------------------------------------------
with tab2:
    if len(all_policies) == 0:
        st.warning("No policies available to compare.")
    else:
        p_id = st.selectbox("Select Policy to Compare", sorted(list(all_policies.keys())), key="diff_policy_select")
        
        versions = all_policies[p_id]
        if len(versions) < 2:
            st.info("Policy must have at least 2 versions to perform comparisons. Create a new version under policies/ first.")
        else:
            version_strs = [p.version for p in versions]
            
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                v1_str = st.selectbox("Compare From (Version A)", version_strs, index=0)
            with col_v2:
                v2_str = st.selectbox("Compare To (Version B)", version_strs, index=len(version_strs)-1)
                
            if v1_str == v2_str:
                st.warning("Please select two different versions to compare.")
            else:
                p1 = next(p for p in versions if p.version == v1_str)
                p2 = next(p for p in versions if p.version == v2_str)
                
                diff = compare_versions(p1, p2)
                
                st.subheader(f"Comparison: v{v1_str} ➔ v{v2_str}")
                
                # Render Changes visually
                has_changes = False
                
                # 1. Allowed Tools
                if diff["added_allowed_tools"] or diff["removed_allowed_tools"]:
                    has_changes = True
                    st.markdown("#### Allowed Tools Changes")
                    for t in diff["removed_allowed_tools"]:
                        st.markdown(f"<span style='color:#FF3B5C;'>➖ Remove: `{t}`</span>", unsafe_allow_html=True)
                    for t in diff["added_allowed_tools"]:
                        st.markdown(f"<span style='color:#00FF88;'>➕ Add: `{t}`</span>", unsafe_allow_html=True)
                        
                # 2. Forbidden Tools
                if diff["added_forbidden_tools"] or diff["removed_forbidden_tools"]:
                    has_changes = True
                    st.markdown("#### Forbidden Tools Changes")
                    for t in diff["removed_forbidden_tools"]:
                        st.markdown(f"<span style='color:#00FF88;'>➖ Remove (Unblock): `{t}`</span>", unsafe_allow_html=True)
                    for t in diff["added_forbidden_tools"]:
                        st.markdown(f"<span style='color:#FF3B5C;'>➕ Add (Block): `{t}`</span>", unsafe_allow_html=True)
                
                # 3. Status Changes
                if "changed_status" in diff:
                    has_changes = True
                    st.markdown("#### Status Transition")
                    st.markdown(f"Status changed from `{diff['changed_status']['from']}` ➔ `{diff['changed_status']['to']}`")
                    
                # 4. Description Changes
                if "changed_description" in diff:
                    has_changes = True
                    st.markdown("#### Description Update")
                    st.markdown(f"**From:** *{diff['changed_description']['from']}*  \n**To:** *{diff['changed_description']['to']}*")
                    
                # 5. Constraints Changes
                if "changed_constraints" in diff:
                    has_changes = True
                    st.markdown("#### Constraints Modifications")
                    cc = diff["changed_constraints"]
                    if cc.get("added"):
                        st.markdown("**Added Constraints:**")
                        st.json(cc["added"])
                    if cc.get("removed"):
                        st.markdown("**Removed Constraints:**")
                        st.json(cc["removed"])
                    if cc.get("modified"):
                        st.markdown("**Modified Constraints:**")
                        for k, v in cc["modified"].items():
                            st.markdown(f"- Parameter `{k}` changed from `{v['from']}` to `{v['to']}`")
                            
                if not has_changes:
                    st.success("Versions are identical - no governance parameter differences detected.")
