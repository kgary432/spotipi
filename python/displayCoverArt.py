import math
import time
import sys
import logging
from logging.handlers import RotatingFileHandler
from getSongInfo import getSongInfo
import requests
from io import BytesIO
from PIL import Image
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import os
import configparser

# Visual spin rate: slow enough to read the cover, fast enough to read as a CD.
SPIN_RPM = 16
SPIN_STEP_DEG = 8
POLL_SECONDS = 1.0


def _square_cover(src, size):
    img = src.convert('RGB')
    width, height = img.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    img = img.crop((left, top, left + side, top + side))
    return img.resize((size, size), Image.Resampling.LANCZOS)


def make_cd_disc(src, size):
    """Turn an album cover into a circular CD on a black background."""
    disc = _square_cover(src, size)
    pixels = disc.load()
    cx = (size - 1) / 2.0
    cy = (size - 1) / 2.0
    outer_r = size / 2.0 - 0.35
    hole_r = max(1.6, size * 0.07)
    hub_r = max(hole_r + 1.5, size * 0.17)
    rim_w = max(1.0, size * 0.035)

    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            dist = math.hypot(dx, dy)
            if dist > outer_r or dist < hole_r:
                pixels[x, y] = (0, 0, 0)
                continue

            r, g, b = pixels[x, y]

            if dist < hub_r:
                t = (dist - hole_r) / (hub_r - hole_r)
                if t < 0.55:
                    metal = 170 + int(70 * t)
                    r, g, b = metal, metal, min(255, metal + 12)
                else:
                    mix = 0.55
                    metal = 210
                    r = int(metal * mix + r * (1 - mix))
                    g = int(metal * mix + g * (1 - mix))
                    b = int((metal + 8) * mix + b * (1 - mix))

            if dist > outer_r - 1.1:
                # Metallic rim so the disc edge reads against the black matrix.
                r = min(255, int(r * 0.25 + 110))
                g = min(255, int(g * 0.25 + 110))
                b = min(255, int(b * 0.25 + 120))
            elif dist > outer_r - rim_w:
                fade = (outer_r - dist) / rim_w
                shade = 0.45 + 0.55 * fade
                r = int(r * shade)
                g = int(g * shade)
                b = int(b * shade)

            # Specular streak + faint grooves so rotation is visible.
            ang = math.atan2(dy, dx)
            shine = (math.cos(ang - 0.6) * 0.5 + 0.5) ** 4 * 36
            groove = abs(math.sin(dist * 2.2)) * 8
            r = min(255, max(0, int(r + shine - groove)))
            g = min(255, max(0, int(g + shine - groove)))
            b = min(255, max(0, int(b + shine - groove)))
            pixels[x, y] = (r, g, b)

    return disc


def make_spin_frames(disc, matrix_w, matrix_h):
    frames = []
    for angle in range(0, 360, SPIN_STEP_DEG):
        rotated = disc.rotate(
            -angle,
            resample=Image.Resampling.BILINEAR,
            fillcolor=(0, 0, 0),
        )
        if rotated.size != (matrix_w, matrix_h):
            canvas = Image.new('RGB', (matrix_w, matrix_h), (0, 0, 0))
            ox = (matrix_w - rotated.size[0]) // 2
            oy = (matrix_h - rotated.size[1]) // 2
            canvas.paste(rotated, (ox, oy))
            rotated = canvas
        frames.append(rotated)
    return frames


if len(sys.argv) > 2:
    username = sys.argv[1]
    token_path = sys.argv[2]

    dir = os.path.dirname(__file__)
    filename = os.path.join(dir, '../config/rgb_options.ini')

    logging.basicConfig(
        format='%(asctime)s %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        filename='spotipy.log',
        level=logging.INFO,
    )
    logger = logging.getLogger('spotipy_logger')
    handler = RotatingFileHandler('spotipy.log', maxBytes=2000, backupCount=3)
    logger.addHandler(handler)

    config = configparser.ConfigParser()
    config.read(filename)

    options = RGBMatrixOptions()
    options.rows = int(config['DEFAULT']['rows'])
    options.cols = int(config['DEFAULT']['columns'])
    options.chain_length = int(config['DEFAULT']['chain_length'])
    options.parallel = int(config['DEFAULT']['parallel'])
    options.hardware_mapping = config['DEFAULT']['hardware_mapping']
    options.gpio_slowdown = int(config['DEFAULT']['gpio_slowdown'])
    options.brightness = int(config['DEFAULT']['brightness'])
    options.limit_refresh_rate_hz = int(config['DEFAULT']['refresh_rate'])
    # Keep root after init so we can still read .cache / images under /home/...
    options.drop_privileges = False

    default_image = os.path.join(dir, config['DEFAULT']['default_image'])
    print(default_image)
    fallback = Image.open(default_image).convert('RGB')

    matrix = RGBMatrix(options=options)
    disc_size = min(matrix.width, matrix.height)
    fallback_frames = make_spin_frames(
        make_cd_disc(fallback, disc_size),
        matrix.width,
        matrix.height,
    )
    frames = fallback_frames
    prevSong = ""
    last_poll = 0.0
    spin_t0 = time.time()
    canvas = matrix.CreateFrameCanvas()

    try:
        while True:
            now = time.time()
            if now - last_poll >= POLL_SECONDS:
                last_poll = now
                try:
                    info = getSongInfo(username, token_path)
                    if not info:
                        raise RuntimeError("No song playing or no Spotify token")

                    imageURL = info[1]
                    if prevSong != imageURL:
                        response = requests.get(imageURL, timeout=8)
                        response.raise_for_status()
                        image = Image.open(BytesIO(response.content))
                        disc = make_cd_disc(image, disc_size)
                        frames = make_spin_frames(disc, matrix.width, matrix.height)
                        prevSong = imageURL
                except Exception as e:
                    frames = fallback_frames
                    prevSong = ""
                    print(e)

            elapsed = time.time() - spin_t0
            angle = (elapsed * SPIN_RPM / 60.0) * 360.0
            idx = int(angle / SPIN_STEP_DEG) % len(frames)
            canvas.SetImage(frames[idx])
            canvas = matrix.SwapOnVSync(canvas)
    except KeyboardInterrupt:
        sys.exit(0)

else:
    print("Usage: %s username token_path" % (sys.argv[0],))
    sys.exit(1)
