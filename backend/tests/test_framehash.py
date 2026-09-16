from PIL import Image, ImageDraw, ImageFont

from kotoba.services.capture.framehash import StabilityTracker, dhash, distance

CANVAS = (480, 100)


def frame(text: str = "") -> Image.Image:
    image = Image.new("RGB", CANVAS, (18, 18, 28))
    if text:
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=40)
        draw.text((14, 20), text, font=font, fill=(240, 240, 240))
    return image


def test_same_image_has_zero_distance():
    value = dhash(frame("AAAAAA"))
    assert 0 <= value < 1 << 64
    assert distance(value, dhash(frame("AAAAAA").copy())) == 0


def test_light_noise_stays_within_threshold():
    noisy = frame("AAAAAA")
    pixels = noisy.load()
    for x in range(20):
        pixels[10 + x, 10] = (255, 255, 255)
    assert distance(dhash(frame("AAAAAA")), dhash(noisy)) <= 6


def test_different_text_exceeds_threshold():
    assert distance(dhash(frame("AAAAAA")), dhash(frame("MMMMMM"))) > 6
    assert distance(dhash(frame("AAAAAA")), dhash(frame(""))) > 6


def test_typewriter_sequence_reports_once():
    tracker = StabilityTracker()
    sequence = ["AA", "AAAAAA", "AAAAAAAAAA", "AAAAAAAAAAAAAA", "AAAAAAAAAAAAAA", "AAAAAAAAAAAAAA"]
    reports = [tracker.update(dhash(frame(text))) for text in sequence]
    assert reports == [False, False, False, False, False, True]
    # The screen stays still: no second event.
    assert tracker.update(dhash(frame("AAAAAAAAAAAAAA"))) is False


def test_scene_change_reports_again():
    tracker = StabilityTracker()
    first = dhash(frame("AAAAAAAAAAAAAA"))
    second = dhash(frame("BBBBBBBBBBBBBBBB"))

    first_reports = [tracker.update(first) for _ in range(3)]
    assert first_reports == [False, False, True]

    assert tracker.update(second) is False
    assert tracker.update(second) is False
    assert tracker.update(second) is True
    assert tracker.update(second) is False
