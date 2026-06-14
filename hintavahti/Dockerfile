# Official Playwright image: Chromium + all OS dependencies are pre-installed,
# so we never run the fragile `playwright install --with-deps`. Multi-arch
# (amd64 + arm64). The image version MUST match the playwright pip version.
FROM mcr.microsoft.com/playwright/python:v1.49.1-noble

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OPTIONS_PATH=/data/options.json

WORKDIR /app

# Browsers are already baked into the image (PLAYWRIGHT_BROWSERS_PATH=/ms-playwright).
# We only install the Python dependencies. lxml/pydantic ship prebuilt wheels,
# so no compiler is needed.
COPY requirements.txt .
RUN pip install --break-system-packages -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
