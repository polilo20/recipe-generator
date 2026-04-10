FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
COPY ./app ./app
COPY ./processing/ingredients_map.json ./processing/ingredients_map.json

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-m", "uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]