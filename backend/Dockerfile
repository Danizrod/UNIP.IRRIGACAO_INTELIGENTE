FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.lock.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app /app/app
COPY tests /app/tests
COPY tools/simulate.py /app/simulate.py
COPY tools/integration_check.py /app/integration_check.py
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
