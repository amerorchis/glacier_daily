"""
Select the best thumbnail frame from the timelapse video.
"""

import os
from datetime import datetime
from pathlib import Path
import sys

import cv2
from PIL import Image
import numpy as np

from dotenv import load_dotenv
load_dotenv("email.env")

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from shared.retrieve_from_json import retrieve_from_json
from shared.ftp import upload_file
from sunrise_timelapse.timelapse_json import *
from sunrise_timelapse.sleep_to_sunrise import sunrise_timelapse_complete_time

def find_frame(video_path: Path) -> bool:
    """
    Find the frame with the most red pixels in a video and save it as an image.

    Args:
        video_path (Path): Path to the video file.

    Returns:
        bool: True if the frame was found and saved, False otherwise.
    """
    # Open the video file
    video = cv2.VideoCapture(str(video_path))
    max_red_ret = None
    max_red_frame = None
    max_red_pixels = 0
    frames_count = 0

    if video.isOpened():
        while True:
            # Read a frame from the video
            ret, frame = video.read()

            if frames_count == 0:
                max_red_frame = frame
                max_red_ret = ret

            frames_count += 1

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
                max_red_ret = ret
                max_red_pixels = red_pixels

        if max_red_ret:
            # Release the video file
            cv2.imwrite('email_images/today/sunrise_frame.jpg', max_red_frame)
            video.release()
            play_button()
            return True

        else:
            print(f'frame not found, {max_red_ret} - {max_red_frame}', file=sys.stderr)

    return False
        

def play_button() -> None:
    """
    Overlay a play button image onto the saved frame image.
    """
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


def made_today(video: Path) -> bool:
    """
    Check if the video was created today.

    Args:
        video (Path): Path to the video file.

    Returns:
        bool: True if the video was created today, False otherwise.
    """
    if os.path.exists(video):
        if datetime.fromtimestamp(os.path.getctime(video)).date() == datetime.now().date():
            return True
        else:
            print(f'Video made on {datetime.fromtimestamp(os.path.getctime(video)).date()}', file=sys.stderr)
    else:
        print('No video at given path.', file=sys.stderr)

def process_video() -> Tuple[Union[str, None], Union[str, None]]:
    """
    Process the sunrise timelapse video and upload the frame and video.

    Returns:
        Tuple[Union[str, None], Union[str, None]]: URLs of the uploaded video and frame, or None if not processed.
    """
    # Check if we already have today's video
    already_retrieved, keys = retrieve_from_json(['sunrise_vid', 'sunrise_still'])
    if already_retrieved:
        return keys

    if sunrise_timelapse_complete_time() > 0:
        # print('Too early for sunrise', file=sys.stderr)
        return '', ''

    else:

        # Make sure there is a video and it was made today before proceeding.
        new_style = Path('/home/pi/Modules/timelapse/images/Compilation/videos/sunrise_timelapse.mp4')
        old_style = Path('/home/pi/Documents/sunrise_timelapse/sunrise_timelapse.mp4')

        if made_today(new_style):
            video_path = new_style
        elif made_today(old_style):
            video_path = old_style
            print('Using old video.', file=sys.stderr)
        else:
            print('No video from today.', file=sys.stderr)
            return None, None

        frame_found = find_frame(video_path)

        if frame_found:
            today = datetime.now()
            filename_vid = f'{today.month}_{today.day}_{today.year}_sunrise_timelapse.mp4'
            frame_path = 'email_images/today/sunrise_frame.jpg'
            filename_frame = f'{today.month}_{today.day}_{today.year}_sunrise.jpg'

            vid, vid_files = upload_file('sunrise_vid', filename_vid, video_path)
            frame, _ = upload_file('sunrise_still', filename_frame, frame_path)

            try:
                data = gen_json(vid_files)
                uploaded = send_timelapse_data(data)
                if uploaded:
                    vid = uploaded
            except Exception as e:
                print(e, file=sys.stderr)
        else:
            return '', ''

        return vid, frame

if __name__ == '__main__':
    print(process_video())
