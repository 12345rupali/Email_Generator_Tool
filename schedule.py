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
from celery import Celery
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pandas as pd
import os
import pickle
from datetime import datetime, timedelta

# Initialize Flask for webhook handling
app = Flask(__name__)

# Celery configuration
app = Celery("email_scheduler", broker="redis://localhost:6379/0", backend="redis://localhost:6379/0")

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

# Celery task for sending email
@app.task
def send_email_task(sender_email, sender_password, to_address, subject, content):
    send_email(sender_email, sender_password, to_address, subject, content)

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

        st.write(f"Status: {email_metrics.get(row['Email'], {}).get('status', 'Pending')}")
        st.write(f"Sent: {sent_emails} | Failed: {failed_emails} | Pending: {pending_emails} | Scheduled: {scheduled_emails}")
        
# Step 3: Scheduling and Staggering Emails
schedule_time = st.sidebar.time_input("Schedule Emails at Time:")
stagger_interval = st.sidebar.slider("Stagger Emails Every (minutes)", 1, 60, 10)

# Step 4: Schedule or Stagger Emails
if st.sidebar.checkbox("Schedule Emails"):
    for row in csv_rows:
        st.write(f"Scheduling email to {row['First_Name']} {row['Last_Name']} ({row['Email']})")
        # Schedule email for later
        scheduled_time = datetime.combine(datetime.today(), schedule_time)
        if scheduled_time < datetime.now():
            scheduled_time += timedelta(days=1)
        
        send_email_task.apply_async(
            args=[sender_email, sender_password, row['Email'], row['Subject'], row['Content']],
            eta=scheduled_time
        )
        update_email_status("scheduled")
        st.success(f"Email scheduled for {row['First_Name']} {row['Last_Name']} at {scheduled_time.strftime('%H:%M:%S')}")
        
# Stagger emails over intervals
if st.sidebar.checkbox("Stagger Emails"):
    for idx, row in enumerate(csv_rows):
        staggered_time = datetime.now() + timedelta(minutes=(stagger_interval * idx))
        send_email_task.apply_async(
            args=[sender_email, sender_password, row['Email'], row['Subject'], row['Content']],
            eta=staggered_time
        )
        update_email_status("scheduled")
        st.success(f"Email to {row['First_Name']} {row['Last_Name']} scheduled for {staggered_time.strftime('%H:%M:%S')}")
