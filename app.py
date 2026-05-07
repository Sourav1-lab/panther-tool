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

# --- Google Sheets Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_db():
    try:
        # রিয়েল-টাইম ডাটা রিড করার জন্য
        df = conn.read(ttl="0")
        if df is None or df.empty:
            return create_initial_admin()
        
        data = {}
        for _, row in df.iterrows():
            u_id = str(row['user_id']).strip().lower()
            stats_raw = row['stats']
            try:
                # টেক্সট থেকে ডিকশনারিতে রূপান্তর
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

def save_db(data):
    rows = []
    for u_id, details in data.items():
        rows.append({
            "user_id": u_id,
            "password": details["password"],
            "role": details["role"],
            "stats": json.dumps(details["stats"])
        })
    df = pd.DataFrame(rows)
    # গুগল শিটে ডাটা সেভ করার লজিক
    conn.update(data=df)

def create_initial_admin():
    return {"admin": {"password": "admin", "role": "admin", "stats": {g.split('_')[0]: 0 for g in GAME_SERVICES}}}

# --- API Functions ---
def send_otp(phone, app_name):
    url = f"{BASE_URL}/v1/register/send_otp"
    try:
        res = requests.post(url, headers=HEADERS, json={"phone": str(phone), "app_name": app_name}, verify=False, timeout=20)
        return res.json()
    except: return {"status": "error", "message": "Connection Error"}

def verify_otp(task_id, otp):
    url = f"{BASE_URL}/v1/register/verify_otp"
    try:
        res = requests.post(url, headers=HEADERS, json={"task_id": str(task_id), "otp": str(otp)}, verify=False, timeout=20)
        return res.json()
    except: return {"status": "error", "message": "Verify Failed"}

# --- UI Setup ---
st.set_page_config(page_title="Panther Ultimate Panel", layout="wide")
db = load_db()

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "multi_tasks" not in st.session_state: st.session_state.multi_tasks = {}
if "submitted_tasks" not in st.session_state: st.session_state.submitted_tasks = {}

# --- Login & UI Logic ---
if not st.session_state.logged_in:
    st.title("🛡️ Panther Tool Login")
    u_id = st.text_input("User ID").strip().lower()
    u_pass = st.text_input("Password", type="password")
    if st.button("Login", use_container_width=True):
        if u_id in db and db[u_id]["password"] == u_pass:
            st.session_state.logged_in, st.session_state.user, st.session_state.role = True, u_id, db[u_id]["role"]
            st.rerun()
        else: st.error("Invalid Credentials!")
else:
    user, role = st.session_state.user, st.session_state.role
    st.sidebar.title(f"👤 {user.upper()}")
    
    # Navigation
    nav = st.sidebar.radio("Menu", ["Registration Tool", "Admin Panel"] if role == "admin" else ["Registration Tool"])

    if nav == "Admin Panel":
        st.header("⚙️ Admin Control Center")
        tab1, tab2 = st.tabs(["➕ Add New User", "👥 Manage Users"])
        with tab1:
            new_id = st.text_input("New User ID").strip().lower()
            new_pass = st.text_input("New Password").strip()
            if st.button("Create User"):
                db[new_id] = {"password": new_pass, "role": "user", "stats": {g.split('_')[0]: 0 for g in GAME_SERVICES}}
                save_db(db); st.success(f"User created!"); time.sleep(1); st.rerun()
        with tab2:
            targets = [u for u in db.keys() if db[u]["role"] != "admin"]
            if targets:
                target = st.selectbox("Select User", targets)
                new_p = st.text_input("Change Password", value=db[target]["password"])
                if st.button("💾 Save Changes"):
                    db[target]["password"] = new_p
                    save_db(db); st.success("Updated!"); time.sleep(1); st.rerun()

    else:
        st.markdown(f"### 👋 Welcome, {user.upper()}!")
        u_stats = db[user]["stats"]
        st.info("📊 Stats: " + " | ".join([f"**{k}:** {v}" for k, v in u_stats.items()]))
        
        # ওটিপি পাঠানোর ইন্টারফেস
        col_in1, col_in2 = st.columns([2, 1])
        with col_in1: selected_games = st.multiselect("Select Apps", GAME_SERVICES, default=[GAME_SERVICES[0]])
        with col_in2: phone_val = st.text_input("10-digit Phone", key="p_in").strip()

        if st.button("🚀 SEND ALL OTPs", use_container_width=True):
            if len(phone_val) == 10 and selected_games:
                st.session_state.multi_tasks, st.session_state.submitted_tasks = {}, {}
                for g in selected_games:
                    res = send_otp(phone_val, g)
                    if res.get("status") == "success": st.session_state.multi_tasks[g] = res.get("task_id")
                st.rerun()

        # --- Smart Multi-Submit লজিক (আপনার অরিজিনাল ফাইল থেকে) ---
        if st.session_state.multi_tasks:
            st.divider()
            with st.container(border=True):
                st.markdown("#### ⚡ **Smart Multi-OTP Submission**")
                uni_col1, uni_col2 = st.columns([3, 1])
                raw_input = uni_col1.text_input("Enter OTPs (space/comma separated)", key=f"uni_{len(st.session_state.submitted_tasks)}")
                
                if uni_col2.button("🚀 Quick Submit", type="primary", use_container_width=True):
                    otp_list = [o.strip() for o in raw_input.replace(',', ' ').split() if o.strip()]
                    for current_otp in otp_list:
                        pending = [n for n in st.session_state.multi_tasks if n not in st.session_state.submitted_tasks]
                        for g_name in pending:
                            v_res = verify_otp(st.session_state.multi_tasks[g_name], current_otp)
                            if v_res.get("status") == "success":
                                st.session_state.submitted_tasks[g_name] = current_otp
                                db[user]["stats"][g_name.split('_')[0]] += 1
                                save_db(db)
                                break
                    st.rerun()

            # --- ম্যানুয়াল ভেরিফাই বাটন এবং হাইলাইট লজিক ---
            for g_name, tid in st.session_state.multi_tasks.items():
                is_done = g_name in st.session_state.submitted_tasks
                with st.container():
                    c1, c2, c3 = st.columns([1.5, 2, 1])
                    c1.write(f"**{g_name}**")
                    display_val = f"{st.session_state.submitted_tasks[g_name]} ✅" if is_done else ""
                    
                    otp_val = c2.text_input("OTP", value=display_val, key=f"in_{g_name}", disabled=is_done, label_visibility="collapsed")
                    
                    if not is_done: # কাজ শেষ না হলে তবেই বাটন দেখাবে
                        if c3.button("Verify", key=f"btn_{g_name}", use_container_width=True):
                            v_res = verify_otp(tid, otp_val)
                            if v_res.get("status") == "success":
                                st.session_state.submitted_tasks[g_name] = otp_val
                                db[user]["stats"][g_name.split('_')[0]] += 1
                                save_db(db)
                                st.rerun()
                            else: st.error("Wrong OTP")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
