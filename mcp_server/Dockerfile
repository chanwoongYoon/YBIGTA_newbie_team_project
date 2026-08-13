FROM python:3.11-slim

WORKDIR /app

COPY mcp_server/requirements.txt ./mcp_server/requirements.txt
RUN pip install --no-cache-dir --default-timeout=120 --retries 10 -r mcp_server/requirements.txt

COPY mcp_server ./mcp_server

EXPOSE 8000

CMD ["uvicorn", "mcp_server.server:app", "--host", "0.0.0.0", "--port", "8000"]
