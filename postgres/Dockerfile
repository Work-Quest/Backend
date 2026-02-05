FROM postgres:16-alpine

# We install python3 only to robustly parse DATABASE_URL (handles URL escaping, special chars, etc.)
RUN apk add --no-cache python3

COPY pg-entrypoint.sh /usr/local/bin/pg-entrypoint.sh
RUN chmod +x /usr/local/bin/pg-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/pg-entrypoint.sh"]
CMD ["postgres"]

