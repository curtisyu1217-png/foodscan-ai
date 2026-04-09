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
required_columns = ["ingredient", "dm_score", "chol_score", "bp_score", "category", "notes"]
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
    except Exception as e:
        pass

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
        condition_counts = log_df["condition"].value_counts()
        st.bar_chart(condition_counts)

        st.subheader("Top Detected Foods")
        food_counts = log_df[log_df["food_found"] == "Yes"]["detected_food"].value_counts().head(10)
        st.bar_chart(food_counts)

        st.subheader("Risk Level Breakdown")
        risk_counts = log_df["risk_level"].value_counts()
        st.bar_chart(risk_counts)

        st.subheader("Recent Scans")
        st.dataframe(log_df.tail(20).iloc[::-1], use_container_width=True)

        st.markdown("---")
        csv = log_df.to_csv(index=False)
        st.download_button(
            label="⬇️ Download Full Log as CSV",
            data=csv,
            file_name="foodscan_logs.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Could not load dashboard: {e}")

# =============================
# Page routing
# =============================
page = st.sidebar.radio("Navigation", ["🍱 Food Scanner", "📊 Admin Dashboard"])

if page == "📊 Admin Dashboard":
    show_dashboard()

else:
    st.title("🍱 FoodScan AI")
    st.write("Upload a food photo to detect health risk")

    st.markdown("---")
    st.subheader("Your Condition")
    condition = st.radio(
        "Select your condition to see relevant risk:",
        ["All", "Diabetes (DM)", "High Cholesterol", "High Blood Pressure (BP)"],
        horizontal=True
    )

    CONFIDENCE_THRESHOLD = 0.7

    st.markdown("---")
    uploaded_file = st.file_uploader("Upload food image", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
        content = uploaded_file.read()
        image = vision.Image(content=content)
        response = vision_client.label_detection(image=image)

        confident_labels = [l for l in response.label_annotations if l.score >= CONFIDENCE_THRESHOLD]
        low_conf_labels = [l for l in response.label_annotations if l.score < CONFIDENCE_THRESHOLD]
        labels = [l.description.lower() for l in confident_labels]

        if not labels and low_conf_labels:
            st.warning("Image not clear enough to detect food confidently. Please try a clearer photo.")
            log_scan(condition, "unclear image", "unknown", False, False)
            st.stop()

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

            risk_shown = []
            if condition == "All":
                risk_shown.append(traffic_light("Diabetes (DM)", match_row["dm_score"], match_row["category"]))
                risk_shown.append(traffic_light("Cholesterol", match_row["chol_score"], match_row["category"]))
                risk_shown.append(traffic_light("Blood Pressure (BP)", match_row["bp_score"], match_row["category"]))
            elif condition == "Diabetes (DM)":
                risk_shown.append(traffic_light("Diabetes (DM)", match_row["dm_score"], match_row["category"]))
            elif condition == "High Cholesterol":
                risk_shown.append(traffic_light("Cholesterol", match_row["chol_score"], match_row["category"]))
            elif condition == "High Blood Pressure (BP)":
                risk_shown.append(traffic_light("Blood Pressure (BP)", match_row["bp_score"], match_row["category"]))

            log_scan(condition, detected_food, ", ".join(risk_shown), True, True)

        else:
            st.error("❌ Food not found in database. Try a clearer photo or a different angle.")
            st.write("Detected labels:", labels)
            log_scan(condition, ", ".join(labels[:3]) if labels else "none", "not found", False, True)