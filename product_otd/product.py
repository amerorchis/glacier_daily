import random
import requests
import json
import os
import re
from datetime import datetime, date
from PIL import Image
import requests
from io import BytesIO
from ftplib import FTP

username = os.environ['FTP_USERNAME']
password = os.environ['FTP_PASSWORD']
server = 'ftp.glacier.org'

def upload_potd():
    today = datetime.now()
    file_path = f'{today.month}_{today.day}_{today.year}_product_otd.jpg'
    directory = 'product'

    # Connect to the FTP server
    ftp = FTP(server)
    ftp.login(username, password)
    ftp.cwd(directory)

    try:
        # Open the local file in binary mode
        with open('email_images/today/product_otd.jpg', 'rb') as f:
            # Upload the file to the FTP server
            ftp.storbinary('STOR ' + file_path, f)

    except:
        print('Failed upload product image')
        pass

    # Close the FTP connection
    ftp.quit()

    return f'https://glacier.org/daily/{directory}/{file_path}'

def resize_image(url):
    # Fetch the image from the URL
    response = requests.get(url)
    image = Image.open(BytesIO(response.content))

    # Calculate the new size while maintaining the aspect ratio
    width, height = image.size
    aspect_ratio = width / height

    # Calculate the new width and height to fit within the canvas
    scale_multiplier = 2
    new_width = min(width, 255 * scale_multiplier)
    new_height = int(new_width / aspect_ratio)

    # Check if the new height exceeds the canvas height
    if new_height > (150 * scale_multiplier):
        new_height = (150 * scale_multiplier)
        new_width = int(new_height * aspect_ratio)

    # Resize the image
    resized_image = image.resize((new_width, new_height))

    # Create a new blank canvas with white background
    canvas = Image.new('RGB', (255*scale_multiplier, 150*scale_multiplier), 'white')

    # Calculate the position to paste the resized image
    x = (canvas.width - resized_image.width) // 2
    y = (canvas.height - resized_image.height) // 2

    # Paste the resized image onto the canvas
    canvas.paste(resized_image, (x, y))

    # Save or display the resulting image
    canvas.save('email_images/today/product_otd.jpg')

def get_product():
    BC_token = os.environ['BC_TOKEN']
    store_hash = os.environ['BC_STORE_HASH']
    url = f"https://api.bigcommerce.com/stores/{store_hash}/v3/catalog/products?inventory_level:min=1&is_visible=true"
    header = {"X-Auth-Token": BC_token,}

    r = requests.get(url=url, headers=header)
    products = json.loads(r.text)
    total_products = products['meta']['pagination']['total']

    random.seed(datetime.today().strftime("%Y:%m:%d"))
    product_otd = random.randrange(1, total_products + 1)

    def retrieve_potd(product_otd):
        product_page = product_otd // 50 + 1
        product_on_page = product_otd % 50

        new_url = f"https://api.bigcommerce.com/stores/{store_hash}/v3/catalog/products?inventory_level:min=1&is_visible=true&page={product_page}"
        product_index_on_page = product_on_page - 1
        r = requests.get(url=new_url, headers=header)
        products = json.loads(r.text)
        item = products['data'][product_index_on_page]
        name = item['name']

        if item['meta_description']:
            pattern = r'(<(?!br\s*\/?)[^>]*>)|((<br\s*\/?>)\s*)+'
            desc = re.sub(pattern, lambda m: m.group(1) if m.group(1) else '<br>', item['meta_description'])
        else:
            pattern = r'(<(?!br\s*\/?)[^>]*>)|((<br\s*\/?>)\s*)+'
            desc = re.sub(pattern, lambda m: m.group(1) if m.group(1) else '<br>', item['description'])
        desc = desc.replace('&nbsp;','') # remove non-breaking spaces
        desc = re.sub(r'<p[^>]*>|<\/p>', '', desc) # remove paragraph tags
        desc = re.sub(r'(?<=\w)(\.)', r'\1 ', desc) # add space after sentence

        if len(desc) > 150:
            index = desc.find(' ', 150)
            desc = desc[:index] + '...'

        item_id = item['id']
        item_url = f"https://shop.glacier.org{item['custom_url']['url']}"
        get_image_url = f"https://api.bigcommerce.com/stores/{store_hash}/v3/catalog/products/{item_id}/images"
        r = requests.get(url=get_image_url, headers=header)
        image_url = json.loads(r.text)['data'][0]['url_standard']
        # print(f'{name}: {desc} - {item_id}, {item_url} | {image_url}')
        return {'image_url':image_url, 'name':name, 'desc':desc, 'product_link':item_url}
    
    while True:
        try:
            product_data = retrieve_potd(product_otd)
            if product_data['image_url']:
                break
        except Exception:
            print('Product not found')
            product_otd = random.randint(1, total_products)
    
    resize_image(product_data['image_url'])
    image_url = upload_potd()
    # print(product_data['name'], image_url, product_data['product_link'], product_data['desc'])
    return product_data['name'], image_url, product_data['product_link'], product_data['desc']

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("email.env")
    print(get_product())
