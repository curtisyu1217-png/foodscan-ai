import streamlit as st
import pandas as pd
import json
from google.cloud import vision
from google.oauth2 import service_account

st.set_page_config(page_title="FoodScan AI", layout="centered")

st.title("🍱 FoodScan AI")
st.write("Upload a food photo to detect health risk")

# =============================
# Load Google Vision API
# =============================

try:
    key_dict = json.loads(st.secrets["GOOGLE_VISION_KEY"])
    credentials = service_account.Credentials.from_service_account_info(key_dict)
    client = vision.ImageAnnotatorClient(credentials=credentials)
except:
    st.error("Google Vision API key not loaded properly")
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

required_columns = [
    "ingredient",
    "dm_score",
    "chol_score",
    "bp_score",
    "category",
    "notes"
]

for col in required_columns:
    if col not in df.columns:
        st.error(f"Missing column: {col}")
        st.stop()

# =============================
# Upload image
# =============================

uploaded_file = st.file_uploader("Upload food image", type=["jpg", "jpeg", "png"])

if uploaded_file:

    st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)

    content = uploaded_file.read()
    image = vision.Image(content=content)

    response = client.label_detection(image=image)
    labels = [label.description.lower() for label in response.label_annotations]

    st.write("Detected labels:", labels)

    # =============================
    # Match ingredient
    # =============================

    match_row = None
    detected_food = None

    for label in labels:
        match = df[df["ingredient"].str.contains(label, case=False, na=False)]
        if not match.empty:
            match_row = match.iloc[0]
            detected_food = label
            break

    if match_row is not None:

        st.success(f"Detected Food: {detected_food}")

        st.markdown("---")

        st.subheader("Health Risk")

        st.write("DM Score:", match_row["dm_score"])
        st.write("Chol Score:", match_row["chol_score"])
        st.write("BP Score:", match_row["bp_score"])

        st.warning(match_row["category"])
        st.info(match_row["notes"])

    else:
        st.error("Food not found in database")