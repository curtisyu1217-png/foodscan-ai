import streamlit as st
from google.cloud import vision
from google.oauth2 import service_account

st.title("FoodScan Debug")

st.write("Checking secrets...")

try:
    key_dict = st.secrets["GOOGLE_VISION_KEY"]
    st.write("Secrets loaded ✅")

    credentials = service_account.Credentials.from_service_account_info(key_dict)
    st.write("Credentials created ✅")

    client = vision.ImageAnnotatorClient(credentials=credentials)
    st.write("Vision client created ✅")

except Exception as e:
    st.error("Google Vision API key not loaded properly")
    st.write("Actual error:")
    st.write(e)
    st.stop()