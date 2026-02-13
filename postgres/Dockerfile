FROM postgres:16-alpine

# We install python3 only to robustly parse DATABASE_URL (handles URL escaping, special chars, etc.)
RUN apk add --no-cache python3

COPY pg-entrypoint.sh /usr/local/bin/pg-entrypoint.sh
# On Windows, scripts can get CRLF line endings which break Linux shebang execution
# with: "exec ...: no such file or directory". Normalize to LF and make executable.
RUN sed -i 's/\r$//' /usr/local/bin/pg-entrypoint.sh && chmod +x /usr/local/bin/pg-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/pg-entrypoint.sh"]
CMD ["postgres"]

