#!/bin/sh
set -e

CERT_DIR="/etc/nginx/certs"
KEY="$CERT_DIR/privkey.pem"
CERT="$CERT_DIR/fullchain.pem"

if [ ! -f "$KEY" ] || [ ! -f "$CERT" ]; then
  echo "No TLS certs found — generating self-signed certs for development..."
  mkdir -p "$CERT_DIR"
  openssl req -x509 -newkey rsa:2048 \
    -keyout "$KEY" -out "$CERT" \
    -days 365 -nodes \
    -subj "/C=US/ST=CA/L=San Francisco/O=Device Manager/CN=localhost"
  echo "Self-signed certs generated."
fi

exec nginx -g "daemon off;"
