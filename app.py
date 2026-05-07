import streamlit as st
import requests
import urllib3
import json
import os
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

# --- Google Sheets Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_db():
    try:
        # গুগল শিট থেকে ডাটা রিড করা (ttl=0 মানে লেটেস্ট ডাটা)
        df = conn.read(ttl="0")
        if df is None or df.empty:
            return create_initial_admin()
        
        data = {}
        for _, row in df.iterrows():
            u_id = str(row['user_id']).strip().lower()
            stats_raw = row['stats']
            # Stats ডিকশনারি লোড করার লজিক
            try:
                stats_data = json.loads(stats_raw) if isinstance(stats_raw, str) else stats_raw
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
    return {"admin": {"password": "admin", "role": "admin", "stats": {g.split('_')[0]: 0 for g in GAME_SERVICES}}}

def save_db(data):
    rows = []
    for u_id, details in data.items():
        rows.append({
            "user_id": u_id,
            "password": details["password"],
            "role": details["role"],
            "stats": json.dumps(details["stats"]) # শিটে সেভ করার জন্য টেক্সট করা
        })
    df = pd.DataFrame(rows)
    conn.update(data=df)

# --- API Functions ---
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

# --- Login Page ---
if not st.session_state.logged_in:
    st.title("🛡️ Panther Tool Login")
    u_id = st.text_input("User ID").strip().lower()
    u_pass = st.text_input("Password", type="password").strip()
    if st.button("Login", use_container_width=True):
        if u_id in db and db[u_id]["password"] == u_pass:
            st.session_state.logged_in, st.session_state.user, st.session_state.role = True, u_id, db[u_id].get("role", "user")
            st.rerun()
        else: st.error("Invalid Credentials!")

# --- Main App ---
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
        
        # OTP Send Section (Your Logic)
        col_in1, col_in2 = st.columns([2, 1])
        with col_in1: selected_games = st.multiselect("Select Apps", GAME_SERVICES, default=[GAME_SERVICES[0]])
        with col_in2: phone_val = st.text_input("10-digit Phone", key="phone_input").strip()

        if st.button("🚀 SEND ALL OTPs", use_container_width=True):
            if len(phone_val) == 10 and selected_games:
                st.session_state.multi_tasks, st.session_state.submitted_tasks = {}, {}
                status_placeholder, progress_bar = st.empty(), st.progress(0)
                for idx, game in enumerate(selected_games):
                    status_placeholder.markdown(f"📩 Sending: `{game}`...")
                    res = send_otp(phone_val, game)
                    if res.get("status") == "success":
                        st.session_state.multi_tasks[game] = res.get("task_id")
                    progress_bar.progress((idx + 1) / len(selected_games))
                st.rerun()

        # Smart Multi-Submit Logic (Your Priority Logic)
        if st.session_state.multi_tasks:
            st.divider()
            with st.container(border=True):
                st.markdown("#### ⚡ **Smart Multi-OTP Submission**")
                uni_col1, uni_col2 = st.columns([3, 1])
                raw_input = uni_col1.text_input("OTPs (space separated)", key=f"uni_{len(st.session_state.submitted_tasks)}")
                if uni_col2.button("🚀 Quick Submit", type="primary"):
                    otps = [o.strip() for o in raw_input.replace(',', ' ').split() if o.strip()]
                    for otp in otps:
                        pending = [n for n in st.session_state.multi_tasks if n not in st.session_state.submitted_tasks]
                        for g in pending:
                            v_res = verify_otp(st.session_state.multi_tasks[g], otp)
                            if v_res.get("status") == "success":
                                st.session_state.submitted_tasks[g] = otp
                                db[user]["stats"][g.split('_')[0]] += 1
                                save_db(db); break
                    st.rerun()

            # Individual App List UI
            for g, tid in st.session_state.multi_tasks.items():
                done = g in st.session_state.submitted_tasks
                col1, col2, col3 = st.columns([1.5, 2, 1])
                col1.write(f"**{g}**")
                final_val = f"{st.session_state.submitted_tasks[g]} ✅" if done else ""
                val = col2.text_input("OTP", value=final_val, key=f"box_{g}", disabled=done)
                if not done and col3.button("Verify", key=f"btn_{g}"):
                    v_res = verify_otp(tid, val)
                    if v_res.get("status") == "success":
                        st.session_state.submitted_tasks[g] = val
                        db[user]["stats"][g.split('_')[0]] += 1
                        save_db(db); st.rerun()

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
