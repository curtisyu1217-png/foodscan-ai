import streamlit as st
import pandas as pd
from google.cloud import vision
import os

# ---------- GOOGLE VISION ----------
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\USER\Desktop\三高FoodScan\google-vision-key.json"

client = vision.ImageAnnotatorClient()

# ---------- LOAD DATA ----------
df = pd.read_csv("三高FoodScan Dataset/food_data.csv")
food_list = df["ingredient"].str.lower().tolist()

# ---------- FILTER ----------
ignore_labels = [
    "food","ingredient","dish","cuisine",
    "tableware","produce","plant","meal","recipe"
]

# ---------- MAPPING ----------
mapping_dict = {
    "spinach": "vegetable",
    "leaf vegetable": "vegetable",
    "greens": "vegetable",
    "cruciferous vegetables": "vegetable",
    "bok choy": "vegetable",
    "cabbage": "vegetable",
    "lettuce": "vegetable",
    "broccoli": "vegetable",

    "mandu": "dumpling",
    "momo": "dumpling",
    "gyoza": "dumpling",

    "ramen": "noodle",
    "spaghetti": "noodle",
    "udon": "noodle",

    "latte": "coffee",
    "cappuccino": "coffee",

    "yam": "sweet potato",
    "shumai": "siu mai"
}

# ---------- MATCH ----------
def find_best_match(labels):

    labels = [l.lower() for l in labels]

    mapped_labels = []

    for label in labels:

        if label in ignore_labels:
            continue

        if label in mapping_dict:
            mapped_labels.append(mapping_dict[label])
        else:
            mapped_labels.append(label)

    # ---------- PRIORITY SCORE ----------
    priority_scores = {

        # protein
        "fish":5,
        "chicken":5,
        "beef":5,
        "pork":5,
        "duck":5,
        "shrimp":5,
        "egg":5,
        "tofu":5,
        "salmon":5,
        "crab":5,

        # carb
        "rice":4,
        "noodle":4,
        "dumpling":4,
        "bread":4,
        "bun":4,
        "pasta":4,
        "pizza":4,
        "burger":4,
        "congee":4,

        # dish
        "fried rice":3,
        "wonton noodle":3,
        "char siu rice":3,
        "curry chicken":3,

        # vegetable
        "vegetable":2,
        "broccoli":2,
        "spinach":2,
        "cabbage":2,
        "lettuce":2,
        "bok choy":2
    }

    best_food = None
    best_score = 0

    for label in mapped_labels:

        # exact match
        if label in food_list:

            score = priority_scores.get(label, 3)

            if score > best_score:
                best_score = score
                best_food = label

        # partial match
        for food in food_list:

            if label in food or food in label:

                score = priority_scores.get(food, 3)

                if score > best_score:
                    best_score = score
                    best_food = food

    return best_food

# ---------- RISK CALC ----------
def calculate_risk(dm, chol, bp):

    avg = (dm + chol + bp) / 3

    if avg <= 1:
        return "Low Risk 🟢"
    elif avg <= 2:
        return "Moderate Risk 🟡"
    else:
        return "High Risk 🔴"

# ---------- UI ----------
st.title("🍱 三高 FoodScan AI")
st.write("Upload a food image to analyze diabetes, cholesterol and blood pressure risk.")

uploaded_file = st.file_uploader("Upload food image", type=["jpg","png","jpeg"])

if uploaded_file:

    st.image(uploaded_file, caption="Uploaded Food", use_column_width=True)

    content = uploaded_file.read()

    image = vision.Image(content=content)

    response = client.label_detection(image=image)

    labels = [label.description for label in response.label_annotations]

    filtered_labels = [l for l in labels if l.lower() not in ignore_labels]

    matched_food = find_best_match(filtered_labels)

    if matched_food:

        result = df[df["ingredient"].str.lower() == matched_food]

        if not result.empty:

            dm = int(result.iloc[0]["dm_score"])
            chol = int(result.iloc[0]["chol_score"])
            bp = int(result.iloc[0]["bp_score"])
            category = result.iloc[0]["category"]
            notes = result.iloc[0]["notes"]

            risk = calculate_risk(dm, chol, bp)

            st.success(f"Detected Food: {matched_food}")

            st.subheader(risk)

            col1, col2, col3 = st.columns(3)

            col1.metric("DM Risk", dm)
            col2.metric("Cholesterol Risk", chol)
            col3.metric("Blood Pressure Risk", bp)

            st.write("### Category")
            st.write(category)

            st.write("### Notes")
            st.write(notes)

    else:

        st.error("Food not recognized. Try another image.")