#!/bin/bash
# Generate self-signed SSL certificates for development
# For production, use Let's Encrypt with certbot

set -e

CERT_DIR="./nginx/certs"
DAYS=365

mkdir -p "$CERT_DIR"

echo "Generating self-signed certificate for development..."

openssl req -x509 -newkey rsa:2048 -keyout "$CERT_DIR/privkey.pem" -out "$CERT_DIR/fullchain.pem" \
    -days $DAYS -nodes \
    -subj "/C=US/ST=CA/L=San Francisco/O=Device Manager/CN=localhost"

echo "✓ Generated self-signed certificate"
echo "  Private key: $CERT_DIR/privkey.pem"
echo "  Certificate: $CERT_DIR/fullchain.pem"
echo ""
echo "For production (DigitalOcean), use Let's Encrypt:"
echo "  certbot certonly --standalone -d yourdomain.com"
echo "  Then mount the certs from /etc/letsencrypt/live/"
