"""Frame hashing and stability detection for the region watcher.

Pure logic: no screen capture, no OCR, no database. The watcher grabs frames,
hashes them here, and only when the picture has changed *and* settled does it
make sense to run OCR — a typewriter effect would otherwise produce one
partial line per frame.
"""

from __future__ import annotations

from PIL import Image


def dhash(image: Image.Image, size: int = 8) -> int:
    """64-bit difference hash: one bit per horizontal neighbour comparison."""
    gray = image.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    stride = size + 1
    pixels = gray.tobytes()
    bits = 0
    for row in range(size):
        base = row * stride
        for col in range(size):
            left, right = pixels[base + col], pixels[base + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return bits


def distance(a: int, b: int) -> int:
    """Hamming distance between two dhashes: how many of the 64 bits differ."""
    return (a ^ b).bit_count()


class StabilityTracker:
    """Report once when the picture has changed and then settled.

    Stable means ``distance(current, previous) <= threshold``. Reporting also
    requires the current frame to differ from the last reported one, so a
    screen that merely sits still never reports again.
    """

    def __init__(self, threshold: int = 6, stable_frames: int = 2) -> None:
        self.threshold = threshold
        self.stable_frames = stable_frames
        self._previous: int | None = None
        self._confirmed: int | None = None
        self._stable = 0

    def update(self, frame_hash: int) -> bool:
        """Feed one frame hash; True exactly once per changed-and-stable scene."""
        if self._previous is None:
            self._previous = frame_hash
            return False
        stable = distance(frame_hash, self._previous) <= self.threshold
        self._previous = frame_hash
        if not stable:
            self._stable = 0
            return False
        self._stable += 1
        if self._stable < self.stable_frames:
            return False
        if self._confirmed is not None and distance(frame_hash, self._confirmed) <= self.threshold:
            return False
        self._confirmed = frame_hash
        self._stable = 0
        return True
