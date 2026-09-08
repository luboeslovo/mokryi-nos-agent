import hashlib
import shutil
import ssl
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import certifi


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from gigachat_tls import (
    APP_CA_BUNDLE_PARTS,
    CA_BUNDLE_ENV,
    LOCAL_APP_DATA_ENV,
    get_gigachat_ca_bundle_file,
)


def certifi_fingerprint() -> str:
    context = ssl.create_default_context(cafile=certifi.where())
    certificate = context.get_ca_certs(binary_form=True)[0]
    return hashlib.sha256(certificate).hexdigest().upper()


class GigaChatTlsConfigTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.temp_path = Path(self.temporary_directory.name)

    def copy_valid_bundle(self, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(certifi.where(), destination)
        return destination

    def test_explicit_app_bundle_is_validated_and_returned(self):
        bundle = self.copy_valid_bundle(self.temp_path / "explicit.pem")

        result = get_gigachat_ca_bundle_file(
            {CA_BUNDLE_ENV: str(bundle)},
            required_root_sha256=certifi_fingerprint(),
        )

        self.assertEqual(Path(result), bundle.resolve())

    def test_local_app_data_bundle_is_used_by_default(self):
        bundle = self.copy_valid_bundle(
            self.temp_path.joinpath(*APP_CA_BUNDLE_PARTS)
        )

        result = get_gigachat_ca_bundle_file(
            {LOCAL_APP_DATA_ENV: str(self.temp_path)},
            required_root_sha256=certifi_fingerprint(),
        )

        self.assertEqual(Path(result), bundle.resolve())

    def test_missing_bundle_fails_before_ssl_context_creation(self):
        with patch("gigachat_tls.ssl.create_default_context") as create_context:
            with self.assertRaisesRegex(RuntimeError, "bundle отсутствует"):
                get_gigachat_ca_bundle_file(
                    {CA_BUNDLE_ENV: str(self.temp_path / "missing.pem")}
                )

        create_context.assert_not_called()

    def test_invalid_bundle_fails_without_insecure_fallback(self):
        bundle = self.temp_path / "invalid.pem"
        bundle.write_text("not a certificate", encoding="utf-8")

        with self.assertRaisesRegex(RuntimeError, "повреждён"):
            get_gigachat_ca_bundle_file({CA_BUNDLE_ENV: str(bundle)})

    def test_bundle_without_required_root_is_rejected(self):
        bundle = self.copy_valid_bundle(self.temp_path / "certifi-only.pem")

        with self.assertRaisesRegex(RuntimeError, "Russian Trusted Root CA"):
            get_gigachat_ca_bundle_file({CA_BUNDLE_ENV: str(bundle)})


if __name__ == "__main__":
    unittest.main()
