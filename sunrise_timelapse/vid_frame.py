"""
Select the best thumbnail frame from the timelapse video.
"""

import os
from datetime import datetime
from pathlib import Path
import sys
from typing import Tuple, Union, Optional

import cv2
from PIL import Image
import numpy as np

from dotenv import load_dotenv

load_dotenv("email.env")

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # pragma: no cover

from shared.retrieve_from_json import retrieve_from_json
from shared.ftp import upload_file
from sunrise_timelapse.timelapse_json import *
from sunrise_timelapse.sleep_to_sunrise import sunrise_timelapse_complete_time


class TimelapseError(Exception):
    """Base exception for timelapse processing errors."""

    pass


class VideoProcessingError(TimelapseError):
    """Exception raised for errors during video processing."""

    pass


class FileOperationError(TimelapseError):
    """Exception raised for file operation errors."""

    pass


def find_frame(video_path: Path) -> bool:
    """
    Find the frame with the most red pixels in a video and save it as an image.

    Args:
        video_path (Path): Path to the video file.

    Returns:
        bool: True if the frame was found and saved, False otherwise.

    Raises:
        VideoProcessingError: If there are issues processing the video
        FileOperationError: If there are issues saving the frame
    """
    try:
        if not os.path.exists(video_path):
            raise FileOperationError(f"Video file not found: {video_path}")

        # Open the video file
        video = cv2.VideoCapture(str(video_path))

        if not video.isOpened():
            raise VideoProcessingError(f"Failed to open video: {video_path}")

        max_red_ret = None
        max_red_frame = None
        max_red_pixels = 0
        frames_count = 0

        while True:
            # Read a frame from the video
            ret, frame = video.read()

            if frames_count == 0:
                if frame is None:
                    raise VideoProcessingError("First frame is empty")
                max_red_frame = frame.copy()
                max_red_ret = ret

            frames_count += 1

            if not ret:
                break

            try:
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

                # Create a mask for pixels within the red color range
                mask2 = cv2.inRange(hsv_frame, lower_red, upper_red)

                # Combine the masks
                mask = cv2.bitwise_or(mask1, mask2)

                # Count the number of red pixels in the frame
                red_pixels = cv2.countNonZero(mask)

                # Update the maximum red frame and pixel count if necessary
                if red_pixels > max_red_pixels:
                    max_red_frame = frame.copy()
                    max_red_ret = ret
                    max_red_pixels = red_pixels

            except cv2.error as e:
                print(f"Error processing frame {frames_count}: {e}", file=sys.stderr)
                continue

        if not max_red_ret or max_red_frame is None:
            print("No valid frames found in video", file=sys.stderr)
            return False

        # Ensure the output directory exists
        os.makedirs("email_images/today", exist_ok=True)

        try:
            # Save the frame
            cv2.imwrite("email_images/today/sunrise_frame.jpg", max_red_frame)
            play_button()
            return True
        except Exception as e:
            raise FileOperationError(f"Failed to save frame: {e}")

    except (cv2.error, Exception) as e:
        raise VideoProcessingError(f"Error processing video: {e}")

    finally:
        if "video" in locals():
            video.release()


def play_button() -> None:
    """
    Overlay a play button image onto the saved frame image.

    Raises:
        FileOperationError: If there are issues with file operations
    """
    try:
        frame_path = "email_images/today/sunrise_frame.jpg"
        if not os.path.exists(frame_path):
            raise FileOperationError("Frame image not found")

        play_button_path = "email_images/base/play_button.png"
        if not os.path.exists(play_button_path):
            raise FileOperationError("Play button image not found")

        # Open the timelapse frame
        background = Image.open(frame_path)

        # Open the play button
        overlay = Image.open(play_button_path)

        # Calculate the positions
        overlay_position = (
            (background.width - overlay.width) // 2,
            (background.height - overlay.height) // 2,
        )

        # Create a new image with the background
        composite = background.copy()

        # Paste the overlay image
        composite.paste(overlay, overlay_position, mask=overlay)

        # Save the composite image
        composite.save("email_images/today/sunrise_frame.jpg")

    except (IOError, OSError) as e:
        raise FileOperationError(f"Error in play_button operation: {e}")


def made_today(video: Path) -> bool:
    """
    Check if the video was created today.

    Args:
        video (Path): Path to the video file.

    Returns:
        bool: True if the video was created today, False otherwise.
    """
    try:
        if not os.path.exists(video):
            print("No video at given path.", file=sys.stderr)
            return False

        creation_date = datetime.fromtimestamp(os.path.getctime(video)).date()
        today = datetime.now().date()

        if creation_date == today:
            return True
        else:
            print(f"Video made on {creation_date}", file=sys.stderr)
            return False

    except (OSError, ValueError) as e:
        print(f"Error checking video date: {e}", file=sys.stderr)
        return False


def process_video(test: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """
    Process the sunrise timelapse video and upload the frame and video.
    Args:
        test (bool): Whether to use the test frame.

    Returns:
        Tuple[Optional[str], Optional[str]]: URLs of the uploaded video and frame, or None if not processed.
    """
    try:
        # Check if we already have today's video
        already_retrieved, keys = retrieve_from_json(["sunrise_vid", "sunrise_still"])
        if already_retrieved:
            return keys

        if sunrise_timelapse_complete_time() > 0:
            print("Too early for sunrise", file=sys.stderr)
            return "", ""

        # Make sure there is a video and it was made today
        new_style = Path(
            "/home/pi/Modules/timelapse/images/Compilation/videos/sunrise_timelapse.mp4"
        )
        old_style = Path("/home/pi/Documents/sunrise_timelapse/sunrise_timelapse.mp4")
        test_style = Path(
            "/Users/ws1/Documents/script/glacier_daily/email_images/today/sunrise_frame.jpg"
        )

        if made_today(new_style):
            video_path = new_style
        elif made_today(old_style):
            video_path = old_style
            print("Using old video.", file=sys.stderr)
        elif made_today(test) and test:
            video_path = test_style
        else:
            print("No video from today.", file=sys.stderr)
            return None, None

        try:
            frame_found = find_frame(video_path)
        except (VideoProcessingError, FileOperationError) as e:
            print(f"Error processing video: {e}", file=sys.stderr)
            return None, None

        if frame_found:
            today = datetime.now()
            filename_vid = (
                f"{today.month}_{today.day}_{today.year}_sunrise_timelapse.mp4"
            )
            frame_path = "email_images/today/sunrise_frame.jpg"
            filename_frame = f"{today.month}_{today.day}_{today.year}_sunrise.jpg"

            try:
                vid, vid_files = upload_file("sunrise_vid", filename_vid, video_path)
                frame, _ = upload_file("sunrise_still", filename_frame, frame_path)

                try:
                    print(vid_files)
                    data = gen_json(vid_files)
                    uploaded = send_timelapse_data(data)
                    if uploaded:
                        vid = uploaded
                except Exception as e:
                    print(f"Error with JSON operations: {e}", file=sys.stderr)

                return vid, frame

            except Exception as e:
                print(f"Error uploading files: {e}", file=sys.stderr)
                return None, None
        else:
            return "", ""

    except Exception as e:
        print(f"Unexpected error in process_video: {e}", file=sys.stderr)
        return None, None


if __name__ == "__main__":  # pragma: no cover
    print(process_video(test=True))
