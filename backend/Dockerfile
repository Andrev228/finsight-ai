FROM python:3.12-slim AS builder

ARG PIP_NO_INDEX=0

WORKDIR /build

COPY requirements.txt .
COPY .wheels /wheels

RUN if [ "$PIP_NO_INDEX" = "1" ]; then \
      pip install --prefix=/install --no-index --find-links=/wheels -r requirements.txt; \
    else \
      pip install --prefix=/install --no-cache-dir -r requirements.txt; \
    fi

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .
RUN rm -rf /app/.wheels

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
