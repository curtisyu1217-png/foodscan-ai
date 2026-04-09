import streamlit as st
import pandas as pd
from google.cloud import vision
from google.oauth2 import service_account

st.set_page_config(page_title="FoodScan AI", layout="centered")
st.title("🍱 FoodScan AI")
st.write("Upload a food photo to detect health risk")

# =============================
# Load Google Vision API
# =============================
try:
    key_dict = dict(st.secrets["GOOGLE_VISION_KEY"])
    credentials = service_account.Credentials.from_service_account_info(key_dict)
    client = vision.ImageAnnotatorClient(credentials=credentials)
except Exception as e:
    st.error(f"Google Vision API key not loaded properly: {e}")
    st.stop()

# =============================
# Load CSV
# =============================
try:
    df = pd.read_csv("food.csv")
except:
    st.error("food.csv not found")
    st.stop()

df.columns = df.columns.str.lower()
required_columns = ["ingredient", "dm_score", "chol_score", "bp_score", "category", "notes"]
for col in required_columns:
    if col not in df.columns:
        st.error(f"Missing column: {col}")
        st.stop()

# =============================
# Condition selection
# =============================
st.markdown("---")
st.subheader("Your Condition")
condition = st.radio(
    "Select your condition to see relevant risk:",
    ["All", "Diabetes (DM)", "High Cholesterol", "High Blood Pressure (BP)"],
    horizontal=True
)

# =============================
# Traffic light helper
# =============================
def traffic_light(label, score, category):
    category_lower = str(category).lower()
    if "low" in category_lower:
        color = "#2ecc71"
        emoji = "🟢"
        risk = "Low Risk"
    elif "high" in category_lower:
        color = "#e74c3c"
        emoji = "🔴"
        risk = "High Risk"
    else:
        color = "#f39c12"
        emoji = "🟡"
        risk = "Moderate Risk"

    st.markdown(
        f"""
        <div style="
            background-color: {color}22;
            border-left: 5px solid {color};
            border-radius: 8px;
            padding: 12px 16px;
            margin: 8px 0;
        ">
            <span style="font-size: 20px;">{emoji}</span>
            <strong style="font-size: 16px; margin-left: 8px;">{label}</strong>
            <span style="float: right; font-size: 14px; color: {color}; font-weight: bold;">{risk} (Score: {score})</span>
        </div>
        """,
        unsafe_allow_html=True
    )

# =============================
# Confidence threshold
# =============================
CONFIDENCE_THRESHOLD = 0.7

# =============================
# Upload image
# =============================
st.markdown("---")
uploaded_file = st.file_uploader("Upload food image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
    content = uploaded_file.read()
    image = vision.Image(content=content)
    response = client.label_detection(image=image)

    # Filter by confidence threshold
    labels = [
        label.description.lower()
        for label in response.label_annotations
        if label.score >= CONFIDENCE_THRESHOLD
    ]

    if not labels:
        st.warning("Image not clear enough to detect food. Please try a clearer photo.")
        st.stop()

    # Match ingredient
    match_row = None
    detected_food = None
    for label in labels:
        match = df[df["ingredient"].str.contains(label, case=False, na=False)]
        if not match.empty:
            match_row = match.iloc[0]
            detected_food = label
            break

    if match_row is not None:
        st.success(f"✅ Detected Food: **{detected_food.title()}**")
        st.markdown("---")
        st.subheader("Health Risk Assessment")
        st.caption(match_row["notes"])
        st.markdown(" ")

        # Show relevant scores based on condition
        if condition == "All":
            traffic_light("Diabetes (DM)", match_row["dm_score"], match_row["category"])
            traffic_light("Cholesterol", match_row["chol_score"], match_row["category"])
            traffic_light("Blood Pressure (BP)", match_row["bp_score"], match_row["category"])
        elif condition == "Diabetes (DM)":
            traffic_light("Diabetes (DM)", match_row["dm_score"], match_row["category"])
        elif condition == "High Cholesterol":
            traffic_light("Cholesterol", match_row["chol_score"], match_row["category"])
        elif condition == "High Blood Pressure (BP)":
            traffic_light("Blood Pressure (BP)", match_row["bp_score"], match_row["category"])

    else:
        st.error("❌ Food not found in database. Try a clearer photo or a different angle.")
        st.write("Detected labels:", labels)