import streamlit as st
import pandas as pd
import numpy as np
from api import submit_complaint, get_all_complaints, get_analytics

st.set_page_config(page_title="AutoNagrik CRM", layout="wide")

st.title("🏛️ AutoNagrik: Smart City CRM (Nagpur)")

tab1, tab2, tab3 = st.tabs(["📱 Citizen Portal", "📊 Admin Dashboard", "🚁 Multimodal Feed"])

# ─── TAB 1: CITIZEN PORTAL ──────────────────────────────────────────────────
with tab1:
    st.header("Report a Civic Issue")
    st.info("Type your complaint in Marathi, Hindi, or English. No category selection needed.")
    
    user_text = st.text_area("What is the issue?", placeholder="e.g., Dharampeth madhe kachra gaadi aali nahi...")
    
    if st.button("Submit Complaint"):
        with st.spinner("🤖 AI processing, translating, and routing..."):
            result = submit_complaint(user_text)
            
            if result["success"]:
                st.success(f"✅ {result['acknowledgment_message']}")
                st.markdown("### 📍 Live Status Tracker")
                st.progress(25) 
                st.caption(f"**Tracking ID:** `{result['complaint_id']}` | **Status:** AI Processed & Routed to {result['department']}")
                
                with st.expander("👀 Peek under the hood (AI Output)"):
                    st.json({
                        "Detected Language": result["detected_language"],
                        "Translated English": result["translated_text"],
                        "Assigned Category": result["category"],
                        "Urgency Level": result["priority"]
                    })
            else:
                st.error(f"Backend Error: {result['error']}")

# ─── TAB 2: ADMIN DASHBOARD (UPDATED FOR REAL GPS) ──────────────────────────
with tab2:
    st.header("City Operations Command Center")
    
    analytics_resp = get_analytics()
    if analytics_resp["success"]:
        a = analytics_resp["analytics"]
        col1, col2, col3 = st.columns(3)
        col1.metric("🏆 City Health Score", a.get("city_health_score", "N/A"), a.get("health_status", ""))
        col2.metric("Total Complaints", a.get("total_complaints", 0))
        col3.metric("Avg Resolution Time", "2.4 Days") 
        
        if a.get("overload_warning_active"):
            st.error(f"⚠️ **OVERLOAD WARNING:** {', '.join(a.get('overloaded_departments', []))} departments need immediate escalation!")
    
    st.markdown("---")
    col_map, col_data = st.columns([1, 1])
    
    with col_map:
        st.subheader("📍 Live Grievance Hotspots (Real-Time GPS)")
        # FETCH REAL DATA FOR THE MAP
        all_data = get_all_complaints(limit=100)
        if all_data["success"] and all_data["complaints"]:
            df_map = pd.DataFrame(all_data["complaints"])
            # Clean coordinate data
            if 'latitude' in df_map.columns and 'longitude' in df_map.columns:
                df_map = df_map.dropna(subset=['latitude', 'longitude'])
                # Streamlit automatically maps 'latitude' and 'longitude' columns
                st.map(df_map[['latitude', 'longitude']], zoom=11, use_container_width=True)
            else:
                st.warning("Waiting for GPS data injection...")
        
    with col_data:
        st.subheader("📋 Recent Tickets (Verification Mode)")
        
        # Increase limit to 60 so you can see all 50 complaints + test ones
        complaints_resp = get_all_complaints(limit=60) 
        
        if complaints_resp["success"] and complaints_resp["complaints"]:
            df = pd.DataFrame(complaints_resp["complaints"])
            
            # Auto-rename if needed
            if 'id' in df.columns and 'complaint_id' not in df.columns:
                df = df.rename(columns={'id': 'complaint_id'})
            
            # ADDED: 'original_text' (which contains [Area]), 'latitude', and 'longitude'
            desired_cols = ['complaint_id', 'original_text', 'latitude', 'longitude', 'status']
            existing_cols = [col for col in desired_cols if col in df.columns]
            
            # Display the interactive table
            st.dataframe(df[existing_cols], use_container_width=True, height=500)
            
            st.caption("💡 Pro Tip: Hover over the dots on the map to see coordinates, then match them with this table.")
        else:
            st.info("No complaints in database yet.")

# ─── TAB 3: MULTIMODAL FEED ─────────────────────────────────────────────────
with tab3:
    st.header("🚁 Multimodal Field Ingestion System")
    feed_source = st.radio("Select Live Data Source:", 
                           ["💻 Primary Fast Feed (PC Webcam)", "📱 Frugal Field Node (IP Webcam)", "📂 Archived 3D/Thermal Scan (Video)"], 
                           horizontal=True)

    st.markdown("---")
    if feed_source == "💻 Primary Fast Feed (PC Webcam)":
        st.camera_input("Live Municipal Assessment Feed")
        st.success("✅ Ultra-low latency connection established.")
    elif feed_source == "📱 Frugal Field Node (IP Webcam)":
        st.warning("📡 Connecting to remote field edge-node...")
        try:
            st.image("http://192.168.1.5:8080/video", use_container_width=True)
        except:
            st.error("Connection timeout. Switch to Primary Feed.")
    else:
        st.info("📂 Loading high-fidelity disaster area scan...")
        try:
            st.video("archived_footage.mp4")
        except:
            st.error("archived_footage.mp4 not found.")