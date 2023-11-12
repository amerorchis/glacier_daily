import json
import socket
from datetime import datetime
from ftplib import FTP
from time import sleep
import io
import os


def gen_json(files):

    def get_date_from_file_name(file_name):
        # Split the file name by underscores to extract the date parts
        parts = file_name.split('_')
        
        # Assuming the format is month_day_year, convert parts to integers
        month = int(parts[0])
        day = int(parts[1])
        year = int(parts[2])
        
        # Return a tuple (year, month, day) for sorting
        return (year, month, day)

    files.remove('..')
    files.remove('.')
    
    files.sort(key=get_date_from_file_name, reverse=True)

    timelapses = [{'date':f'{datetime.now()}'}]

    for file in files:
        year, month, day = get_date_from_file_name(file)
        timelapses.append({
            'id': f"{file.replace('.mp4','')}",
            'vid_src': f'/daily/sunrise_vid/{file}',
            'url': f"https://glacier.org/webcam-timelapse/?type=daily&id={file.replace('.mp4','')}",
            'title': f'{month}-{day} Sunrise Timelapse', # Title of the webpage showing this timelapse.
            'string': f'{month}-{day} Sunrise'
        })
    
    return json.dumps(timelapses)

def send_timelapse_data(data):
    
    username = os.environ["webcam_ftp_user"]
    password = os.environ["webcam_ftp_pword"]
    server = os.environ["timelapse_server"]

    try:
        ftp = FTP(server)
    except socket.gaierror:
        sleep(5)
        ftp = FTP(server)

    ftp.login(username, password)

    json_bytes = data.encode()
    json_buffer = io.BytesIO(json_bytes)
    file_path = 'daily_timelapse_data.json'

    try:
        ftp.storbinary('STOR ' + file_path, json_buffer)
        today = datetime.now().date()
        filename_vid = f'{today.month}_{today.day}_{today.year}_sunrise_timelapse.mp4'
        url = f"https://glacier.org/webcam-timelapse/?type=daily&id={filename_vid.replace('.mp4','')}"
        ftp.quit()
        return url
   
    except:
        print(f'Failed upload data')
        ftp.quit()
        return False
