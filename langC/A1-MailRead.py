import imaplib 
import email 
from email.header import decode_header 
 
# Function to clean up the email subject 
def clean_subject(subject): 
    if isinstance(subject, bytes): 
        subject = subject.decode() 
    return subject 
 
# Function to fetch emails 
def fetch_emails(username, password, folder="inbox"): 
    # Connect to the email server 
    mail = imaplib.IMAP4_SSL("imap.gmail.com") 
    mail.login(username, password) 
 
    # Select the folder (inbox) 
    mail.select(folder) 
 
    # Search for all emails 
    status, messages = mail.search(None, 'ALL') 
    email_ids = messages[0].split() 
 
    email_list = [] 
     
    # Iterate through email IDs 
    for email_id in email_ids: 
        # Fetch the email by ID 
        res, msg = mail.fetch(email_id, "(RFC822)") 
        msg = email.message_from_bytes(msg[0][1]) 
         
        # Get the subject 
        subject, _ = decode_header(msg["Subject"])[0] 
        subject = clean_subject(subject) 
         
        # Get the sender 
        from_ = msg.get("From") 
         
        # Append to the list 
        email_list.append({"from": from_, "subject": subject}) 
 
    # Logout 
    mail.logout() 
     
    return email_list 
 
# Usage 
username = "deepak@aisalanalytics.com" 
password = "XxxYyy@1"  # Consider using an app password or OAuth2 
emails = fetch_emails(username, password) 
 
# Print the list of emails 
for email in emails: 
    print(f"From: {email['from']}, Subject: {email['subject']}") 