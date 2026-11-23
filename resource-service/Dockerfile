# python:3.12-slim (Debian) instead of python:3.12-alpine (musl libc):
# psycopg2-binary ships prebuilt wheels for standard glibc Linux on both
# x86_64 and ARM64 (Apple Silicon). Alpine's musl libc can't always use those
# wheels and would force compiling the driver from C source inside the image
# (needing gcc, libpq headers, etc.) -- slower builds and more attack surface
# in the final image for no benefit here.
FROM python:3.12-slim

WORKDIR /app

# curl is used by the docker-compose healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--ssl-keyfile", "/certs/resource-service.key", \
     "--ssl-certfile", "/certs/resource-service.crt", \
     "--ssl-ca-certs", "/certs/ca.crt", \
     "--ssl-cert-reqs", "2"]
