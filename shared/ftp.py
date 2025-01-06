from ftplib import FTP
import os
from datetime import datetime, timedelta
import ftplib

def delete_on_first(ftp: FTP):
    current_date = datetime.now()

    if current_date.day == 1:
        print('First of the Month: Deleting files over 6 months old.')
        six_months_ago = current_date - timedelta(days=6*30)
        files = ftp.nlst()

        # Iterate through the files and delete those older than 6 months
        for file in files:
            try:
                ftp.size(file)
            except ftplib.error_perm:
                continue

            file_modification_date = ftp.sendcmd('MDTM ' + file)
            file_modification_date = datetime.strptime(file_modification_date[4:], '%Y%m%d%H%M%S')

            if file_modification_date < six_months_ago:
                ftp.delete(file)

def upload_file(directory, filename, file):

    username = os.environ['FTP_USERNAME']
    password = os.environ['FTP_PASSWORD']
    server = 'ftp.glacier.org'

    # Connect to the FTP server
    ftp = FTP(server)
    ftp.login(username, password)

    ftp.cwd(directory)
    delete_on_first(ftp)

    try:
        # Open the local file in binary mode
        with open(file, 'rb') as f:
            # Upload the file to the FTP server
            ftp.storbinary('STOR ' + filename, f)
        files = ftp.nlst()

    except:
        print(f'Failed upload {filename}')
        files = []

    return f'https://glacier.org/daily/{directory}/{filename}', files