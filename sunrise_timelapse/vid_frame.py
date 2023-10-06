from PIL import Image
import numpy as np
import os
from datetime import datetime
import cv2
from pathlib import Path
try:
    from sunrise_timelapse.timelapse_json import *
    from sunrise_timelapse.ftp import upload_sunrise
except ModuleNotFoundError:
    from ftp import upload_sunrise
    from timelapse_json import *

    
def find_frame(video_path):
    # Open the video file
    video = cv2.VideoCapture(str(video_path))
    max_red_frame = None
    max_red_pixels = 0

    while True:
        # Read a frame from the video
        ret, frame = video.read()
        if not ret:
            break

        # Convert the frame to the HSV color space
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Define the lower and upper bounds for the red color range
        lower_red = np.array([0, 50, 50])
        upper_red = np.array([10, 255, 255])

        # Create a mask for pixels within the red color range
        mask1 = cv2.inRange(hsv_frame, lower_red, upper_red)

        # Redefine the upper bound for the red color range
        lower_red = np.array([170, 50, 50])
        upper_red = np.array([180, 255, 255])

        # Create a mask for pixels within the red color range (wrapping around in the hue channel)
        mask2 = cv2.inRange(hsv_frame, lower_red, upper_red)

        # Combine the masks
        mask = cv2.bitwise_or(mask1, mask2)

        # Count the number of red pixels in the frame
        red_pixels = cv2.countNonZero(mask)

        # Update the maximum red frame and pixel count if necessary
        if red_pixels > max_red_pixels:
            max_red_frame = frame
            max_red_pixels = red_pixels

    # Release the video file
    cv2.imwrite('email_images/today/sunrise_frame.jpg', max_red_frame)
    video.release()
    play_button()

def play_button():
    # Open the timelapse frame
    background = Image.open("email_images/today/sunrise_frame.jpg")

    # Open the play button
    overlay = Image.open("email_images/base/play_button.png")

    # Calculate the positions to center the overlay image on the background image
    overlay_position = (
        (background.width - overlay.width) // 2,
        (background.height - overlay.height) // 2
    )

    # Create a new image with the background as the base
    composite = background.copy()

    # Paste the overlay image onto the composite image at the calculated position
    composite.paste(overlay, overlay_position, mask=overlay)

    # Save the composite image
    composite.save("email_images/today/sunrise_frame.jpg")


def made_today(video):
    if os.path.exists(video):
        if datetime.fromtimestamp(os.path.getctime(video)).date() == datetime.now().date():
            return True
        else:
            print(f'Video made on {datetime.fromtimestamp(os.path.getctime(video)).date()}')
    else:
        print('No video at given path.')

def process_video():
    # Make sure there is a video and it was made today before proceeding.
    new_style = Path('/home/pi/Modules/timelapse/images/Compilation/videos/sunrise_timelapse.mp4')
    old_style = Path('/home/pi/Documents/sunrise_timelapse/sunrise_timelapse.mp4')

    if made_today(new_style):
        video_path = new_style
    elif made_today(old_style):
        video_path = old_style
        print('Using old video.')
    else:
        print('No video from today.')
        return None, None

    find_frame(video_path)
    vid, frame, files = upload_sunrise(video_path)

    try:
        data = gen_json(files)
        uploaded = send_timelapse_data(data)
        if uploaded:
            vid = uploaded
    except Exception as e:
        print(e)
        pass

    return vid, frame

if __name__ == '__main__':
    print(process_video())
