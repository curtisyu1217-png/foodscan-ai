import streamlit as st
import pandas as pd
from google.cloud import vision
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime

st.set_page_config(page_title="FoodScan AI", layout="centered")

# =============================
# Language strings
# =============================
LANG = {
    "en": {
        "title": "🍱 FoodScan AI",
        "subtitle": "Upload a food photo to check your health risk",
        "lang_btn": "中文",
        "condition_label": "Select your condition",
        "conditions": ["All", "Diabetes (DM)", "High Cholesterol", "High Blood Pressure (HT)"],
        "upload_label": "Upload a food photo",
        "detected": "Detected Food",
        "risk_title": "Health Risk Assessment",
        "low": "Low Risk",
        "moderate": "Moderate Risk",
        "high": "High Risk",
        "score": "Score",
        "not_found": "Food not found in database. Try a clearer photo or different angle.",
        "unclear": "Image not clear enough. Please try a clearer photo.",
        "labels": "Detected labels",
        "dm": "Diabetes (DM)",
        "chol": "Cholesterol",
        "bp": "Blood Pressure (HT)",
        "api_error": "API not loaded properly",
        "csv_error": "food.csv not found",
        "col_error": "Missing column",
        "admin_password_prompt": "Enter admin password",
        "admin_wrong": "Incorrect password.",
        "admin_hint": "Enter the admin password in the sidebar to view the dashboard.",
        "nav_scanner": "🍱 Food Scanner",
        "nav_admin": "📊 Admin Dashboard",
        "dashboard_title": "📊 Admin Dashboard",
        "total_scans": "Total Scans",
        "food_detected": "Food Detected",
        "not_found_label": "Not Found",
        "condition_breakdown": "Condition Breakdown",
        "top_foods": "Top Detected Foods",
        "risk_breakdown": "Risk Level Breakdown",
        "recent_scans": "Recent Scans",
        "download": "⬇️ Download Full Log as CSV",
        "no_data": "No scan data yet.",
        "disclaimer": "⚠️ For reference only. Not a substitute for medical advice.",
    },
    "zh": {
        "title": "🍱 食物掃描 AI",
        "subtitle": "上傳食物照片，即時查看健康風險",
        "lang_btn": "English",
        "condition_label": "選擇你的健康狀況",
        "conditions": ["全部", "糖尿病", "高膽固醇", "高血壓"],
        "upload_label": "上傳食物照片",
        "detected": "識別食物",
        "risk_title": "健康風險評估",
        "low": "低風險",
        "moderate": "中等風險",
        "high": "高風險",
        "score": "分數",
        "not_found": "資料庫中找不到此食物，請嘗試更清晰的照片或不同角度。",
        "unclear": "圖片不夠清晰，請嘗試更清晰的照片。",
        "labels": "識別標籤",
        "dm": "糖尿病",
        "chol": "膽固醇",
        "bp": "血壓",
        "api_error": "API 載入失敗",
        "csv_error": "找不到 food.csv",
        "col_error": "缺少欄位",
        "admin_password_prompt": "輸入管理員密碼",
        "admin_wrong": "密碼錯誤。",
        "admin_hint": "請在側邊欄輸入管理員密碼以查看數據。",
        "nav_scanner": "🍱 食物掃描",
        "nav_admin": "📊 管理員數據",
        "dashboard_title": "📊 管理員數據",
        "total_scans": "總掃描次數",
        "food_detected": "成功識別",
        "not_found_label": "未能識別",
        "condition_breakdown": "健康狀況分佈",
        "top_foods": "最常識別食物",
        "risk_breakdown": "風險等級分佈",
        "recent_scans": "最近掃描記錄",
        "download": "⬇️ 下載完整記錄 (CSV)",
        "no_data": "暫無掃描數據。",
        "disclaimer": "⚠️ 僅供參考，不能替代專業醫療建議。",
    }
}

# =============================
# Language toggle
# =============================
if "lang" not in st.session_state:
    st.session_state.lang = "en"

def t(key):
    return LANG[st.session_state.lang][key]

# =============================
# Load APIs
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
    st.error(f"{t('api_error')}: {e}")
    st.stop()

SHEET_ID = "1v583u7Fj2jYVpQc4NtLDrk-M4SxTPlUi0ppdbPf_XZI"
SHEET_NAME = "FoodScan Logs"

# =============================
# Load CSV
# =============================
try:
    df = pd.read_csv("food.csv")
except:
    st.error(t("csv_error"))
    st.stop()

df.columns = df.columns.str.lower()
required_columns = ["ingredient", "dm_score", "chol_score", "bp_score", "category", "notes"]
for col in required_columns:
    if col not in df.columns:
        st.error(f"{t('col_error')}: {col}")
        st.stop()

# =============================
# Logging
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
# Traffic light
# =============================
def traffic_light(label, score):
    try:
        score = float(score)
    except:
        score = 0

    if score <= 3:
        color = "#2ecc71"
        emoji = "🟢"
        risk = t("low")
    elif score <= 6:
        color = "#f39c12"
        emoji = "🟡"
        risk = t("moderate")
    else:
        color = "#e74c3c"
        emoji = "🔴"
        risk = t("high")

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
            <span style="float: right; font-size: 14px; color: {color}; font-weight: bold;">{risk} ({t('score')}: {int(score)})</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    return risk

# =============================
# Admin dashboard
# =============================
def show_dashboard():
    st.title(t("dashboard_title"))
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=f"{SHEET_NAME}!A1:F1000"
        ).execute()
        values = result.get("values", [])

        if len(values) <= 1:
            st.info(t("no_data"))
            return

        log_df = pd.DataFrame(values[1:], columns=values[0])

        col1, col2, col3 = st.columns(3)
        col1.metric(t("total_scans"), len(log_df))
        col2.metric(t("food_detected"), (log_df["food_found"] == "Yes").sum())
        col3.metric(t("not_found_label"), (log_df["food_found"] == "No").sum())

        st.markdown("---")
        st.subheader(t("condition_breakdown"))
        st.bar_chart(log_df["condition"].value_counts())

        st.subheader(t("top_foods"))
        st.bar_chart(log_df[log_df["food_found"] == "Yes"]["detected_food"].value_counts().head(10))

        st.subheader(t("risk_breakdown"))
        st.bar_chart(log_df["risk_level"].value_counts())

        st.subheader(t("recent_scans"))
        st.dataframe(log_df.tail(20).iloc[::-1], use_container_width=True)

        st.markdown("---")
        st.download_button(
            label=t("download"),
            data=log_df.to_csv(index=False),
            file_name="foodscan_logs.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"Could not load dashboard: {e}")

# =============================
# Page routing
# =============================
page = st.sidebar.radio("Navigation", [t("nav_scanner"), t("nav_admin")])

st.sidebar.markdown("---")
if st.sidebar.button(t("lang_btn")):
    st.session_state.lang = "zh" if st.session_state.lang == "en" else "en"
    st.rerun()

if page == t("nav_admin"):
    password = st.sidebar.text_input(t("admin_password_prompt"), type="password")
    if password == "foodscan2024":
        show_dashboard()
    elif password == "":
        st.info(t("admin_hint"))
    else:
        st.error(t("admin_wrong"))

else:
    st.title(t("title"))
    st.write(t("subtitle"))
    st.markdown("---")

    st.subheader(t("condition_label"))
    conditions = t("conditions")
    condition = st.radio("", conditions, horizontal=True, label_visibility="collapsed")

    CONFIDENCE_THRESHOLD = 0.7

    st.markdown("---")
    uploaded_file = st.file_uploader(t("upload_label"), type=["jpg", "jpeg", "png"])

    if uploaded_file:
        st.image(uploaded_file, caption=t("upload_label"), use_column_width=True)
        content = uploaded_file.read()
        image = vision.Image(content=content)
        response = vision_client.label_detection(image=image)

        confident_labels = [l for l in response.label_annotations if l.score >= CONFIDENCE_THRESHOLD]
        low_conf_labels = [l for l in response.label_annotations if l.score < CONFIDENCE_THRESHOLD]
        labels = [l.description.lower() for l in confident_labels]

        if not labels and low_conf_labels:
            st.warning(t("unclear"))
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
            st.success(f"✅ {t('detected')}: **{detected_food.title()}**")
            st.markdown("---")
            st.subheader(t("risk_title"))
            st.caption(match_row["notes"])
            st.markdown(" ")

            risk_shown = []
            if condition == conditions[0]:
                risk_shown.append(traffic_light(t("dm"), match_row["dm_score"]))
                risk_shown.append(traffic_light(t("chol"), match_row["chol_score"]))
                risk_shown.append(traffic_light(t("bp"), match_row["bp_score"]))
            elif condition == conditions[1]:
                risk_shown.append(traffic_light(t("dm"), match_row["dm_score"]))
            elif condition == conditions[2]:
                risk_shown.append(traffic_light(t("chol"), match_row["chol_score"]))
            elif condition == conditions[3]:
                risk_shown.append(traffic_light(t("bp"), match_row["bp_score"]))

            st.markdown("---")
            st.caption(t("disclaimer"))
            log_scan(condition, detected_food, ", ".join(risk_shown), True, True)

        else:
            st.error(t("not_found"))
            st.caption(f"{t('labels')}: {', '.join(labels)}")
            log_scan(condition, ", ".join(labels[:3]) if labels else "none", "not found", False, True)