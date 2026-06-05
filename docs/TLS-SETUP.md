# TLS/HTTPS Setup

## Development (Self-Signed Certificates)

The project includes self-signed certificates for local development:

```bash
./scripts/generate-certs.sh
```

This creates:
- `nginx/certs/privkey.pem` — private key
- `nginx/certs/fullchain.pem` — certificate

Access the application:
- HTTP: `http://localhost:8080` (redirects to HTTPS)
- HTTPS: `https://localhost:8443` (self-signed, use `-k` flag with curl)

## Production (Let's Encrypt)

### Prerequisites
- Domain name pointing to your DigitalOcean droplet
- Port 80 and 443 open to the internet

### Initial Setup

1. **Stop nginx temporarily** (for ACME challenge):
```bash
docker compose down
```

2. **Get Let's Encrypt certificate** (on the DigitalOcean droplet):
```bash
sudo apt-get update && sudo apt-get install -y certbot
certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
```

3. **Update docker-compose.yml** to use Let's Encrypt certs:
```yaml
nginx:
  volumes:
    - /etc/letsencrypt/live/yourdomain.com:/etc/nginx/certs:ro
    - /var/www/certbot:/var/www/certbot:ro
  ports:
    - "80:80"
    - "443:443"
```

4. **Start the application**:
```bash
docker compose up -d
```

### Certificate Auto-Renewal

Let's Encrypt certificates expire every 90 days. Set up automatic renewal:

```bash
# Create renewal script
sudo tee /usr/local/bin/renew-certs.sh << 'EOF'
#!/bin/bash
certbot renew --quiet
docker compose -f /path/to/docker-compose.yml restart nginx
EOF

chmod +x /usr/local/bin/renew-certs.sh

# Add to crontab (runs every 60 days at 2:30 AM)
(crontab -l; echo "30 2 * * 0 /usr/local/bin/renew-certs.sh") | crontab -
```

## Security Features

The Nginx configuration includes:

- **HSTS** — Browsers forced to use HTTPS for 1 year
- **X-Content-Type-Options** — Prevents MIME type sniffing
- **X-Frame-Options** — Protects against clickjacking
- **X-XSS-Protection** — Legacy XSS protection
- **TLS 1.2+ only** — No older insecure protocols
- **Rate limiting** — Auth (10 req/min), API (100 req/min)

## Testing

Check certificate info:
```bash
openssl x509 -in nginx/certs/fullchain.pem -text -noout
```

Test HTTPS:
```bash
curl -k https://localhost:8443/health  # dev
curl https://yourdomain.com/health      # prod (if Let's Encrypt cert)
```

Check rate limiting:
```bash
# Should return 429 after burst limit exceeded
for i in {1..20}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  https://localhost:8443/api/auth/login -H "Content-Type: application/json" \
  -d '{"username":"support","password":"support123"}' -k; done
```
