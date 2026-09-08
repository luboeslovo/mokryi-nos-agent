"""Fail-closed, app-scoped TLS configuration for the GigaChat SDK."""

from __future__ import annotations

import hashlib
import os
import ssl
from collections.abc import Mapping
from pathlib import Path


CA_BUNDLE_ENV = "GIGACHAT_CA_BUNDLE_FILE"
LOCAL_APP_DATA_ENV = "LOCALAPPDATA"
APP_CA_BUNDLE_PARTS = (
    "mokryi-nos-agent",
    "tls",
    "gigachat-ca-bundle.pem",
)
RUSSIAN_TRUSTED_ROOT_CA_SHA256 = (
    "D26D2D0231B7C39F92CC738512BA5410"
    "3519E4405D68B5BD703E9788CA8ECF31"
)


def _configured_bundle_path(environment: Mapping[str, str]) -> Path:
    configured_path = str(environment.get(CA_BUNDLE_ENV, "")).strip()
    if configured_path:
        return Path(configured_path).expanduser()

    local_app_data = str(environment.get(LOCAL_APP_DATA_ENV, "")).strip()
    if not local_app_data:
        raise RuntimeError(
            "GigaChat CA bundle не настроен: задайте "
            f"{CA_BUNDLE_ENV} или {LOCAL_APP_DATA_ENV}."
        )

    return Path(local_app_data).joinpath(*APP_CA_BUNDLE_PARTS)


def get_gigachat_ca_bundle_file(
    environment: Mapping[str, str] | None = None,
    *,
    required_root_sha256: str = RUSSIAN_TRUSTED_ROOT_CA_SHA256,
) -> str:
    """Return a verified CA bundle path or fail before creating the client."""

    effective_environment = os.environ if environment is None else environment
    bundle_path = _configured_bundle_path(effective_environment).resolve()

    if not bundle_path.is_file():
        raise RuntimeError(
            "GigaChat CA bundle отсутствует. "
            f"Проверьте {CA_BUNDLE_ENV} и локальную TLS-конфигурацию."
        )

    try:
        context = ssl.create_default_context(cafile=str(bundle_path))
        bundle_fingerprints = {
            hashlib.sha256(certificate).hexdigest().upper()
            for certificate in context.get_ca_certs(binary_form=True)
        }
    except (OSError, ssl.SSLError) as error:
        raise RuntimeError(
            "GigaChat CA bundle повреждён или не является валидным CA bundle."
        ) from error

    normalized_required_fingerprint = (
        required_root_sha256.replace(":", "").strip().upper()
    )
    if normalized_required_fingerprint not in bundle_fingerprints:
        raise RuntimeError(
            "GigaChat CA bundle не содержит проверенный "
            "Russian Trusted Root CA."
        )

    return str(bundle_path)
