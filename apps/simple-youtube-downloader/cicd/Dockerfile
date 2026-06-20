FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /

RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y ffmpeg
COPY requirements.lock .
RUN sed '/-e/d' requirements.lock > requirements.txt
RUN pip install -r requirements.txt

COPY src/ src/
COPY targetDir/ targetDir/
COPY .streamlit/ .streamlit/

EXPOSE 8501


CMD ["streamlit", "run", "src/main.py","--server.port=8501", "--server.address=0.0.0.0"]
