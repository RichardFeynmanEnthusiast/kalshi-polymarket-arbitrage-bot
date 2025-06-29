FROM python:3.11-slim

WORKDIR /app

COPY ../shared_libraries ./
COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir  ../shared_libraries/shared_wallets_container/
RUN pip install --no-cache-dir  ../shared_libraries/shared_infrastructure_container/

CMD ["python", "main.py"]