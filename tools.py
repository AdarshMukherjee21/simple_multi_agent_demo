import os
import json
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain_core.tools import tool
from config import POLICY_FILE, LEAVE_FILE, CONTACTS_FILE, DRAFTS_DIR

@tool
def lookup_policy(query: str) -> str:
    """Fetches the contents of the company policy document."""
    print(f"\n>>> [TOOL EXECUTION] lookup_policy called with query: '{query}'")
    try:
        with open(POLICY_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            print(f">>> [TOOL SUCCESS] lookup_policy read {len(content)} characters.")
            return content
    except Exception as e:
        print(f">>> [TOOL ERROR] lookup_policy failed: {str(e)}")
        return f"Tool Error reading policy file: {str(e)}"

@tool
def lookup_leave(query: str) -> str:
    """Fetches the contents of the company leave policy document."""
    print(f"\n>>> [TOOL EXECUTION] lookup_leave called with query: '{query}'")
    try:
        with open(LEAVE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            print(f">>> [TOOL SUCCESS] lookup_leave read {len(content)} characters.")
            return content
    except Exception as e:
        print(f">>> [TOOL ERROR] lookup_leave failed: {str(e)}")
        return f"Tool Error reading leave file: {str(e)}"

@tool
def fetch_email_id(name: str) -> str:
    """Fetches the email ID for a given contact name."""
    print(f"\n>>> [TOOL EXECUTION] fetch_email_id called for name: '{name}'")
    try:
        with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
            contacts = json.load(f)
        
        email = contacts.get(name)
        if email:
            print(f">>> [TOOL SUCCESS] Found email for {name}: {email}")
            return email
        else:
            print(f">>> [TOOL WARNING] Contact {name} not found in contacts.json")
            return f"Error: Contact {name} not found in contacts.json"
    except Exception as e:
        print(f">>> [TOOL ERROR] fetch_email_id failed: {str(e)}")
        return f"Tool Error reading contacts: {str(e)}"

@tool
def write_email(subject: str, body: str, recipient_email: str) -> str:
    """Drafts an email and saves it to the drafts directory with a UUID."""
    print(f"\n>>> [TOOL EXECUTION] write_email called.")
    print(f"    Recipient: {recipient_email}")
    print(f"    Subject: {subject}")
    try:
        draft_id = str(uuid.uuid4())
        draft_path = os.path.join(DRAFTS_DIR, f"{draft_id}.txt")
        
        content = f"To: {recipient_email}\nSubject: {subject}\n\n{body}"
        
        with open(draft_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f">>> [TOOL SUCCESS] Email saved to {draft_path}")
        return f"Email drafted successfully. Draft ID: {draft_id}, Path: {draft_path}"
    except Exception as e:
        print(f">>> [TOOL ERROR] write_email failed: {str(e)}")
        return f"Tool Error drafting email: {str(e)}"

@tool
def send_email(recipient_email: str, subject: str, body: str) -> str:
    """Sends an email using SMTP credentials from environment variables."""
    print(f"\n>>> [TOOL EXECUTION] send_email called.")
    print(f"    Recipient: {recipient_email}")
    
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    
    if not sender_email or not sender_password:
        print(">>> [TOOL ERROR] Missing SENDER_EMAIL or SENDER_PASSWORD in environment.")
        return "Error: SENDER_EMAIL or SENDER_PASSWORD are not set in the environment."

    try:
        print(">>> [TOOL INFO] Constructing MIME message and attempting SMTP connection...")
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # FIXED: Using Gmail's SMTP server instead of mailtrap
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        print(">>> [TOOL SUCCESS] Email dispatched successfully.")
        return "Email sent successfully."
    except Exception as e:
        print(f">>> [TOOL ERROR] send_email failed: {str(e)}")
        return f"Tool Error sending email: {str(e)}"