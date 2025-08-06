from googleapiclient.discovery import build
from google.cloud import secretmanager
from google.oauth2 import service_account
from google.auth import compute_engine
import traceback
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseUpload
from dotenv import load_dotenv
import json
from io import BytesIO
import base64
from utils.googleSheetHandler import GoogleSheetHandler
import os

load_dotenv()

class DriveHandler:
    def __init__(self, serviceAccountJson : dict = None):
        self.credentials = self.getCredentials(serviceAccountJson)
        self.service = build("drive", "v3", credentials=self.credentials)
        self.sender_email = self.credentials.service_account_email if hasattr(self.credentials, 'service_account_email') else None
        # print(f"DriveHandler initialized with sender email: {self.sender_email}")
        self.googleSheetHandler = GoogleSheetHandler(self.credentials)

    def getCredentials(self, serviceAccountJson : dict = None):
        """
        Get the credentials for the Gmail API.
        Args:
            serviceAccountJson (dict, optional): The service account JSON credentials.
        Returns:
            Credentials: The credentials for the Gmail API.
        """
        try:
            if not serviceAccountJson:
                with open('var/bigquery_service_account.json', 'r') as file:
                    print("Using service account file")
                    serviceAccountJson = json.load(file)
            return service_account.Credentials.from_service_account_info(
                serviceAccountJson,
                scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
            )
        except Exception as e:
            print("Service account file not found. Using default credentials.")
            try:
                credentials = os.environ.get('SERVICE_ACCOUNT_FILE', '{}')
                credentials = json.loads(credentials)
                print("Using service account environment variable")
                return service_account.Credentials.from_service_account_info(
                    credentials,
                    scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
                )
            except Exception as e:
                print('Using default credentials')
                return compute_engine.Credentials(scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets'])

    def uploadFile(self, fileBytes: BytesIO, folderId: str = None, fileType: str = None, fileName: str = None) -> str:
        """
        Upload a file to Google Drive.
        Args:
            fileBytes (BytesIO): The file to upload.
            folderId (str, optional): The ID of the folder to upload the file to.
            fileType (str, optional): The type of file to upload.
            fileName (str, optional): The name of the file to upload.
        Returns:
            str: The ID of the uploaded file.
        """
        try:
            file_metadata = {'name': fileName}
            if folderId:
                file_metadata['parents'] = [folderId]
            if fileType:
                file_metadata['mimeType'] = fileType
            
            # Use MediaIoBaseUpload for in-memory files
            media = MediaIoBaseUpload(fileBytes, mimetype=fileType, resumable=True)
            
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            return file.get('id')
        except Exception as e:
            print(f"An error occurred while uploading the file: {e}")
            return None
        

    def createFolder(self, folderName: str, parentFolderId: str = None) -> str:
        """
        Create a folder in Google Drive.
        Args:
            folderName (str): The name of the folder to create.
            parentFolderId (str, optional): The ID of the parent folder.
        Returns:
            str: The ID of the created folder.
        """
        try:
            file_metadata = {
                'name': folderName,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parentFolderId:
                file_metadata['parents'] = [parentFolderId]
            
            file = self.service.files().create(body=file_metadata, fields='id').execute()
            return file.get('id')
        except Exception as e:
            print(f"An error occurred while creating the folder: {e}")
            return None
        
    def getFiles(self, folderId: str, lastUpdatedTime: str = None, driveId: str = None) -> list:
        """
        Get files from a folder in Google Drive, supporting Shared Drives.
        
        Args:
            folderId (str): The ID of the folder to get files from.
            lastUpdatedTime (str, optional): Filter files modified after this time.
            driveId (str, optional): The ID of the Shared Drive (if any).
            
        Returns:
            list: A list of files in the folder.
        """
        try:
            query = f"'{folderId}' in parents"
            if lastUpdatedTime:
                query += f" and modifiedTime > '{lastUpdatedTime}'"

            params = {
                'q': query,
                'fields': "files(id, name, mimeType, modifiedTime)",
                'supportsAllDrives': True,
                'includeItemsFromAllDrives': True
            }

            if driveId:
                params['corpora'] = 'drive'
                params['driveId'] = driveId

            results = self.service.files().list(**params).execute()
            return results.get('files', [])
        except Exception as e:
            print(f"An error occurred while getting files: {e}")
            return []
        
    def emptyFolder(self, folderId: str) -> bool:
        """
        Empty a folder in Google Drive.
        Args:
            folderId (str): The ID of the folder to empty.
        Returns:
            bool: True if the folder was emptied successfully, False otherwise.
        """
        try:
            files = self.getFiles(folderId)
            print(f"Emptying folder {folderId} with {len(files)} files")
            for file in files:
                self.service.files().delete(
                    fileId=file['id'],
                    supportsAllDrives=True
                ).execute()
            return True
        except Exception as e:
            print(f"An error occurred while emptying the folder: {e}")
            return False
        
    def createSheetInFolder(self, title: str, folderId: str) -> str:
        """
        Create a Google Sheet and move it into a specific Drive folder.
        Args:
            title (str): The name of the sheet to create.
            folderId (str): The ID of the target Drive folder.
        Returns:
            str: The ID of the created spreadsheet.
        """
        try:
          
            file_metadata = {
                "name": title,
                "mimeType": "application/vnd.google-apps.spreadsheet",
                "parents": [folderId]
            }

            file = self.service.files().create(
                body=file_metadata,
                fields="id",
                supportsAllDrives=True
            ).execute()

            return file.get("id")
        except Exception as e:
            print(f"Failed to create Google Sheet in Shared Drive: {e}")
            return None