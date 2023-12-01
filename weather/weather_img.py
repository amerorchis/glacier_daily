from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from ftplib import FTP
from pathlib import Path
import os

try:
    from weather.season import get_season
except ModuleNotFoundError:
    from season import get_season

username = os.environ['FTP_USERNAME']
password = os.environ['FTP_PASSWORD']
server = 'ftp.glacier.org'

def upload_weather():
    today = datetime.now()
    file_path = f'{today.month}_{today.day}_{today.year}_today_park_map.png'

    # Connect to the FTP server
    ftp = FTP(server)
    ftp.login(username, password)
    ftp.cwd('weather')

    try:
        # Open the local file in binary mode
        with open('email_images/today/today_park_map.png', 'rb') as f:
            # Upload the file to the FTP server
            ftp.storbinary('STOR ' + file_path, f)

    except:
        print('Failed upload weather image')
        pass

    # Close the FTP connection
    ftp.quit()

    return f'https://glacier.org/daily/weather/{file_path}'

def weather_image(results):
    dimensions = {"West Glacier":(292.1848, 462.5), "Polebridge":(165.3, 190), "St. Mary":(591,303), "Two Medicine":(623,524), "Logan Pass":(423.52,336), "Many Glacier":(460.1623,185)}
    
    # Open the image
    image_path = f'email_images/base/park_map_{get_season()}.png'
    image = Image.open(image_path)

    # Create a drawing object
    draw = ImageDraw.Draw(image)

    # Define the font style and color
    font_path = 'email_images/base/OpenSans-Regular.ttf'
    text_color = (0,0,0)

    for location in results:
        name, high, low, cond = location
        left, y = dimensions[name]

        font_size = 20
        font = ImageFont.truetype(font_path, font_size)


        # Add the text to the image
        text_width = draw.textlength(f'{high} | {low}', font=font)
        x = left + ((139.11 - text_width)/2)
        draw.text((x,y), f'{high} | {low}', font=font, fill=text_color)

        text_width = draw.textlength(cond, font=font)

        while text_width > 139.11:
            font_size -= 1
            font = ImageFont.truetype(font_path, font_size)
            text_width = draw.textlength(cond, font=font)

        x = left + ((139.11 - text_width)/2)
        draw.text((x,y+24), f'{cond}', font=font, fill=text_color)

    # Add date
    font = ImageFont.truetype(font_path, 20)
    day = datetime.now().strftime("%B %-d, %Y").upper()
    text_width = draw.textlength(day)
    left_margin, width_textbox = 149, 347
    x = left_margin + ((width_textbox - text_width)/2)
    draw.text((x, 74), day, font=font, fill='#FFFFFF')

    # Save the modified image
    image.resize((405, 374))
    image.save('email_images/today/today_park_map.png')

    return upload_weather()

if __name__ == '__main__':
    from weather import weather_data
    weather_image(weather_data().results)
