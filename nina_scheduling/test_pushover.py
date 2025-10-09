import http.client
import urllib.parse
import os
from typing import Tuple, Optional

# Simple Python 3 example using the standard library (no external deps).
# Replace token/user with your own values or load from a secrets file.
def send_pushover(token: str, user: str, message: str) -> None:
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    params = urllib.parse.urlencode({
        "token": token,
        "user": user,
        "message": message,
    })
    headers = {"Content-type": "application/x-www-form-urlencoded"}
    conn.request("POST", "/1/messages.json", params, headers)
    resp = conn.getresponse()
    print(resp.status, resp.reason)
    print(resp.read().decode())


if __name__ == '__main__':
    # Load credentials from local secrets file, or environment variables as fallback
    def load_secrets() -> Tuple[Optional[str], Optional[str]]:
        try:
            # Local file should be named pushover_secrets.py and contain PUSHOVER_TOKEN and PUSHOVER_USER
            from pushover_secrets import PUSHOVER_TOKEN, PUSHOVER_USER  # type: ignore
            return PUSHOVER_TOKEN, PUSHOVER_USER
        except Exception:
            # Fallback to environment variables
            return os.environ.get('PUSHOVER_TOKEN'), os.environ.get('PUSHOVER_USER')

    token, user = load_secrets()
    if not token or not user:
        print('Pushover credentials not found. Create nina_scheduling/pushover_secrets.py or set PUSHOVER_TOKEN and PUSHOVER_USER env vars.')
    else:
        send_pushover(token=token, user=user, message="hello world")