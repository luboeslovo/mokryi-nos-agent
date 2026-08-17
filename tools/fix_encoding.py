from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent

FILE = (
    PROJECT_DIR
    / "tools"
    / "export_rfm_to_sheets.py"
)


text = FILE.read_text(
    encoding="utf-8-sig"
)


raw = bytearray()

for char in text:

    try:

        raw.extend(
            char.encode("cp1251")
        )

    except UnicodeEncodeError:

        code = ord(char)

        if 0 <= code <= 255:

            raw.append(code)

        else:

            raise


fixed = bytes(raw).decode(
    "utf-8"
)


FILE.write_text(
    fixed,
    encoding="utf-8",
)


print("Кодировка восстановлена.")
print(FILE)