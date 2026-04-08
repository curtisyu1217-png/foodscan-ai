import streamlit as st
from google.cloud import vision
from google.oauth2 import service_account
import pandas as pd

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="FoodScan AI", page_icon="🍱")
st.title("🍱 FoodScan AI")
st.write("Upload a food image to detect food and estimate calories")

# -----------------------------
# LOAD GOOGLE VISION SECRET
# -----------------------------
try:
    key_dict = dict(st.secrets["GOOGLE_VISION_KEY"])
    credentials = service_account.Credentials.from_service_account_info(key_dict)
    client = vision.ImageAnnotatorClient(credentials=credentials)
except Exception as e:
    st.error("Google Vision API key not loaded properly")
    st.stop()

# -----------------------------
# LOAD FOOD DATABASE
# -----------------------------
try:
    df = pd.read_csv("food.csv")
except:
    st.error("food.csv not found")
    st.stop()

food_list = df["food"].str.lower().tolist()

# -----------------------------
# PRIORITY MATCH FUNCTION
# -----------------------------
priority_keywords = [
    "rice",
    "noodle",
    "chicken",
    "beef",
    "pork",
    "egg",
    "fish",
    "salmon",
    "shrimp",
    "pizza",
    "burger",
    "pasta",
    "cake",
    "bread",
    "sushi",
    "ramen",
    "steak"
]

def priority_match(labels):

    detected = []

    for label in labels:
        text = label.description.lower()

        for food in food_list:
            if food in text:
                detected.append(food)

        for keyword in priority_keywords:
            if keyword in text:
                detected.append(keyword)

    detected = list(set(detected))

    return detected[:5]

# -----------------------------
# IMAGE UPLOAD
# -----------------------------
uploaded_file = st.file_uploader("Upload food image", type=["jpg","jpeg","png"])

if uploaded_file:

    st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)

    content = uploaded_file.read()
    image = vision.Image(content=content)

    with st.spinner("Scanning food..."):

        response = client.label_detection(image=image)
        labels = response.label_annotations

    if not labels:
        st.warning("No food detected")
        st.stop()

    # -----------------------------
    # MATCH FOOD
    # -----------------------------
    detected_food = priority_match(labels)

    if not detected_food:
        st.warning("Food not found in database")
        st.write("Detected labels:")

        for label in labels[:5]:
            st.write(label.description)

        st.stop()

    # -----------------------------
    # SHOW RESULT
    # -----------------------------
    st.success("Food detected")

    results = df[df["food"].str.lower().isin(detected_food)]

    for _, row in results.iterrows():

        st.subheader(row["food"])

        st.write("Calories:", row["calories"])
        st.write("Protein:", row["protein"])
        st.write("Carbs:", row["carbs"])
        st.write("Fat:", row["fat"])

        st.divider()