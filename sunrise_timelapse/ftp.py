from ftplib import FTP
import os
from datetime import datetime, timedelta
import ftplib


username = os.environ['FTP_USERNAME']
password = os.environ['FTP_PASSWORD']
server = 'ftp.glacier.org'

"""
Get a list of all of the files, make a json entry for each one, upload the json.
"""

def upload_sunrise(sunrise_path):
    # Connect to the FTP server
    ftp = FTP(server)
    ftp.login(username, password)
    today = datetime.now()

    def delete_on_first():
        current_date = datetime.now()

        if current_date.day == 1:
            print('First of the Month: Deleting files over 6 months old.')
            six_months_ago = current_date - timedelta(days=6*30)
            files = ftp.nlst()

            # Iterate through the files and delete those older than 6 months
            for file in files:
                try:
                    ftp.size(file)
                except ftplib.error_perm as e:
                    continue

                file_modification_date = ftp.sendcmd('MDTM ' + file)
                file_modification_date = datetime.strptime(file_modification_date[4:], '%Y%m%d%H%M%S')
                
                if file_modification_date < six_months_ago:
                    ftp.delete(file)
    

    # Change current working directory.
    ftp.cwd('sunrise_vid')
    delete_on_first()

    try:
        # Open the local file in binary mode
        with open(sunrise_path, 'rb') as f:
            # Upload the file to the FTP server
            filename_vid = f'{today.month}_{today.day}_{today.year}_sunrise_timelapse.mp4'
            ftp.storbinary('STOR ' + filename_vid, f)
        
        files = ftp.nlst()

    except:
        print('Failed upload sunrise timelapse')
        pass
    
    ftp.cwd('../sunrise_still')
    delete_on_first()
    with open('email_images/today/sunrise_frame.jpg', 'rb') as f:
        # Upload the file to the FTP server
        filename_still = f'{today.month}_{today.day}_{today.year}_sunrise.jpg'
        ftp.storbinary('STOR ' + filename_still, f)

    # Close the FTP connection
    ftp.quit()

    return f'https://glacier.org/daily/sunrise_vid/{filename_vid}', f'https://glacier.org/daily/sunrise_still/{filename_still}', files

