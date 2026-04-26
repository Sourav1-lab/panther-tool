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
    if not os.path.exists(DB_FILE):
        initial_data = {"admin": {"password": "admin", "role": "admin", "stats": {"567slot": 0, "mbmbet": 0, "yonoslot": 0, "hirummy": 0}}}
        save_db(initial_data)
        return initial_data
    with open(DB_FILE, "r") as f: return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

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
    st.title("🔐 Tool Login")
    u_id = st.text_input("User ID").strip()
    u_pass = st.text_input("Password", type="password").strip()
    if st.button("Login", use_container_width=True):
        if u_id in db and db[u_id]["password"] == u_pass:
            st.session_state.logged_in, st.session_state.user, st.session_state.role = True, u_id, db[u_id].get("role", "user")
            st.rerun()
        else: st.error("Invalid Credentials!")

# --- Main Application ---
else:
    user, role = st.session_state.user, st.session_state.role
    st.sidebar.title(f"👤 {user.upper()}")
    nav = st.sidebar.radio("Menu", ["Registration Tool", "Admin Panel"] if role == "admin" else ["Registration Tool"])

    if nav == "Admin Panel":
        st.header("🛠️ Admin Control Center")
        tab1, tab2 = st.tabs(["➕ Add New User", "⚙️ Manage Users"])
        with tab1:
            new_id, new_pass = st.text_input("New User ID"), st.text_input("New Password")
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
                for i, g in enumerate(db[target]["stats"]):
                    updated_stats[g] = stat_cols[i].number_input(f"{g}", value=db[target]["stats"][g], min_value=0)
                if st.button("💾 Save Changes"):
                    db[target]["password"], db[target]["stats"] = new_p, updated_stats
                    save_db(db); st.success("Updated!"); st.rerun()
                if st.button("🗑️ Delete User", type="primary"): del db[target]; save_db(db); st.rerun()

    else:
        st.markdown(f"""<div style="background-color:#f0f2f6; padding:12px; border-radius:10px; border-left: 6px solid #FF4B4B;">
                <h2 style="color:#222; margin:0;">👤 Welcome, {user.upper()}!</h2></div>""", unsafe_allow_html=True)
        
        u_stats = db[user]["stats"]
        st.info("📊 Stats: " + " | ".join([f"**{k}:** {v}" for k, v in u_stats.items()]))
        st.divider()

        st.subheader("🚀 Send Multi-OTP")
        col_in1, col_in2 = st.columns([2, 1])
        with col_in1:
            selected_games = st.multiselect("Select Apps", GAME_SERVICES, default=[GAME_SERVICES[0]])
        with col_in2:
            phone_val = st.text_input("10-digit Phone Number", key="phone_input").strip()

        if st.button("🚀 SEND ALL OTPs", use_container_width=True):
            if len(phone_val) == 10 and selected_games:
                st.session_state.multi_tasks = {}
                st.session_state.submitted_tasks = {}
                for key in list(st.session_state.keys()):
                    if key.startswith("otp_"): st.session_state[key] = ""
                if "universal_otp" in st.session_state: st.session_state.universal_otp = ""

                status_placeholder = st.empty()
                progress_bar = st.progress(0)
                
                for idx, game in enumerate(selected_games):
                    status_placeholder.markdown(f"⏳ **Sending OTP for:** `{game}`...")
                    res = send_otp(phone_val, game)
                    if res.get("status") == "success":
                        st.session_state.multi_tasks[game] = res.get("task_id")
                        st.toast(f"✅ {game} Sent")
                    else: st.error(f"❌ {game}: {res.get('message')}")
                    progress_bar.progress((idx + 1) / len(selected_games))
                    if idx < len(selected_games) - 1: time.sleep(2)
                
                status_placeholder.empty()
                progress_bar.empty()
                st.rerun()
            else: st.warning("Enter valid phone.")

        if st.session_state.multi_tasks:
            st.divider()
            pending_count = len(st.session_state.multi_tasks)
            c_info, c_cancel_all = st.columns([3, 1])
            c_info.subheader(f"⏳ Active Tasks: {pending_count}")
            if c_cancel_all.button("🗑️ Cancel All Tasks", type="secondary", use_container_width=True):
                for g, t in list(st.session_state.multi_tasks.items()): cancel_task_api(t)
                st.session_state.multi_tasks, st.session_state.submitted_tasks = {}, {}
                st.rerun()

            # --- Ultimate Universal Multi-OTP Submission ---
            st.markdown("### 🌟 Smart Multi-OTP Submission")
            uni_col1, uni_col2 = st.columns([3, 1])
            raw_input = uni_col1.text_input("Enter multiple OTPs (split by space or comma)", key="universal_otp", placeholder="Example: 1111 2222, 3333")
            
            if uni_col2.button("⚡ Quick Submit", use_container_width=True):
                if raw_input:
                    # সব ওটিপি আলাদা করে লিস্টে নেওয়া
                    otp_list = [o.strip() for o in raw_input.replace(',', ' ').split() if o.strip()]
                    found_any = False
                    
                    with st.spinner(f"Testing {len(otp_list)} OTPs against pending apps..."):
                        # প্রতিটি ওটিপি-র জন্য আলাদা লুপ
                        for current_otp in otp_list:
                            # প্রতিবার ফ্রেশ ভাবে চেক করবে কোন অ্যাপগুলো এখনো সাবমিট হয়নি
                            current_pending_apps = [name for name in st.session_state.multi_tasks.keys() 
                                                   if name not in st.session_state.submitted_tasks]
                            
                            for g_name in current_pending_apps:
                                t_id = st.session_state.multi_tasks[g_name]
                                try:
                                    v_res = verify_otp(t_id, current_otp)
                                    if v_res.get("status") == "success":
                                        st.session_state.submitted_tasks[g_name] = current_otp
                                        st.session_state[f"otp_{g_name}"] = current_otp
                                        
                                        # ডাটাবেস আপডেট
                                        stat_key = g_name.split('_')[0]
                                        if stat_key in db[user]["stats"]:
                                            db[user]["stats"][stat_key] += 1
                                            save_db(db)
                                        
                                        st.toast(f"✅ Success: {g_name}")
                                        found_any = True
                                        # এই ওটিপিটি একটি অ্যাপে মিলে গেছে, তাই এটি দিয়ে আর চেক করার দরকার নেই
                                        break 
                                except:
                                    continue
                    
                    if found_any:
                        st.success("Successfully processed matching OTPs!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ No matching OTP found in your list.")
                else: st.warning("Enter OTPs first.")

            st.write("---")

            # --- Individual Task List ---
            for game_name, task_id in list(st.session_state.multi_tasks.items()):
                is_submitted = game_name in st.session_state.submitted_tasks
                with st.container():
                    col1, col2, col3, col4 = st.columns([1.5, 2, 1, 0.5])
                    col1.write(f"**{game_name}**")
                    display_otp = st.session_state.submitted_tasks.get(game_name, "") if is_submitted else st.session_state.get(f"otp_{game_name}", "")
                    otp_val = col2.text_input("OTP", value=display_otp, key=f"otp_{game_name}", label_visibility="collapsed", disabled=is_submitted)
                    
                    with col3:
                        if is_submitted: st.markdown("🟢 **Submitted**")
                        else:
                            if st.button("✔️ Verify", key=f"v_btn_{game_name}", use_container_width=True):
                                if otp_val:
                                    v_res = verify_otp(task_id, otp_val)
                                    if v_res.get("status") == "success":
                                        st.session_state.submitted_tasks[game_name] = otp_val
                                        stat_key = game_name.split('_')[0]
                                        if stat_key in db[user]["stats"]:
                                            db[user]["stats"][stat_key] += 1
                                            save_db(db)
                                        st.rerun()
                                    else: st.error(f"❌ {v_res.get('message', 'Wrong OTP')}")
                                else: st.warning("Enter OTP!")
                    with col4:
                        if not is_submitted:
                            if st.button("❌", key=f"c_btn_{game_name}"):
                                cancel_task_api(task_id)
                                del st.session_state.multi_tasks[game_name]
                                st.rerun()

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()