FROM python:3.10

RUN apt-get update && \
    apt-get install -y \
    wget curl gnupg2 \
    libgtk-3-0 libgbm-dev libnss3 libatk-bridge2.0-0 libxkbcommon0 \
    libasound2 libatk1.0-0 libcups2 libdrm2 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libxrender1 libxss1 libxtst6 fonts-liberation libappindicator3-1 \
    libgdk-pixbuf-2.0-0 libffi7 libncurses5 libx11-xcb1 libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 libpangocairo-1.0-0 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt && playwright install

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
