# Glacier Daily Update Emails

This program collects data from a wide variety of sources, sanitizes/organizes it, makes it available to Drip email custom dynamic content module, then sends the email out to a list of subscribers.

## Modules

The program is divided into 10 modules, plus a few scripts in the main folder.

### main
The main module has the `main.py` script that controls the overall flow of the program (retrieving subscribers, generating and uploading data, sending emails). It has a test mode that only sends the email to people with the test tag.

The main folder also contains the `generate_and_upload.py` script that does the heavy lifting of threading all of the data retrieval processes, creating a JSON file to upload and using FTP to put that JSON on the server where Drip can access it. When the data is collected from the various functions and put into a JSON format, it is all encoded using base64. This is because HTML contains characters that have special meaning in JSON format, so to create valid JSON and not mangle the HTML, everything needs to be encoded.

### activities
The activities module retrieves and formats the ranger activities that are happening that day. The data is from the "events" endpoint of the official NPS API. Much of the module is dedicated to condensing the information so that it is readable but not too long.

### drip
The drip module is dedicated to interacting with the Drip email API. It has a function to retrieve a list of subscribers that have the tag "Glacier Daily Update" (if not in test mode). Then, after the content is uploaded, the `send_in_drip` function is called that subscribes each user to the Glacier Daily Update workflow using a bulk action. It also checks which people have opted in and out of Daily Updates for that day, adding and removing tags.

### image_otd
This module randomly takes a GlacierNPS Flickr photo, then resizes it to the correct shape/size for the email. The module accesses the Flickr API.

### notices
`notices` uses the Google Sheets API to retrieve a list of announcements, and the start and end dates for when they should be included. It then sorts out and formats the ones that are meant to run the current day. The notices are the only data source that requires manual updating, since it is just a Google sheet things can be added to. 

### peak
This module randomly selects a Glacier peak from a CSV file. It grabs a satellite image of that peak from Mapbox.

### product_otd
Product of the day interacts with the BigCommerce store API. If we change the location of the online store, this module will need to be replaced.  

### sunrise_timelapse
The `sunrise_timelapse` module retrieves the latest sunrise timelapse video from the webcam FTP server and prepares it for inclusion in the email, including selecting the most colorful frame to use as a thumbnail.

### trails_and_cgs
The `trails_and_cgs` module retrieves the current status of trails and campgrounds from the NPS API and formats it for inclusion in the email.

### weather
The `weather` module retrieves the current weather forecast from the OpenMateo API and formats it for inclusion in the email. It creates a map of the park with weather data, gets air quality information, NWS alerts, aurora forecasts, and sunset color forecasts.

## Associated Files

### email_html
Contains the HTML templates used for generating the email content.

### email_images
Contains the images used in the emails. The `today` subdirectory is created dynamically if it doesn't exist.

### server
Contains scripts and configurations for the FTP server used to upload the generated JSON files and images.

## API Connection
The program connects to various APIs including the NPS API, Drip API, Google Sheets API, BigCommerce API, Flickr API, Mapbox API, and the OpenMateo API to retrieve and format the data needed for the daily update emails.

## Interaction with Drip
The program interacts with the Drip email marketing platform to retrieve subscribers and send the daily update emails. It uses the Drip API to manage subscribers and workflows.

## Interaction with glacier.org
The program uploads the generated JSON files and images to the FTP server at glacier.org, where they can be accessed by the Drip email platform.

## Author
Glacier Daily Update Emails was made by Andrew Smith in 2023 for the Glacier National Park Conservancy.
