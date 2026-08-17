from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


PROJECT_DIR = Path(__file__).resolve().parent.parent

CREDENTIALS_FILE = PROJECT_DIR / "credentials.json"
TOKEN_FILE = PROJECT_DIR / "token.json"

SPREADSHEET_ID_FILE = (
    PROJECT_DIR / "rfm_spreadsheet_id.txt"
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

SPREADSHEET_TITLE = "Мокрый нос — RFM"


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
    print("GOOGLE SHEETS — RFM")
    print("=" * 70)

    if SPREADSHEET_ID_FILE.exists():

        spreadsheet_id = (
            SPREADSHEET_ID_FILE
            .read_text(encoding="utf-8")
            .strip()
        )

        if spreadsheet_id:

            print()
            print(
                "Таблица уже была создана."
            )

            print(
                "Spreadsheet ID:"
            )

            print(
                spreadsheet_id
            )

            print()
            print(
                "Ссылка:"
            )

            print(
                "https://docs.google.com/"
                f"spreadsheets/d/{spreadsheet_id}/edit"
            )

            print()
            print("=" * 70)

            return

    creds = get_credentials()

    service = build(
        "sheets",
        "v4",
        credentials=creds,
    )

    body = {
        "properties": {
            "title": SPREADSHEET_TITLE,
            "locale": "ru_RU",
            "timeZone": "Europe/Moscow",
        },
        "sheets": [
            {
                "properties": {
                    "title": "RFM",
                    "gridProperties": {
                        "rowCount": 3000,
                        "columnCount": 20,
                        "frozenRowCount": 1,
                    },
                }
            },
            {
                "properties": {
                    "title": "Сводка",
                    "gridProperties": {
                        "rowCount": 200,
                        "columnCount": 10,
                    },
                }
            },
        ],
    }

    spreadsheet = (
        service
        .spreadsheets()
        .create(
            body=body,
            fields="spreadsheetId,spreadsheetUrl",
        )
        .execute()
    )

    spreadsheet_id = spreadsheet[
        "spreadsheetId"
    ]

    spreadsheet_url = spreadsheet[
        "spreadsheetUrl"
    ]

    SPREADSHEET_ID_FILE.write_text(
        spreadsheet_id,
        encoding="utf-8",
    )

    print()
    print("Таблица создана.")

    print()
    print("Spreadsheet ID:")
    print(spreadsheet_id)

    print()
    print("Ссылка:")
    print(spreadsheet_url)

    print()
    print(
        f"ID сохранён в: "
        f"{SPREADSHEET_ID_FILE}"
    )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()