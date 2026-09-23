#!/usr/bin/env bash
# Trust the demonstration root, then hand off to the shipped command unchanged.
#
# Two clients have to trust it: httpx reads SSL_CERT_FILE (httpx/_config.py:35),
# and Playwright's Chromium reads the NSS database. Neither the application nor
# its security controls are modified; the root is simply made known to the
# containers that talk to the mirror.
set -euo pipefail

ROOT_CA=/demo/ca/rootCA.pem
BUNDLE="${SSL_CERT_FILE:-/tmp/demo-ca-bundle.pem}"
NICKNAME=ameria-demo-root

if [[ -f "${ROOT_CA}" ]]; then
  certifi_path="$(uv run python -c 'import certifi; print(certifi.where())')"
  cat "${certifi_path}" "${ROOT_CA}" > "${BUNDLE}"

  mkdir -p "${HOME}/.pki/nssdb"
  certutil -d "sql:${HOME}/.pki/nssdb" -N --empty-password >/dev/null 2>&1 || true
  certutil -d "sql:${HOME}/.pki/nssdb" -D -n "${NICKNAME}" >/dev/null 2>&1 || true
  certutil -d "sql:${HOME}/.pki/nssdb" -A -t "C,," -n "${NICKNAME}" -i "${ROOT_CA}"

  printf '%s\n' "demo: trusted ${ROOT_CA} for httpx (${BUNDLE}) and Chromium (NSS)" >&2
else
  printf '%s\n' "demo: no ${ROOT_CA}; run demo/bin/make-certs.sh before filming" >&2
fi

exec "$@"
