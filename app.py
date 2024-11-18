import streamlit as st
import csv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask import Flask, request, jsonify
import threading
import time
from langchain_groq import ChatGroq
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pandas as pd
import os
import pickle

# Initialize Flask for webhook handling
app = Flask(__name__)

# API Keys and SMTP Configuration
SENDGRID_API_KEY = "ENTER-YOUR-API-KEY"
GROQ_API_KEY = "ENTER-YOUR-API-KEY"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Initialize email delivery metrics
sent_emails = 0
pending_emails = 0
failed_emails = 0
scheduled_emails = 0
email_metrics = {}

# Function to update email status
def update_email_status(status):
    global sent_emails, pending_emails, failed_emails, scheduled_emails
    if status == "sent":
        sent_emails += 1
    elif status == "failed":
        failed_emails += 1
    elif status == "pending":
        pending_emails += 1
    elif status == "scheduled":
        scheduled_emails += 1


# Initialize Groq LLM
llm = ChatGroq(groq_api_key=GROQ_API_KEY, model="llama3-groq-8b-8192-tool-use-preview")

# Store the rows from the CSV for later reference
csv_rows = []

# Function to generate personalized email content using LLM
def generate_personalized_email(row):
    prompt = f"""
    Generate a professional, personalized email for the following recipient:

    First Name: {row['First_Name']}
    Last Name: {row['Last_Name']}
    Company Name: {row['Company_Name']}
    Location: {row['Location']}

    Subject: {row['Subject']}

    Email Content:
    """
    response = llm.invoke(prompt)
    email_content = response.content.strip()
    return email_content

# Function: Authenticate with Google
def authenticate_with_google():
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds

# Function to send email via Gmail with OAuth2
def send_email_with_oauth2(creds, to_address, subject, content):
    import base64
    from googleapiclient.discovery import build

    try:
        service = build('gmail', 'v1', credentials=creds)
        message = MIMEText(content)
        message['to'] = to_address
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        email_metrics[to_address] = {"status": "Delivered", "opened": "NA", "sent_status": "Sent"}
        return "Email sent successfully via OAuth2!"
    except Exception as e:
        email_metrics[to_address] = {"status": "Failed", "opened": "NA", "sent_status": "Failed"}
        return f"Error: {e}"

# Function to send email via SendGrid
def send_email_via_sendgrid(to_address, subject, content):
    try:
        message = Mail(
            from_email="your-email@example.com",  # Change to your email
            to_emails=to_address,
            subject=subject,
            plain_text_content=content,
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        email_metrics[to_address] = {"status": "Delivered", "opened": "NA", "sent_status": "Sent"}
        return "Email sent successfully via SendGrid!"
    except Exception as e:
        email_metrics[to_address] = {"status": "Failed", "opened": "NA", "sent_status": "Failed"}
        return f"Error: {e}"

# Function to send email via SMTP
def send_email(sender_email, sender_password, to_address, subject, content):
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(sender_email, sender_password)
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = to_address
        message['Subject'] = subject
        message.attach(MIMEText(content, 'plain'))
        server.sendmail(sender_email, to_address, message.as_string())
        server.quit()
        email_metrics[to_address] = {"status": "Delivered", "opened": "NA", "sent_status": "Sent"}
        return "Email sent successfully via SMTP!"
    except Exception as e:
        email_metrics[to_address] = {"status": "Failed", "opened": "NA", "sent_status": "Failed"}
        return f"Error: {e}"

# Flask webhook for SendGrid events
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    for event in data:
        email_id = event.get("email")
        event_type = event.get("event")
        if email_id and event_type:
            # Update status based on event type
            if event_type == "open":
                email_metrics[email_id]["opened"] = "Yes"
            else:
                email_metrics[email_id]["status"] = event_type.capitalize()
    return jsonify({"status": "success"}), 200

# Streamlit UI
st.title("Custom Email Generation and Sending Tool")

# Sidebar setup
st.sidebar.title("Email Configuration")

# Step 1: Email account selection
account_type = st.sidebar.radio("Select Email Account Type:", ["Google", "Outlook", "SendGrid"])
sender_email = ""
sender_password = ""

if account_type == "Google":
    auth_required = st.sidebar.checkbox("Authenticate with Google")
    if auth_required:
        creds = authenticate_with_google()
        if creds:
            st.sidebar.success("Successfully authenticated with Google!")
elif account_type == "Outlook":
    st.sidebar.title("Sender Email Credentials")
    sender_email = st.sidebar.text_input("Sender Email")
    sender_password = st.sidebar.text_input("App Password", type="password")
    if sender_email and sender_password:
        st.sidebar.success("Outlook credentials added successfully!")
elif account_type == "SendGrid":
    SENDGRID_API_KEY = st.sidebar.text_input("Enter SendGrid API Key", type="password")
    if SENDGRID_API_KEY:
        st.sidebar.success("SendGrid API Key added successfully!")

# Step 2: File upload and email generation
# File upload
uploaded_file = st.file_uploader("Upload CSV", type="csv")
if uploaded_file:
    reader = csv.DictReader(uploaded_file.read().decode("utf-8").splitlines())
    csv_rows = [dict(row) for row in reader]

    st.write("## Generated Emails")

    for index, row in enumerate(csv_rows):
        email_content = generate_personalized_email(row)
        email_key = f"email_{index}"

        if email_key not in st.session_state:
            st.session_state[email_key] = {"content": email_content, "editing": False}

        st.write(f"### Email {index + 1}")
        st.write(f"Recipient: {row['First_Name']} {row['Last_Name']} ({row['Email']})")

        if st.session_state[email_key]["editing"]:
            st.session_state[email_key]["content"] = st.text_area(
                f"Edit Email {index + 1}",
                value=st.session_state[email_key]["content"],
                height=200,
                key=f"editable_area_{index}",
            )
            if st.button(f"Done Editing {index + 1}", key=f"done_button_{index}"):
                st.session_state[email_key]["editing"] = False
        else:
            st.text(st.session_state[email_key]["content"])
            if st.button(f"Edit Email {index + 1}", key=f"edit_button_{index}"):
                st.session_state[email_key]["editing"] = True

        if st.button(f"Send Email {index + 1}", key=f"send_button_{index}"):
            if account_type == "Google" and auth_required:
                try:
                    send_status = send_email_with_oauth2(creds, row['Email'], row['Subject'], st.session_state[email_key]["content"])
                    update_email_status("sent")
                    st.success(f"Email sent successfully to {row['Email']} via Google!")
                except Exception as e:
                    st.error(f"Failed to send email to {row['Email']}. Error: {e}")
            elif account_type == "Outlook" and sender_email and sender_password:
                try:
                    send_status = send_email(sender_email, sender_password, row['Email'], row['Subject'], st.session_state[email_key]["content"])
                    update_email_status("sent")
                    st.success(f"Email sent successfully to {row['Email']} via Outlook!")
                except Exception as e:
                    st.error(f"Failed to send email to {row['Email']}. Error: {e}")
            elif account_type == "SendGrid" and SENDGRID_API_KEY:
                try:
                    send_status = send_email_via_sendgrid(row['Email'], row['Subject'], st.session_state[email_key]["content"])
                    update_email_status("sent")
                    st.success(f"Email sent successfully to {row['Email']} via SendGrid!")
                except Exception as e:

                    st.error(f"Failed to send email to {row['Email']}. Error: {e}")
# Real-time analytics section
st.sidebar.title("Real-time Analytics")
real_time_analytics = st.sidebar.checkbox("Enable Real-Time Analytics")

if real_time_analytics:
    st.sidebar.write("Real-Time Email Analytics is now enabled.")

# Email Delivery Metrics
st.sidebar.title("Email Delivery Metrics")
st.sidebar.write(f"Sent Emails: {sent_emails}")
st.sidebar.write(f"Pending Emails: {pending_emails}")
st.sidebar.write(f"Failed Emails: {failed_emails}")
st.sidebar.write(f"Scheduled Emails: {scheduled_emails}")

# Step 3: Display email metrics
show_dashboard = st.checkbox("Show Email Delivery Dashboard")

if show_dashboard:
    st.header("Email Delivery Metrics")

    # Ensure that csv_rows are available for showing metrics
    # if csv_rows:
    # Ensure that csv_rows are available for showing metrics
    if uploaded_file is not None and csv_rows:
        metrics_data = []
        for row in csv_rows:
            email = row['Email']
            company_name = row['Company_Name']
            status = email_metrics.get(email, {}).get("status", "Unknown")
            opened = email_metrics.get(email, {}).get("opened", "NA")
            sent_status = email_metrics.get(email, {}).get("sent_status", "Failed")

            metrics_data.append({
                "Company": company_name,
                "Email": email,
                "Delivery Status": status,
                "Sent Status": sent_status,
                "Opened": opened,
            })

        metrics_df = pd.DataFrame(metrics_data)
        st.table(metrics_df)

        if st.button("Refresh Metrics"):
            st.experimental_rerun()
    else:
        st.write("No metrics to display yet.")

    
# Start Flask server in background thread
def run_flask():
    app.run(port=5000)

threading.Thread(target=run_flask, daemon=True).start()


# Start Flask server in a separate thread for handling SendGrid webhook
if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000)).start()
    st.write("Flask Webhook server is running.")

