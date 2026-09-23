#!/usr/bin/env bash
# Issue the demonstration certificate authority and the mirror's leaf certificate.
#
# Demonstration-only. The root never leaves demo/ca and is trusted only inside
# the demo containers, so the mirror can be served over the HTTPS that
# app/security/urls.py requires without weakening any shipped control.
set -euo pipefail
cd "$(dirname "$0")/.."

MIRROR_HOST="${MIRROR_HOST:-tariff-mirror.demo}"
DAYS="${DAYS:-825}"

mkdir -p ca certs

if [[ -f ca/rootCA.pem && -f ca/rootCA-key.pem ]]; then
  printf '%s\n' "Reusing the existing demo root in demo/ca."
else
  openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
    -keyout ca/rootCA-key.pem -out ca/rootCA.pem \
    -subj "/CN=Ameria Tariff Monitor Demonstration Root/O=demo-only" \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" 2>/dev/null
  printf '%s\n' "Issued a new demo root in demo/ca."
fi

openssl req -newkey rsa:2048 -sha256 -nodes \
  -keyout "certs/${MIRROR_HOST}-key.pem" -out "certs/${MIRROR_HOST}.csr" \
  -subj "/CN=${MIRROR_HOST}/O=demo-only" 2>/dev/null

openssl x509 -req -in "certs/${MIRROR_HOST}.csr" \
  -CA ca/rootCA.pem -CAkey ca/rootCA-key.pem -CAcreateserial \
  -out "certs/${MIRROR_HOST}.pem" -days "${DAYS}" -sha256 \
  -extfile <(printf '%s\n' \
    "subjectAltName=DNS:${MIRROR_HOST}" \
    "basicConstraints=critical,CA:FALSE" \
    "keyUsage=critical,digitalSignature,keyEncipherment" \
    "extendedKeyUsage=serverAuth") 2>/dev/null

rm -f "certs/${MIRROR_HOST}.csr"
chmod 644 ca/rootCA.pem "certs/${MIRROR_HOST}.pem"
printf '%s\n' "Issued certs/${MIRROR_HOST}.pem for ${MIRROR_HOST}."
openssl x509 -in "certs/${MIRROR_HOST}.pem" -noout -subject -issuer -ext subjectAltName
