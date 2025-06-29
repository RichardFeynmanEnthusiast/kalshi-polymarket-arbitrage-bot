FROM python:3.11-slim

WORKDIR double-time-hft/app

COPY ../shared_libraries ./
COPY double-time-hft/app ./app/
COPY double-time-hft/requirements.txt ./

ENV PYTHONPATH=/double-time-hft/app/

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir --no-cache-dir "shared_wallets_container/"
RUN pip install --no-cache-dir --no-cache-dir "shared_infrastructure_container/"

CMD ["python", "app/main.py"]
