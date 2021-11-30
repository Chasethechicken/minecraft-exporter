FROM docker.io/library/python:3.9-alpine

COPY requirements.txt minecraft_exporter.py /
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

ENTRYPOINT ["python","-u","minecraft_exporter.py"]
