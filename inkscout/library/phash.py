"""Hash percettivo (dHash) per collassare duplicati e near-duplicati."""

from __future__ import annotations

from pathlib import Path


def dhash(image, hash_size: int = 8) -> int:
    from PIL import Image

    img = image.convert("L").resize((hash_size + 1, hash_size), Image.LANCZOS)
    bits = 0
    for row in range(hash_size):
        for col in range(hash_size):
            left = img.getpixel((col, row))
            right = img.getpixel((col + 1, row))
            bits = (bits << 1) | (1 if right > left else 0)
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def is_near_dup(a: int, b: int, threshold: int = 5) -> bool:
    return hamming(a, b) <= threshold


def phash_of_path(path: str | Path) -> int:
    from PIL import Image

    with Image.open(path) as img:
        return dhash(img)
