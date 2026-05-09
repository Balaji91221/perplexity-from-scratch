FROM mcr.microsoft.com/playwright/python:v1.47.0-noble

WORKDIR /app

# The base image's preinstalled Playwright lives in a venv that uvicorn doesn't see.
# Reinstall the Python package into the system Python where uvicorn runs;
# the Chromium binary is already cached in the image.
RUN pip install --no-cache-dir --break-system-packages \
    fastapi==0.115.0 \
    uvicorn[standard]==0.30.6 \
    trafilatura==1.12.2 \
    playwright==1.47.0

COPY browser_pool.py extract.py actions.py main.py ./

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
