# ==============================================================================
# Nginx Load Balancer Dockerfile
# Lightweight Alpine-based image for reverse proxy
# ==============================================================================

FROM nginx:1.25-alpine

# Install additional tools for health checks and monitoring
RUN apk add --no-cache \
    curl \
    ca-certificates

# Remove default nginx configuration
RUN rm /etc/nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create custom error pages directory
RUN mkdir -p /usr/share/nginx/html

# Create custom 50x error page
RUN echo '<!DOCTYPE html><html><head><title>Service Temporarily Unavailable</title><style>body{font-family:Arial,sans-serif;text-align:center;padding:50px;}h1{color:#e74c3c;}</style></head><body><h1>503 Service Temporarily Unavailable</h1><p>The service is currently unavailable. Please try again in a few moments.</p></body></html>' > /usr/share/nginx/html/50x.html

# Create log directories
RUN mkdir -p /var/log/nginx && \
    chown -R nginx:nginx /var/log/nginx

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

EXPOSE 80 443

# Use nginx user for security
USER nginx

CMD ["nginx"]
