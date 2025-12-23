from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import List
from pathlib import Path
import os

PATH_DIR = os.path.join(Path(__file__).parent.parent.parent.parent, "data", "invoices")

# CONSTANTS
USER_EMAIL_GGL : str = "invoices@virtuology.com"
USER_EMAIL_OTHERS : str = "finance@programmads.com"

EMAILS: List[str] = [USER_EMAIL_OTHERS, USER_EMAIL_GGL]

GMAIL_SCOPES : List[str]= [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
CREDENTIALS_PATH : str = os.path.join(Path(__file__).parent.parent.parent.parent,'service_account_pads.json')

PARENT_FOLDER_ID : str = '10PwaF9HLICziXaSKNQBAmdyi5WB0QLok'


def authenticate_drive() -> None:
    try:
        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_PATH,
            scopes=GMAIL_SCOPES
        )
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        print(f"Error initializing Drive service: {str(e)}")
        return None

def create_folder_structure():
    drive_service = authenticate_drive()
    if not drive_service:
        return {}

    # Create month folder for previous month
    today = datetime.now()
    first_of_month = today.replace(day=1)
    prev_month = first_of_month - timedelta(days=1)
    month_folder_name = prev_month.strftime("%B%Y")
    
    # Check if month folder already exists
    month_folder_query = f"name='{month_folder_name}' and mimeType='application/vnd.google-apps.folder' and '{PARENT_FOLDER_ID}' in parents and trashed=false"
    month_folders = drive_service.files().list(q=month_folder_query, fields='files(id,name)').execute()
    
    if month_folders.get('files'):
        # Month folder exists, use the first one
        month_folder_id = month_folders['files'][0]['id']
        print(f"Month folder '{month_folder_name}' already exists with ID: {month_folder_id}")
    else:
        # Create new month folder
        month_folder_metadata = {
            'name': month_folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [PARENT_FOLDER_ID]
        }
        
        month_folder = drive_service.files().create(
            body=month_folder_metadata,
            fields='id'
        ).execute()
        month_folder_id = month_folder.get('id')
        print(f"Created new month folder '{month_folder_name}' with ID: {month_folder_id}")

    folder_ids = {}
    platforms = ['SA360', 'DV360', 'CM360', 'Analytics', 'ADSP', 'Xandr']
    
    for platform in platforms:
        platform_folder_query = f"name='{platform}' and mimeType='application/vnd.google-apps.folder' and '{month_folder_id}' in parents and trashed=false"
        platform_folders = drive_service.files().list(q=platform_folder_query, fields='files(id,name)').execute()
        
        if platform_folders.get('files'):
            # Platform folder exists, use the first one
            platform_folder_id = platform_folders['files'][0]['id']
            print(f"Platform folder '{platform}' already exists with ID: {platform_folder_id}")
        else:
            # Create new platform folder
            platform_metadata = {
                'name': platform,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [month_folder_id]
            }
            
            platform_folder = drive_service.files().create(
                body=platform_metadata,
                fields='id'
            ).execute()
            platform_folder_id = platform_folder.get('id')
            print(f"Created new platform folder '{platform}' with ID: {platform_folder_id}")
        
        folder_ids[platform] = platform_folder_id
    
    return folder_ids


folder_ids = create_folder_structure()


MAPPING_INVOICES_TO_DRIVE_GGL = [
    {'drive_name': 'SA360', 'subject': 'Your Google Search Ads 360 documents are ready', 'folder_id': folder_ids.get('SA360'), 'label_tag': 'Invoice saved to Drive', 'local_folder': 'sa360'}, 
]