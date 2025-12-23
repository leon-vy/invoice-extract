import base64
import io
import os
from datetime import datetime
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from invoice_extractor.extractor.sa.retrieve_file_mail.configs import GMAIL_SCOPES, CREDENTIALS_PATH, PATH_DIR

class GmailToDrive:
    def __init__(self, user_to_impers, subjects, drive_folder_id, label_name, local_folder_name):
        self.subjects = subjects if isinstance(subjects, list) else [subjects]  
        self.drive_folder_id = drive_folder_id
        self.label_name = label_name
        self.user_to_impersonate = user_to_impers
        self.local_folder_path = self._create_local_folder(local_folder_name)
        self.gmail_service = self.authenticate_gmail()
        self.drive_service = self.authenticate_drive()
            
    def authenticate_gmail(self):
        try:
            credentials = service_account.Credentials.from_service_account_file(
                CREDENTIALS_PATH,
                scopes=GMAIL_SCOPES
            )
            
            delegated_credentials = credentials.with_subject(self.user_to_impersonate)
            service = build('gmail', 'v1', credentials=delegated_credentials)
            
            # Verify connection by getting user profile
            service.users().getProfile(userId=self.user_to_impersonate).execute()
            return service
            
        except Exception as e:
            print(f"Gmail authentication failed for {self.user_to_impersonate}")
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            if hasattr(e, 'error_details'):
                print(f"Error details: {e.error_details}")
            return None

    def authenticate_drive(self):
        try:
            credentials = service_account.Credentials.from_service_account_file(
                CREDENTIALS_PATH, 
                scopes=GMAIL_SCOPES
            )
            return build('drive', 'v3', credentials=credentials)
        except Exception as e:
            print(f"Error initializing Drive service: {str(e)}")
            return None

    def find_emails_with_subject(self):
        try:
            # Create OR conditions for each subject
            subject_conditions = [f'subject:"{subject}"' for subject in self.subjects]
            subject_query = ' OR '.join(subject_conditions)
            
            # Calculate dates for previous month
            # Get first day of current month
            current_date = datetime.now()
            start_date = current_date.replace(day=1)
            date_filter = f'after:{start_date.strftime("%Y/%m/01")}'
            
            print(f"Date filter: {date_filter}")
            
            # Search for emails with subject that haven't been processed yet
            query = f'({subject_query}) -label:{self.label_name} {date_filter}'
            print(f"Searching with query: {query}")
            
            results = self.gmail_service.users().messages().list(
                userId='me', q=query
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                print(f"No messages found with subjects: {self.subjects}")
                return []
            
            message_ids = [message['id'] for message in messages]
            print(f"Found {len(message_ids)} messages")
            return message_ids

        except Exception as e:
            print(f"An error occurred while searching for the emails: {e}")
            return []

    def get_label_id(self, label_name : str) -> str :
        try:
            results = self.gmail_service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            for label in labels:
                if label['name'] == label_name:
                    return label['id']
            print(f"Label '{label_name}' not found.")
            return None
        except Exception as e:
            print(f"An error occurred while retrieving labels: {e}")
            return None

    def _create_local_folder(self, folder_name : str) -> Path:
        """Create local folder structure for PDF storage if it doesn't exist."""
        # Create base folder in the current directory
        folder_path = os.path.join(PATH_DIR, folder_name)
        
        # Only create folders if they don't exist
        if not Path(PATH_DIR).exists():
            print(f"Creating base directory: {PATH_DIR}")
            Path(PATH_DIR).mkdir(exist_ok=True)
            
        if not Path(folder_path).exists():
            print(f"Creating platform directory: {folder_path}")
            Path(folder_path).mkdir(exist_ok=True)
        else:
            print(f"Using existing directory: {folder_path}")
        
        return Path(folder_path)

    def upload_pdf_attachments_to_drive(self, message_id):
        if not message_id:
            return []

        uploaded_files = []
        try:
            msg = self.gmail_service.users().messages().get(userId='me', id=message_id).execute()
            parts = msg['payload'].get('parts', [])

            for part in parts:
                filename = part.get('filename')
                body = part.get('body', {})
                attachment_id = body.get('attachmentId')

                if filename and filename.lower().endswith('.pdf') and attachment_id:
                    attachment = self.gmail_service.users().messages().attachments().get(
                        userId='me',
                        messageId=message_id,
                        id=attachment_id
                    ).execute()

                    file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))

                    # Save to Google Drive
                    file_metadata = {
                        'name': filename,
                        'parents': [self.drive_folder_id]
                    }
                    media = MediaIoBaseUpload(io.BytesIO(file_data), mimetype='application/pdf', resumable=True)

                    file = self.drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id, name'
                    ).execute()

                    uploaded_files.append(file)
                    print(f"Uploaded '{file.get('name')}' (File ID: {file.get('id')}) to folder: {self.drive_folder_id}")

                    # Save to local folder
                    local_file_path = self.local_folder_path / filename
                    with open(local_file_path, 'wb') as f:
                        f.write(file_data)
                    print(f"Saved '{filename}' to local folder: {self.local_folder_path}")

            # Mark email as processed by adding the label
            label_id = self.get_label_id(self.label_name)
            if not label_id:
                print("Label ID not found. Cannot mark email as processed.")
                return uploaded_files

            modify_body = {
                'addLabelIds': [label_id]
            }

            self.gmail_service.users().messages().modify(
                userId='me',
                id=message_id,
                body=modify_body
            ).execute()

            return uploaded_files
        except Exception as e:
            print(f"An error occurred while uploading attachments to Drive: {e}")
            return []

    def process_emails(self) -> None:
        message_ids = self.find_emails_with_subject()
        for message_id in message_ids:
            self.upload_pdf_attachments_to_drive(message_id)