import streamlit as st
import pandas as pd
from google.cloud import vision
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime

st.set_page_config(page_title="FoodScan AI", layout="centered")

# =============================
# Load Google Vision + Sheets
# =============================
try:
    key_dict = dict(st.secrets["GOOGLE_VISION_KEY"])
    credentials = service_account.Credentials.from_service_account_info(
        key_dict,
        scopes=[
            "https://www.googleapis.com/auth/cloud-vision",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
    )

    vision_client = vision.ImageAnnotatorClient(credentials=credentials)
    sheets_service = build("sheets", "v4", credentials=credentials)

except Exception as e:
    st.error(f"API not loaded properly: {e}")
    st.stop()

SHEET_ID = "1v583u7Fj2jYVpQc4NtLDrk-M4SxTPlUi0ppdbPf_XZI"
SHEET_NAME = "FoodScan Logs"

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
# Logging function
# =============================
def log_scan(condition, detected_food, risk_level, food_found, confident):
    try:
        row = [[
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            condition,
            detected_food,
            risk_level,
            "Yes" if food_found else "No",
            "Yes" if confident else "No"
        ]]

        sheets_service.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range=f"{SHEET_NAME}!A1",
            valueInputOption="RAW",
            body={"values": row}
        ).execute()

    except:
        pass


# =============================
# Traffic light (clean output)
# =============================
def traffic_light(label, score, category):

    try:
        score = int(score)
    except:
        score = 0

    if score == 0:
        emoji = "🟢"
        risk = "Low Risk"

    elif score == 1:
        emoji = "🟡"
        risk = "Moderate Risk"

    else:
        emoji = "🔴"
        risk = "High Risk"

    st.write(f"{emoji} {label}: {risk} (Score: {score})")

    return risk


# =============================
# Admin dashboard
# =============================
def show_dashboard():

    st.title("📊 Admin Dashboard")

    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=f"{SHEET_NAME}!A1:F1000"
        ).execute()

        values = result.get("values", [])

        if len(values) <= 1:
            st.info("No scan data yet.")
            return

        log_df = pd.DataFrame(values[1:], columns=values[0])

        total_scans = len(log_df)
        found_rate = (log_df["food_found"] == "Yes").sum()
        not_found = (log_df["food_found"] == "No").sum()

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Scans", total_scans)
        col2.metric("Food Detected", found_rate)
        col3.metric("Not Found", not_found)

        st.markdown("---")

        st.subheader("Condition Breakdown")
        st.bar_chart(log_df["condition"].value_counts())

        st.subheader("Top Detected Foods")
        food_counts = log_df[
            log_df["food_found"] == "Yes"
        ]["detected_food"].value_counts().head(10)

        st.bar_chart(food_counts)

        st.subheader("Risk Level Breakdown")
        st.bar_chart(log_df["risk_level"].value_counts())

        st.subheader("Recent Scans")
        st.dataframe(
            log_df.tail(20).iloc[::-1],
            use_container_width=True
        )

        st.markdown("---")

        csv = log_df.to_csv(index=False)

        st.download_button(
            label="Download Full Log",
            data=csv,
            file_name="foodscan_logs.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Could not load dashboard: {e}")


# =============================
# Navigation
# =============================
page = st.sidebar.radio(
    "Navigation",
    ["Food Scanner", "Admin Dashboard"]
)

# =============================
# Dashboard
# =============================
if page == "Admin Dashboard":
    show_dashboard()

# =============================
# Scanner
# =============================
else:

    st.title("FoodScan AI")
    st.write("Upload a food photo to detect health risk")

    st.markdown("---")

    condition = st.radio(
        "Select your condition:",
        [
            "All",
            "Diabetes (DM)",
            "High Cholesterol",
            "High Blood Pressure (BP)"
        ],
        horizontal=True
    )

    CONFIDENCE_THRESHOLD = 0.7

    st.markdown("---")

    uploaded_file = st.file_uploader(
        "Upload food image",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file:

        st.image(uploaded_file)

        content = uploaded_file.read()
        image = vision.Image(content=content)

        response = vision_client.label_detection(image=image)

        confident_labels = [
            l for l in response.label_annotations
            if l.score >= CONFIDENCE_THRESHOLD
        ]

        low_conf_labels = [
            l for l in response.label_annotations
            if l.score < CONFIDENCE_THRESHOLD
        ]

        labels = [
            l.description.lower()
            for l in confident_labels
        ]

        if not labels and low_conf_labels:
            st.warning("Image not clear enough. Try a clearer photo.")
            log_scan(condition, "unclear image", "unknown", False, False)
            st.stop()

        match_row = None
        detected_food = None

        for label in labels:

            match = df[
                df["ingredient"].str.contains(
                    label,
                    case=False,
                    na=False
                )
            ]

            if not match.empty:
                match_row = match.iloc[0]
                detected_food = label
                break

        if match_row is not None:

            st.success(f"Detected Food: {detected_food.title()}")

            st.markdown("---")
            st.subheader("Health Risk Assessment")

            st.write(match_row["notes"])
            st.write("")

            risk_shown = []

            if condition == "All":

                risk_shown.append(
                    traffic_light(
                        "Diabetes (DM)",
                        match_row["dm_score"],
                        match_row["category"]
                    )
                )

                risk_shown.append(
                    traffic_light(
                        "Cholesterol",
                        match_row["chol_score"],
                        match_row["category"]
                    )
                )

                risk_shown.append(
                    traffic_light(
                        "Blood Pressure (BP)",
                        match_row["bp_score"],
                        match_row["category"]
                    )
                )

            elif condition == "Diabetes (DM)":

                risk_shown.append(
                    traffic_light(
                        "Diabetes (DM)",
                        match_row["dm_score"],
                        match_row["category"]
                    )
                )

            elif condition == "High Cholesterol":

                risk_shown.append(
                    traffic_light(
                        "Cholesterol",
                        match_row["chol_score"],
                        match_row["category"]
                    )
                )

            elif condition == "High Blood Pressure (BP)":

                risk_shown.append(
                    traffic_light(
                        "Blood Pressure (BP)",
                        match_row["bp_score"],
                        match_row["category"]
                    )
                )

            log_scan(
                condition,
                detected_food,
                ", ".join(risk_shown),
                True,
                True
            )

        else:

            st.error("Food not found in database.")
            st.write("Detected labels:", labels)

            log_scan(
                condition,
                ", ".join(labels[:3]) if labels else "none",
                "not found",
                False,
                True
            )