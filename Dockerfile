FROM python:3.13
EXPOSE 8083
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]

ENV PYTHONUNBUFFERED=1

ENV AWS_REGION=""
ENV AWS_Q3=""
ENV SENDER_EMAIL=""
ENV RECIPIENT_EMAIL=""