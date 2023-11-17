# Glacier Daily Update Emails

This program collects data from a wide variety of sources, sanitizes/organizes it, makes it available to Drip email custom dynamic content module, then sends the email out to a list of subscribers.

## Modules

The program is divided into 10 modules, plus a few scripts in the main folder.

### main
The main module has the `main.py` script that controls the overall flow of the program (retrieving subscribers, generating and uploading data, sending emails). It has a test mode that is automatically activated if the main function is run after 9am and only send the emails to people with the test tag.

The main folder also contains the `generate_and_upload.py` script that does the heaving lifting of threading all of the data retrieval processes, creating a json file to upload and using FTP to put that json on the server where Drip can access it. When the data is collected from the various functions and put into a json format, it is all encoded using base64. This is because HTML contains characters that have special meaning in json format, so to create valid json and not mangle the html, everything needs to be encoded.

### activities
The activities module retrieves and formats the ranger activities that are happening that day. The data is from the "events" endpoint of the official NPS API. Much of the module is dedicated to condensing the information so that it is readable but not too long.

### drip
The drip module is dedicated to interacting with the Drip email api. It has one function to retrieve a list of subscribers to that have the tag "Glacier Daily Update" (if not in test mode). Then, after the content is uploaded, the send_in_drip function is called that subscribes each user to the Glacier Daily Update workflow.

### image_otd
This module randomly takes a GlacierNPS flickr photo, then resizes it to the correct shape/size for the email. This one will only work right on my Raspberry Pi because I've downloaded the entire flickr account and named the files sequentially, so it accesses them locally and can select one by generating a random number. In the future, I'd like to connect this to the flickr API so it's more portable.

### notices
`notices` uses the Google Sheets API to retrieve a list of announcements, and the start and end dates for when they should be included. It then sorts out and formats the ones that are meant to run the current day. The notices are the only data source that requires manual updating, since it is just a google sheet things can be added to. 

### peak
This is a very simple module that randomly selects a Glacier peak from a csv file. I would like at some point to include a picture of/from the peak.

### product_otd
Product of the day interacts with the BigCommerce store API. If we change the location of the online store, this module will need to be replaced.  

### sunrise_timelapse

### trails_and_cgs

### weather

## Associated Files


### email_html

### email_images

### server

## API Connection


## Interaction with Drip

## Interaction with glacier.org


## Author

Glacier Daily Update Emails was made by Andrew Smith in 2023 for the Glacier National Park Conservancy.
