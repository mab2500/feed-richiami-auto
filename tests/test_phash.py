from PIL import Image
from inkscout.library.phash import dhash, hamming, is_near_dup


def _img(color, size=(64, 64)):
    return Image.new("RGB", size, color)


def test_identical_images_same_hash():
    a = dhash(_img((10, 20, 30)))
    b = dhash(_img((10, 20, 30)))
    assert a == b and hamming(a, b) == 0


def test_gradient_vs_flat_differ():
    flat = dhash(_img((0, 0, 0)))
    grad = Image.new("L", (64, 64))
    for x in range(64):
        for y in range(64):
            grad.putpixel((x, y), x * 4 % 256)
    assert hamming(flat, dhash(grad)) > 5


def test_near_dup_threshold():
    assert is_near_dup(0b1010, 0b1011, threshold=5) is True
    assert is_near_dup(0, (1 << 40) - 1, threshold=5) is False
