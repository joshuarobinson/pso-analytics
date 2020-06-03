FROM python:3.6-alpine

RUN pip install kubernetes prometheus_client purity_fb purestorage tabulate

COPY *.py .
