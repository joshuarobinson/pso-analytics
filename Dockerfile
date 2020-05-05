FROM python:3.6-alpine

RUN pip install kubernetes purity_fb purestorage tabulate

COPY *.py .
