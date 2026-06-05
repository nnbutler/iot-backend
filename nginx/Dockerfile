FROM nginx:1.25-alpine

COPY nginx.conf /etc/nginx/nginx.conf
RUN rm /etc/nginx/conf.d/default.conf
COPY conf.d/ /etc/nginx/conf.d/

# Copy TLS certificates (mounted at runtime for production)
RUN mkdir -p /etc/nginx/certs /var/www/certbot
COPY certs/ /etc/nginx/certs/

EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider https://localhost/health --no-check-certificate || exit 1
