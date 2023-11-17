#!/usr/bin/env python3.9

from dotenv import load_dotenv
load_dotenv("email.env")
from generate_and_upload import serve_api

serve_api('web')
