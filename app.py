import streamlit as st
import requests
import urllib3
import json
import time
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# SSL warning off
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Configuration ---
BASE_URL = "https://panthers.accbazaar.shop"
HEADERS = {
    "X-API-Key": "panthers_dmfALHZp2bQupCa1OJd--aInjV4skeCSiBTdhA",
    "Content-Type": "application/json"
}
GAME_SERVICES = ["567slot_game", "mbmbet_game", "yonoslot_game", "hirummy_game", "789jackpot_game"]

# --- Google Sheets Connection Setup ---
# এটি database.json এর পরিবর্তে Google Sheet ব্যবহার করবে
conn = st.connection("gsheets", type=GSheetsConnection)

def load_db():
    try:
        # শিট থেকে ডাটা রিড করা (ttl=0 মানে প্রতিবার লেটেস্ট ডাটা আনবে)
        df = conn.read(ttl="0")
        if df is None or df.empty:
            return create_initial_admin()
        
        data = {}
        for _, row in df.iterrows():
            u_id = str(row['user_id']).strip().lower()
            # stats কলামটি টেক্সট হিসেবে থাকে, তাই সেটিকে আবার ডিকশনারি করা হয়
            stats_data = row['stats']
            if isinstance(stats_data, str):
                try:
                    stats_data = json.loads(stats_data)
                except:
                    stats_data = {g.split('_')[0]: 0 for g in GAME_SERVICES}
            
            data[u_id] = {
                "password": str(row['password']),
                "role": row['role'],
                "stats": stats_data
            }
        return data
    except Exception:
        return create_initial_admin()

def create_initial_admin():
    return {
        "admin": {
            "password": "admin", 
            "role": "admin", 
            "stats": {g.split('_')[0]: 0 for g in GAME_SERVICES}
        }
    }

def save_db(data):
    rows = []
    for u_id, details in data.items():
        rows.append({
            "user_id": u_id,
            "password": details["password"],
            "role": details["role"],
            "stats": json.dumps(details["stats"]) # ডাটাবেসে ডিকশনারি সরাসরি সেভ হয় না তাই JSON স্ট্রিং করা
        })
    df = pd.DataFrame(rows)
    # সরাসরি গুগল শিটে ডাটা আপডেট করা
    conn.update(data=df)

# --- API Functions (OTP & Verify) ---
def send_otp(phone, app_name):
    url = f"{BASE_URL}/v1/register/send_otp"
    max_retries = 2
    retry_count = 0
    while retry_count <= max_retries:
        try:
            res = requests.post(url, headers=HEADERS, json={"phone": str(phone), "app_name": app_name}, verify=False, timeout=20)
            response_data = res.json()
            if response_data.get("status") == "success": return response_data
            if "Auth Proxy Error" in response_data.get("message", ""):
                retry_count += 1
                time.sleep(1); continue
            return response_data
        except:
            retry_count += 1
            if retry_count > max_retries: return {"status": "error", "message": "Connection Error"}
            time.sleep(1)

def verify_otp(task_id, otp):
    url = f"{BASE_URL}/v1/register/verify_otp"
    try:
        res = requests.post(url, headers=HEADERS, json={"task_id": str(task_id), "otp": str(otp)}, verify=False, timeout=20)
        return res.json()
    except: return {"status": "error", "message": "Verification Failed"}

# --- UI Setup ---
st.set_page_config(page_title="Panther Ultimate Panel", layout="wide")
db = load_db()

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "multi_tasks" not in st.session_state: st.session_state.multi_tasks = {}
if "submitted_tasks" not in st.session_state: st.session_state.submitted_tasks = {}

# --- Login & Main App Logic ---
if not st.session_state.logged_in:
    st.title("🛡️ Panther Tool Login")
    u_id = st.text_input("User ID").strip().lower()
    u_pass = st.text_input("Password", type="password").strip()
    if st.button("Login", use_container_width=True):
        if u_id in db and db[u_id]["password"] == u_pass:
            st.session_state.logged_in, st.session_state.user, st.session_state.role = True, u_id, db[u_id].get("role", "user")
            st.rerun()
        else: st.error("Invalid Credentials!")
else:
    user, role = st.session_state.user, st.session_state.role
    st.sidebar.title(f"👤 {user.upper()}")
    nav = st.sidebar.radio("Menu", ["Registration Tool", "Admin Panel"] if role == "admin" else ["Registration Tool"])

    if nav == "Admin Panel":
        st.header("⚙️ Admin Control Center")
        tab1, tab2 = st.tabs(["➕ Add New User", "👥 Manage Users"])
        with tab1:
            new_id = st.text_input("New User ID").strip().lower()
            new_pass = st.text_input("New Password").strip()
            if st.button("Create User"):
                if new_id and new_pass:
                    db[new_id] = {"password": new_pass, "role": "user", "stats": {g.split('_')[0]: 0 for g in GAME_SERVICES}}
                    save_db(db); st.success(f"User '{new_id}' created!"); time.sleep(1); st.rerun()
        with tab2:
            users_to_edit = [u for u in db.keys() if db[u].get("role") != "admin"]
            if users_to_edit:
                target = st.selectbox("Select User", users_to_edit)
                new_p = st.text_input("Change Password", value=db[target]["password"])
                updated_stats = {}
                stat_cols = st.columns(len(db[target]["stats"]))
                for i, g_key in enumerate(db[target]["stats"]):
                    updated_stats[g_key] = stat_cols[i].number_input(f"{g_key}", value=int(db[target]["stats"][g_key]), min_value=0)
                if st.button("💾 Save Changes", use_container_width=True):
                    db[target]["password"], db[target]["stats"] = new_p, updated_stats
                    save_db(db); st.success(f"Updated {target}!"); time.sleep(1); st.rerun()
    else:
        st.markdown(f"### 👋 Welcome, {user.upper()}!")
        u_stats = db[user]["stats"]
        st.info("📊 Stats: " + " | ".join([f"**{k}:** {v}" for k, v in u_stats.items()]))
        
        # Registration UI
        phone_val = st.text_input("10-digit Phone Number").strip()
        selected_games = st.multiselect("Select Apps", GAME_SERVICES, default=[GAME_SERVICES[0]])

        if st.button("🚀 SEND ALL OTPs", use_container_width=True):
            if len(phone_val) == 10 and selected_games:
                st.session_state.multi_tasks = {}
                for game in selected_games:
                    res = send_otp(phone_val, game)
                    if res.get("status") == "success":
                        st.session_state.multi_tasks[game] = res.get("task_id")
                st.rerun()

        # OTP Verification Section
        if st.session_state.multi_tasks:
            st.divider()
            for game_name, task_id in list(st.session_state.multi_tasks.items()):
                is_done = game_name in st.session_state.submitted_tasks
                col1, col2, col3 = st.columns([1.5, 2, 1])
                col1.write(f"**{game_name}**")
                otp_val = col2.text_input("OTP", key=f"otp_{game_name}", disabled=is_done)
                if not is_done and col3.button("Verify", key=f"btn_{game_name}"):
                    v_res = verify_otp(task_id, otp_val)
                    if v_res.get("status") == "success":
                        st.session_state.submitted_tasks[game_name] = otp_val
                        sk = game_name.split('_')[0]
                        if sk in db[user]["stats"]: db[user]["stats"][sk] += 1
                        save_db(db); st.rerun()

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
