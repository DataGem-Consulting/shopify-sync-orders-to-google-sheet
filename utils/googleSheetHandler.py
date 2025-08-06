from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json
import os 
import pandas as pd

class GoogleSheetHandler:
    def __init__(self, credentials):
        if credentials:
            self.creds = credentials
        else:
            try:
                with open('var/bigquery_service_account.json', 'r') as file:
                    credentials = json.load(file)
                scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
                self.creds = Credentials.from_service_account_info(credentials, scopes=scopes)
            except FileNotFoundError:
                self.creds = os.environ.get('SERVICE_ACCOUNT_FILE', '{}')
                self.creds = Credentials.from_service_account_info(json.loads(self.creds), scopes=scopes)
                
        self.service = build('sheets', 'v4', credentials=self.creds)

    def append_to_sheet(self, fileId: str, row: dict, is_first_row: bool = False):
        sheet = self.service.spreadsheets()
        
        if is_first_row:
            headers = list(row.keys())
            request = sheet.values().append(
                spreadsheetId=fileId,
                range='Sheet1!A1',
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body={'values': [headers]}
            )
            request.execute()
        else:
            # Read existing headers from the first row
            result = sheet.values().get(spreadsheetId=fileId, range='Sheet1!1:1').execute()
            headers = result.get('values', [[]])[0]

        # Create a row with values in the correct order
        new_row = [row.get(header, "") for header in headers]
        
        # Append the row
        request = sheet.values().append(
            spreadsheetId=fileId,
            range='Sheet1!A1',
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body={'values': [new_row]}
        )
        request.execute()

    def create_sheet(self, title: str) -> str:
        sheet = self.service.spreadsheets().create(body={
            "properties": {"title": title}
        }).execute()
        return sheet['spreadsheetId']
    
    def writeData(self, spreadsheet_id: str, data: pd.DataFrame, range_: str = 'Sheet1!A1'):
        """
        Write a pandas DataFrame to a Google Sheet.
        Args:
            spreadsheet_id (str): The ID of the spreadsheet.
            data (pd.DataFrame): The DataFrame to write.
            range_ (str): The cell range to start writing at.
        """
     

        # Apply sanitization to all cells in the DataFrame, convert to 2D list
        sanitized_data = data.applymap(lambda x: str(x).replace('\r', ' ').replace('"', '""')).values.tolist()
        sanitized_data_with_header = [list(data.columns)] + sanitized_data

        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_,
            valueInputOption='USER_ENTERED',  # or 'USER_ENTERED' if you want sheets to parse input
            body={'values': sanitized_data_with_header}
        ).execute()

    def getSheetData(self, sheetId: str, range_name: str) -> pd.DataFrame:
        """ Get data from a specific range in a Google Sheet.
        Args:
            sheetId (str): The ID of the Google Sheet.
            range_name (str): The range to fetch data from (e.g., 'Sheet1!A1:C10').
        Returns:
            list: The data fetched from the specified range.
        """
        result = self.service.spreadsheets().values().get(
            spreadsheetId=sheetId,
            range=range_name
        ).execute()

        return pd.DataFrame(result.get('values', [])[1:], columns=result.get('values', [[]])[0]) if result.get('values') else pd.DataFrame()