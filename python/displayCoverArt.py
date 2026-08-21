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
    fallback.thumbnail((matrix.width, matrix.height), Image.Resampling.LANCZOS)

    prevSong = ""
    currentSong = ""

    try:
        while True:
            try:
                info = getSongInfo(username, token_path)
                if not info:
                    raise RuntimeError("No song playing or no Spotify token")

                imageURL = info[1]
                currentSong = imageURL

                if prevSong != currentSong:
                    response = requests.get(imageURL)
                    image = Image.open(BytesIO(response.content))
                    image.thumbnail((matrix.width, matrix.height), Image.Resampling.LANCZOS)
                    matrix.SetImage(image.convert('RGB'))
                    prevSong = currentSong

                time.sleep(1)
            except Exception as e:
                matrix.SetImage(fallback)
                print(e)
                time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(0)

else:
    print("Usage: %s username token_path" % (sys.argv[0],))
    sys.exit(1)
