from pathlib import Path

import pytest

import sunrise_timelapse.vid_frame as vf


class DummyImage:
    def __init__(self, *a, **k):
        self.width = 100
        self.height = 100

    def copy(self):
        return self

    def save(self, *a, **k):
        pass

    def paste(self, overlay, position, mask=None):
        pass


@pytest.mark.parametrize("video_path", [Path("dummy.mp4")])
def test_find_frame_success(monkeypatch, video_path):
    import numpy as np

    class DummyVideoCapture:
        def __init__(self, path):
            self.path = path
            self.frames = [
                np.zeros((10, 10, 3), dtype=np.uint8),
                np.zeros((10, 10, 3), dtype=np.uint8),
            ]
            self.index = 0
            self.opened = True

        def isOpened(self):
            return self.opened

        def read(self):
            if self.index < len(self.frames):
                self.index += 1
                return True, self.frames[self.index - 1]
            return False, None

        def release(self):
            self.opened = False

        def get(self, prop):
            return 2

    monkeypatch.setattr(vf.cv2, "VideoCapture", lambda path: DummyVideoCapture(path))
    monkeypatch.setattr(vf, "upload_file", lambda d, f, p: ("url", [f]))
    # Patch os.path.exists to return True for both frame and play button
    monkeypatch.setattr(vf.os.path, "exists", lambda p: True)
    from unittest.mock import patch as upatch

    with upatch("PIL.Image.open", side_effect=[DummyImage(), DummyImage()]):
        assert vf.find_frame(video_path)


def test_play_button_success(monkeypatch):
    # Patch os.path.exists to always return True
    monkeypatch.setattr(vf.os.path, "exists", lambda p: True)
    from unittest.mock import patch as upatch

    with upatch("PIL.Image.open", side_effect=[DummyImage(), DummyImage()]):
        vf.play_button()  # Should not raise


def test_play_button_missing_frame(monkeypatch):
    monkeypatch.setattr(vf.os.path, "exists", lambda p: False)
    with pytest.raises(vf.FileOperationError):
        vf.play_button()


def test_play_button_missing_overlay(monkeypatch):
    # First call (frame) exists, second (overlay) does not
    exists_calls = [True, False]

    def exists_side_effect(p):
        return exists_calls.pop(0)

    monkeypatch.setattr(vf.os.path, "exists", exists_side_effect)
    from unittest.mock import patch as upatch

    with upatch("PIL.Image.open", side_effect=[DummyImage()]):
        with pytest.raises(vf.FileOperationError):
            vf.play_button()


def test_find_frame_failure(monkeypatch):
    class BadVideo:
        def isOpened(self):
            return False

        def release(self):
            pass

    monkeypatch.setattr(vf.cv2, "VideoCapture", lambda path: BadVideo())
    with pytest.raises(vf.VideoProcessingError):
        vf.find_frame(Path("bad.mp4"))
