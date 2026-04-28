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

GAME_SERVICES = ["567slot_game", "mbmbet_game", "yonoslot_game", "hirummy_game", "789jackpot_game"]

# --- Database Management ---
def load_db():
    #             
    if not os.path.exists(DB_FILE) or os.stat(DB_FILE).st_size <= 2:
        initial_data = {
            "admin": {
                "password": "admin", 
                "role": "admin", 
                "stats": {g.split('_')[0]: 0 for g in GAME_SERVICES}
            }
        }
        save_db(initial_data)
        return initial_data
    
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"admin": {"password": "admin", "role": "admin", "stats": {g.split('_')[0]: 0 for g in GAME_SERVICES}}}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- API Functions ---
def send_otp(phone, app_name):
    url = f"{BASE_URL}/v1/register/send_otp"
    try:
        res = requests.post(url, headers=HEADERS, json={"phone": str(phone), "app_name": app_name}, verify=False, timeout=20)
        return res.json()
    except Exception as e: 
        return {"status": "error", "message": f"Connection Error: {str(e)}"}

def verify_otp(task_id, otp):
    url = f"{BASE_URL}/v1/register/verify_otp"
    try:
        # task_id  otp     
        payload = {"task_id": str(task_id), "otp": str(otp)}
        res = requests.post(url, headers=HEADERS, json=payload, verify=False, timeout=20)
        return res.json()
    except Exception as e: 
        return {"status": "error", "message": f"Verification Failed: {str(e)}"}

def cancel_task_api(task_id):
    url = f"{BASE_URL}/v1/register/cancel_task"
    try:
        res = requests.post(url, headers=HEADERS, json={"task_id": str(task_id)}, verify=False, timeout=10)
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
    u_id = st.text_input("User ID").strip().lower()
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
                
                st.write("📊 **Edit User Stats:**")
                updated_stats = {}
                stat_cols = st.columns(len(db[target]["stats"]))
                for i, g_key in enumerate(db[target]["stats"]):
                    updated_stats[g_key] = stat_cols[i].number_input(
                        f"{g_key}", 
                        value=int(db[target]["stats"][g_key]), 
                        min_value=0
                    )
                
                if st.button("💾 Save Changes", use_container_width=True):
                    db[target]["password"] = new_p
                    db[target]["stats"] = updated_stats
                    save_db(db)
                    st.success(f"Updated settings for {target}!")
                    time.sleep(1)
                    st.rerun()
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
            else: st.warning("Enter valid phone number.")

        if st.session_state.multi_tasks:
            st.divider()
            
            # --- Universal Submission Highlighting ---
            st.markdown("---") 
            with st.container(border=True): # এটি পুরো অংশটিকে একটি বক্সের ভেতরে নিয়ে আসবে
                st.markdown("#### ⚡ **Smart Multi-OTP Submission (Priority)**")
                uni_col1, uni_col2 = st.columns([3, 1])
                
                raw_input = uni_col1.text_input(
                    "Enter multiple OTPs (space or comma separated)", 
                    key=f"universal_otp_{len(st.session_state.submitted_tasks)}",
                    placeholder="e.g. 1234 5678 9012"
                )
                
                # বাটনটিকে হাইলাইট করতে এটি ব্যবহার করা হয়েছে
                if uni_col2.button("🚀 Quick Submit", use_container_width=True, type="primary"):
                    if raw_input:
                        otp_list = [o.strip() for o in raw_input.replace(',', ' ').split() if o.strip()]
                        for current_otp in otp_list:
                            pending_apps = [name for name in st.session_state.multi_tasks.keys() if name not in st.session_state.submitted_tasks]
                            for g_name in pending_apps:
                                v_res = verify_otp(st.session_state.multi_tasks[g_name], current_otp)
                                if v_res.get("status") == "success":
                                    st.session_state.submitted_tasks[g_name] = current_otp
                                    sk = g_name.split('_')[0]
                                    if sk in db[user]["stats"]:
                                        db[user]["stats"][sk] += 1
                                    save_db(db)
                                    st.toast(f"  {g_name} Success")
                                    break
                        st.rerun()
            # --- Individual List ---
            for game_name, task_id in list(st.session_state.multi_tasks.items()):
                is_done = game_name in st.session_state.submitted_tasks
                with st.container():
                    col1, col2, col3 = st.columns([1.5, 2, 1])
                    col1.write(f"**{game_name}**")
                    display_otp = st.session_state.submitted_tasks.get(game_name, "")
                    
                    # ওটিপি সাবমিট হয়ে গেলে বক্সের ভেতরেই "OTP ✅" দেখাবে
                    final_value = f"{display_otp} ✅" if is_done else display_otp
                    
                    # ডাইনামিক কি (Key) ব্যবহার করা হয়েছে যাতে সাবমিট করার সাথে সাথে বক্স আপডেট হয়
                    otp_val = col2.text_input(
                        "OTP", 
                        value=final_value, 
                        key=f"otp_box_{game_name}_{len(st.session_state.submitted_tasks)}", 
                        label_visibility="collapsed", 
                        disabled=is_done
                    )
                    # যদি কাজ শেষ না হয়, তবেই ভেরিফাই বাটন দেখাবে
                    if not is_done:
                        if col3.button("Verify", key=f"v_btn_{game_name}", use_container_width=True):
                            with st.spinner("Checking..."):
                                v_res = verify_otp(task_id, otp_val)
                                if v_res.get("status") == "success":
                                    st.session_state.submitted_tasks[game_name] = otp_val
                                    sk = game_name.split('_')[0]
                                    if sk in db[user]["stats"]:
                                        db[user]["stats"][sk] += 1
                                    save_db(db)
                                    st.rerun()
                                else:
                                    st.error(f"Error: {v_res.get('message', 'Invalid OTP')}")


    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
