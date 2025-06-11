import streamlit as st
import json
import hashlib
import os
import pandas as pd
from datetime import datetime

# File paths
USER_FILE = "users.json"
PENDING_FILE = "pending_users.json"
LOG_FILE = "access_log.csv"
DEFAULT_USER = "admin"
DEFAULT_PASSWORD = "08201977Amh"

# Hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Load users
def load_users(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return {}

# Save users
def save_users(users, file_path):
    with open(file_path, "w") as f:
        json.dump(users, f)

# Log access
def log_access(username):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = pd.DataFrame([[now, username]], columns=["Timestamp", "Username"])
    if os.path.exists(LOG_FILE):
        log_entry.to_csv(LOG_FILE, mode="a", header=False, index=False)
    else:
        log_entry.to_csv(LOG_FILE, index=False)

# Register user → stored as pending
def register_user():
    st.subheader("Register New User")
    new_user = st.text_input("New Username")
    new_pass = st.text_input("New Password", type="password")
    confirm_pass = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
        if new_pass != confirm_pass:
            st.error("Passwords do not match.")
            return
        users = load_users(USER_FILE)
        pending = load_users(PENDING_FILE)

        if new_user in users or new_user in pending:
            st.warning("Username already exists or is pending approval.")
        else:
            pending[new_user] = hash_password(new_pass)
            save_users(pending, PENDING_FILE)
            st.success("Registration submitted. Await admin approval.")

# Admin panel to approve/reject pending users
def admin_panel():
    st.subheader("🛡 Admin Approval Panel")

    pending = load_users(PENDING_FILE)
    users = load_users(USER_FILE)

    if not pending:
        st.info("No pending users.")
        return

    for username, password_hash in list(pending.items()):
        cols = st.columns([3, 1, 1])
        cols[0].write(f"🔸 {username}")
        if cols[1].button("✅ Approve", key=f"approve_{username}"):
            users[username] = password_hash
            del pending[username]
            save_users(users, USER_FILE)
            save_users(pending, PENDING_FILE)
            st.success(f"Approved: {username}")
        if cols[2].button("❌ Reject", key=f"reject_{username}"):
            del pending[username]
            save_users(pending, PENDING_FILE)
            st.warning(f"Rejected: {username}")

# Login form
def login_page():
    st.title("🔐 Secure Login")
    menu = st.sidebar.selectbox("Choose Action", ["Login", "Register", "Admin Panel"])

    if menu == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_clicked = st.button("Login")

        if login_clicked:
            users = load_users(USER_FILE)
            pending = load_users(PENDING_FILE)

            if username in pending:
                st.warning("Your registration is still pending admin approval.")
            elif username in users and users[username] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.username = username
                log_access(username)
                st.success(f"Welcome, {username}! Redirecting...")
                st.stop()
            else:
                st.error("Invalid credentials.")

    elif menu == "Register":
        register_user()

    elif menu == "Admin Panel":
        username = st.text_input("Admin Username")
        password = st.text_input("Admin Password", type="password")
        if st.button("Access Panel"):
            users = load_users(USER_FILE)
            if username == DEFAULT_USER and users.get(username) == hash_password(password):
                admin_panel()
            else:
                st.error("Admin credentials invalid.")

# Entry point
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Ensure default admin exists
users = load_users(USER_FILE)
if DEFAULT_USER not in users:
    users[DEFAULT_USER] = hash_password(DEFAULT_PASSWORD)
    save_users(users, USER_FILE)

if st.session_state.logged_in:
    import main
    main.main()
else:
    login_page()
