import sys
import os
import streamlit as st
from dotenv import load_dotenv

# 1. Setup the path BEFORE doing anything else
# This adds the root directory to your path so Python can find 'graph' and 'schemas'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. Now import your project modules
from graph import app  # Now this will work because the path is updated
load_dotenv()

# 3. Application Logic
st.title("Log Analysis Agent")

uploaded_file = st.file_uploader("Upload your log file", type="txt")

if uploaded_file and st.button("Analyze Logs"):
    # Read the file
    raw_text = uploaded_file.read().decode("utf-8")
    
    with st.spinner("Agents are working..."):
        # Invoke the graph with the initial state
        initial_state = {"raw_logs": raw_text}
        result = app.invoke(initial_state)
        
        st.success("Analysis Complete!")
        
        # Display results (using .get() to avoid errors if a key is missing)
        st.write("### Root Cause:", result.get("root_cause", "No root cause found."))
        st.write("### Recommended Fix:", result.get("remediation_plan", "No fix identified."))
        st.write("### Ticket Created:", result.get("ticket_details", "No ticket details."))