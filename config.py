import os

from dotenv import load_dotenv

load_dotenv()

# Paradex config
PRIVATE_KEY = os.environ["PRIVATE_KEY"]

# Bitget config
BITGET_API_KEY = os.environ["BITGET_API_KEY"]
BITGET_API_SECRET = os.environ["BITGET_API_SECRET"]
BITGET_API_PASSPHRASE = os.environ["BITGET_API_PASSPHRASE"]

POSITION_USD_LIMITS = [50, 1000]  # min and max position in usd
