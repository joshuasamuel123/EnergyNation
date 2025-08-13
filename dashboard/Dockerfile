
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py /app/
COPY *.xlsx /app/

EXPOSE 7860
CMD ["gunicorn", "app:server", "-b", "0.0.0.0:7860", "--timeout", "120"]
