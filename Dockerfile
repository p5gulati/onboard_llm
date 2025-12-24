FROM python:3.13

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt --verbose

COPY app/ /app/

EXPOSE 8000

CMD ["fastapi", "run", "main.py", "--port", "8000"]