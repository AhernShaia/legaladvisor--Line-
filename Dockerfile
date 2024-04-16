# 使用 Python 3.12 slim 做為基礎鏡像
FROM python:3.12-slim

# 指定工作目錄
WORKDIR /app

# 安裝套件
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt 並安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache/pip

# 複製目錄下的文件
COPY . .

# 開放端口
EXPOSE 5000

# 啟動 Flask 應用
CMD ["flask", "run", "--host=0.0.0.0"]