import os
from dotenv import load_dotenv

load_dotenv()

# MTN MoMo credentials – set these in your .env file
MOMO_BASE_URL         = os.getenv("MOMO_BASE_URL", "https://sandbox.momodeveloper.mtn.com")
MOMO_SUBSCRIPTION_KEY = os.getenv("MOMO_SUBSCRIPTION_KEY", "")
MOMO_API_USER         = os.getenv("MOMO_API_USER", "")
MOMO_API_KEY          = os.getenv("MOMO_API_KEY", "")
MOMO_ENV              = os.getenv("MOMO_ENV", "sandbox")          # "sandbox" or "mtncongo" / "mtnghana" etc.
MOMO_CURRENCY         = os.getenv("MOMO_CURRENCY", "EUR")         # sandbox uses EUR; production uses your local currency

# App secret – used to sign stream tokens
SECRET_KEY     = os.getenv("SECRET_KEY", "change-me-to-a-random-secret")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "zynara2026")

# Set to True in production
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
