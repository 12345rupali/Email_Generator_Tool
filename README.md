
# Email Generation and Scheduling System

This repository contains an **Email Generation and Scheduling System** built using Python. The system supports email generation via **SendGrid API**, scheduling using **Celery**, and additional functionalities like dashboard analytics. This project is designed to automate email sending and streamline communications.

---

## Table of Contents
   1. [Features](#features)
   2. [Technologies Used](#technologies-used)
   3. [Prerequisites](#prerequisites)
   4. [Setup and Installation](#setup-and-installation)
   5. [Environment Variables](#environment-variables)
   6. [How to Run](#how-to-run)
   7. [API Keys Setup](#api-keys-setup)
   8. [Files Description](#files-description)
   9. [Dashboard](#dashboard)
   10. [Troubleshooting](#troubleshooting)
   11. [License](#license)

---

## Features

1. **User Input Data via CSV**  
   - Easily upload and manage recipient data using a `.csv` file.

2. **Email Integration**  
   - Supports integration with SendGrid and Groq APIs for seamless email delivery.

3. **Custom Editable Box**  
   - Personalize email content dynamically through a user-friendly interface.

4. **Email Generation and Sending**  
   - Automatically generate and send customized emails to recipients.

5. **Email Scheduling and Throttling**  
   - Schedule emails to be sent at specific times and control email sending rate to avoid spam flags.

6. **Real-Time Analytics for Sent Emails**  
   - Get instant insights on sent emails, including delivery success and failure rates.

7. **Email Delivery Tracking with ESP Integration**  
   - Track delivery status and recipient engagement metrics ((Delivered, Opened, Bounced etc.) using SendGrid's API.

8. **Real-Time Dashboard for Email Status and Tracking**  
   - Monitor the status of emails and view tracking information in an intuitive dashboard.


---

## Technologies Used

- **Python**: Core programming language.
- **Streamlit**: For building the dashboard interface.
- **SendGrid**: Email API service.
- **Celery**: For task scheduling.
- **Redis**: Message broker for Celery.
- **Flask**: API backend integration.
- **Pandas**: For CSV and data manipulation.

---

## Prerequisites

Ensure the following are installed on your machine:

1. **Python** (>=3.8)
2. **Redis** (for Celery)
3. A **SendGrid API Key**
4. Optional: **Docker** (for simplified deployment)

---

## Setup and Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/12345rupali/emial_gen.git
   cd email_gen

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate    # For Linux/macOS
   venv\Scripts\activate       # For Windows

3. Install dependencies:
   ```bash
   pip install -r requirements.txt

4. Set up Redis:

   - Install Redis on your machine (Redis Installation Guide)
   - Start the Redis server:
   ```bash
   redis-server

---

## Environment Variables

You need to set the following environment variables for the project to work:

1. **SendGrid API Key**:  
   Set the SendGrid API Key to allow email sending.  

   For Linux/macOS:
   ```bash
   export SENDGRID_API_KEY="your_sendgrid_api_key"
   ```

   For Windows (PowerShell):
   ```bash
   $env:SENDGRID_API_KEY="your_sendgrid_api_key"
   ```


2. **Groq API Key**:
Set the Groq API Key for API integrations.

   For Linux/macOS:
   ```bash
   export GROQ_API_KEY="your_groq_api_key"
   ```
   For Windows:
   ```bash
   $env:GROQ_API_KEY="your_groq_api_key"
   ```

## How to Run
1. **Start the Celery Worker:**
   ```bash
   celery -A app worker --loglevel=info
   ```

2. **Run the Streamlit Server:**
   ```bash
   streamlit run app.py
   ```

## API Keys Setup

**How to Get SendGrid API Key:**

1. Sign up or log in at SendGrid.
2. Go to **Settings** > **API Keys**.
3. Generate a new API key with ```Full Access```.
4. Copy the key and set it as the ```SENDGRID_API_KEY``` environment variable. 

---


**Groq API Key:**

1. Visit Groq API and create an account.
2. Generate an API key.
3. Set it as the ```GROQ_API_KEY``` environment variable.

## Files Description
```app.py:```

- Core application file.
- Manages email generation, scheduling, and sending functionalities.

```schedule.py:```

- Contains Celery tasks for scheduling emails.

```requirements.txt:```

- Lists all dependencies required for the project.

## Dashboard
The dashboard provides the following functionalities:

- Email Analytics: View sent, pending, and failed emails.
- Recipient Management: See the list of recipients loaded from CSV.
- Log Viewer: Check the status of scheduled tasks.


## Troubleshooting
1. Environment Variable Errors:

- Ensure you’ve set SENDGRID_API_KEY correctly.
- Restart your terminal after setting the variables.

2. Redis Connection Issue:

- Make sure Redis is installed and running.
- Verify the ```REDIS_URL```.

3. Celery Task Not Running:

- Check if Celery is correctly pointing to Redis.
- Restart the Celery worker with:
   ```bash
   celery -A app worker --loglevel=info
   ```

4. Streamlit Dashboard Not Launching:

- Verify Streamlit installation with pip list.
- Re-run the dashboard command.









