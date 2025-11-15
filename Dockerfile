FROM python:3.10

RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    libgtk-3-0 \
    libgbm-dev \
    libnss3 \
    libxkbcommon0 \
    libasound2 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    fonts-liberation \
    libappindicator3-1 \
    libffi7 \
    libncurses5 \
    libx11-xcb1 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libpangocairo-1.0-0 \
    --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN playwright install

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
