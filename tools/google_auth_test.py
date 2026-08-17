from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


PROJECT_DIR = Path(__file__).resolve().parent.parent

CREDENTIALS_FILE = PROJECT_DIR / "credentials.json"
TOKEN_FILE = PROJECT_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]


def get_credentials():

    creds = None

    if TOKEN_FILE.exists():

        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES,
        )

    if not creds or not creds.valid:

        if (
            creds
            and creds.expired
            and creds.refresh_token
        ):

            creds.refresh(
                Request()
            )

        else:

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES,
            )

            creds = flow.run_local_server(
                port=0
            )

        TOKEN_FILE.write_text(
            creds.to_json(),
            encoding="utf-8",
        )

    return creds


def main():

    print()
    print("=" * 70)
    print("ПРОВЕРКА GOOGLE SHEETS")
    print("=" * 70)

    creds = get_credentials()

    service = build(
        "sheets",
        "v4",
        credentials=creds,
    )

    print()
    print("OAuth авторизация успешна.")
    print("Google Sheets API подключён.")
    print()
    print(f"token.json: {TOKEN_FILE}")

    print("=" * 70)


if __name__ == "__main__":
    main()