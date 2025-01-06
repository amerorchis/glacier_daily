import os
import sys

from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from pathlib import Path

try:
    from weather.season import get_season
except ModuleNotFoundError:
    from season import get_season

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from shared.ftp import upload_file

def upload_weather():
    """
    Upload the product image to the glacier.org ftp server.
    """
    today = datetime.now()
    filename = f'{today.month}_{today.day}_{today.year}_today_park_map.png'
    file = 'email_images/today/today_park_map.png'
    directory = 'weather'
    address, _ = upload_file(directory, filename, file)
    return address

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
