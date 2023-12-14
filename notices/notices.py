import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
try:
    from notices.retry import retry
except ModuleNotFoundError:
    from retry import retry


default = '<p style="margin:0 0 35px; font-size:12px; line-height:18px; color:#333333;">Notices could not be retrieved.</p>'

@retry(3, (gspread.exceptions.APIError), default, 3)
def get_notices():
    # Load credentials
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_file('notices/sheets-api-389117-34906b5fba7f.json', scopes=scopes)

    # Create a client
    client = gspread.authorize(credentials)

    # Open a spreadsheet
    spreadsheet = client.open_by_key('1Z3jyEj8grDiNKRbYIJWjXG970N7dZO0VLx5pPFZoh2Q')

    # Access a worksheet
    worksheet = spreadsheet.sheet1

    values = worksheet.get_all_values()
    date_format = '%m/%d/%Y'
    if len(values) > 1:
        notices = [i[0:3] for i in values[1:] if i[0] and i[1] and i[2]] # Grab all notices that have a start and end date and content
        notices = [{'start':datetime.strptime(i[0], date_format), 'last':datetime.strptime(i[1], date_format) + timedelta(days=1), 'notice':i[2]} for i in notices] # create a dict for each one
        current_notices = [i['notice'] for i in notices if i['start'] < datetime.now() < i['last']] # isolate the content of the current notices
        
        if current_notices:
            message = '<ul style="margin:0 0 35px; padding-left:10px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">'
            for i in current_notices:
                message += f"<li>{i}</li>\n"
            return message + "</ul>"

    return '<p style="margin:0 0 35px; font-size:12px; line-height:18px; color:#333333;">There were no notices for today.</p>'
    

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("email.env")
    print(get_notices())
    