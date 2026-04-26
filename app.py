import streamlit as st
import requests
import urllib3
import json
import os
import time

# SSL warning off
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Configuration ---
DB_FILE = "database.json"
BASE_URL = "https://panthers.accbazaar.shop"
HEADERS = {
    "X-API-Key": "panthers_dmfALHZp2bQupCa1OJd--aInjV4skeCSiBTdhA",
    "Content-Type": "application/json"
}

GAME_SERVICES = ["567slot_game", "mbmbet_game", "yonoslot_game", "hirummy_game"]

# --- Database Management ---
def load_db():
    #           
    if not os.path.exists(DB_FILE) or os.stat(DB_FILE).st_size <= 4:
        initial_data = {
            "admin": {
                "password": "admin", 
                "role": "admin", 
                "stats": {g.split('_')[0]: 0 for g in GAME_SERVICES}
            }
        }
        with open(DB_FILE, "w") as f:
            json.dump(initial_data, f, indent=4)
        return initial_data
    
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {"admin": {"password": "admin", "role": "admin", "stats": {g.split('_')[0]: 0 for g in GAME_SERVICES}}}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- API Functions ---
def send_otp(phone, app_name):
    url = f"{BASE_URL}/v1/register/send_otp"
    try:
        res = requests.post(url, headers=HEADERS, json={"phone": phone, "app_name": app_name}, verify=False, timeout=20)
        return res.json()
    except: return {"status": "error", "message": "Connection Timeout"}

def verify_otp(task_id, otp):
    url = f"{BASE_URL}/v1/register/verify_otp"
    try:
        res = requests.post(url, headers=HEADERS, json={"task_id": task_id, "otp": otp}, verify=False, timeout=20)
        return res.json()
    except: return {"status": "error", "message": "Verification Failed"}

def cancel_task_api(task_id):
    url = f"{BASE_URL}/v1/register/cancel_task"
    try:
        res = requests.post(url, headers=HEADERS, json={"task_id": task_id}, verify=False, timeout=10)
        return res.json()
    except: return {"status": "error", "message": "Server Error"}

# --- UI Setup ---
st.set_page_config(page_title="Panther Ultimate Panel", layout="wide")
db = load_db()

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "multi_tasks" not in st.session_state: st.session_state.multi_tasks = {}
if "submitted_tasks" not in st.session_state: st.session_state.submitted_tasks = {}

# --- Login Page ---
if not st.session_state.logged_in:
    st.title(" Tool Login")
    u_id = st.text_input("User ID").strip().lower() #    
    u_pass = st.text_input("Password", type="password").strip()
    
    if st.button("Login", use_container_width=True):
        if u_id in db and db[u_id]["password"] == u_pass:
            st.session_state.logged_in, st.session_state.user, st.session_state.role = True, u_id, db[u_id].get("role", "user")
            st.rerun()
        else: st.error("Invalid Credentials!")

# --- Main Application ---
else:
    user, role = st.session_state.user, st.session_state.role
    st.sidebar.title(f" {user.upper()}")
    nav = st.sidebar.radio("Menu", ["Registration Tool", "Admin Panel"] if role == "admin" else ["Registration Tool"])

    if nav == "Admin Panel":
        st.header(" Admin Control Center")
        tab1, tab2 = st.tabs([" Add New User", " Manage Users"])
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
                if st.button(" Save Changes"):
                    db[target]["password"] = new_p
                    save_db(db); st.success("Updated!"); st.rerun()
                if st.button(" Delete User", type="primary"): del db[target]; save_db(db); st.rerun()

    else:
        st.markdown(f"###  Welcome, {user.upper()}!")
        u_stats = db[user]["stats"]
        st.info(" Stats: " + " | ".join([f"**{k}:** {v}" for k, v in u_stats.items()]))
        st.divider()

        st.subheader(" Send Multi-OTP")
        col_in1, col_in2 = st.columns([2, 1])
        with col_in1:
            selected_games = st.multiselect("Select Apps", GAME_SERVICES, default=[GAME_SERVICES[0]])
        with col_in2:
            phone_val = st.text_input("10-digit Phone Number", key="phone_input").strip()

        if st.button(" SEND ALL OTPs", use_container_width=True):
            if len(phone_val) == 10 and selected_games:
                st.session_state.multi_tasks = {}
                st.session_state.submitted_tasks = {}
                
                status_placeholder = st.empty()
                progress_bar = st.progress(0)
                
                for idx, game in enumerate(selected_games):
                    status_placeholder.markdown(f" **Sending OTP for:** `{game}`...")
                    res = send_otp(phone_val, game)
                    if res.get("status") == "success":
                        st.session_state.multi_tasks[game] = res.get("task_id")
                        st.toast(f" {game} Sent")
                    else: st.error(f" {game}: {res.get('message')}")
                    progress_bar.progress((idx + 1) / len(selected_games))
                    if idx < len(selected_games) - 1: time.sleep(1)
                
                status_placeholder.empty()
                progress_bar.empty()
                st.rerun()
            else: st.warning("Enter valid phone.")

        if st.session_state.multi_tasks:
            st.divider()
            
            # --- Universal Submission ---
            st.markdown("###  Smart Multi-OTP Submission")
            uni_col1, uni_col2 = st.columns([3, 1])
            raw_input = uni_col1.text_input("Enter multiple OTPs", key="universal_otp")
            
            if uni_col2.button(" Quick Submit", use_container_width=True):
                if raw_input:
                    otp_list = [o.strip() for o in raw_input.replace(',', ' ').split() if o.strip()]
                    for current_otp in otp_list:
                        pending_apps = [name for name in st.session_state.multi_tasks.keys() if name not in st.session_state.submitted_tasks]
                        for g_name in pending_apps:
                            if verify_otp(st.session_state.multi_tasks[g_name], current_otp).get("status") == "success":
                                st.session_state.submitted_tasks[g_name] = current_otp
                                sk = g_name.split('_')[0]
                                db[user]["stats"][sk] += 1
                                save_db(db)
                                st.toast(f" {g_name} Success")
                                break
                    st.rerun()

            # --- Individual List ---
            for game_name, task_id in list(st.session_state.multi_tasks.items()):
                is_done = game_name in st.session_state.submitted_tasks
                with st.container():
                    col1, col2, col3 = st.columns([1.5, 2, 1])
                    col1.write(f"**{game_name}**")
                    display_otp = st.session_state.submitted_tasks.get(game_name, "")
                    otp_val = col2.text_input("OTP", value=display_otp, key=f"otp_{game_name}", label_visibility="collapsed", disabled=is_done)
                    
                    if is_done: col3.write(" Done")
                    else:
                        if col3.button("Verify", key=f"v_btn_{game_name}", use_container_width=True):
                            if verify_otp(task_id, otp_val).get("status") == "success":
                                st.session_state.submitted_tasks[game_name] = otp_val
                                sk = game_name.split('_')[0]
                                db[user]["stats"][sk] += 1
                                save_db(db); st.rerun()

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
