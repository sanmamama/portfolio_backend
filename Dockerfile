# ベースイメージ
FROM python:3.10-slim

# 環境変数の設定
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 作業ディレクトリを設定
WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    libpq-dev gcc && \
    pip install --upgrade pip

# アプリケーションのソースコードをコピー
COPY . .

# 依存関係のインストール
RUN pip install -r requirements.txt
RUN pip install gunicorn

# ポートを開放
EXPOSE 8000

# サーバーを起動
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "rest.wsgi:application"]
