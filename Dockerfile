FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e "." 2>/dev/null || pip install fastapi uvicorn pydantic pandas numpy yfinance rich click anthropic openai python-dotenv sse-starlette
COPY agent/ ./agent/
ENV PYTHONPATH=/app/agent
CMD ["python", "agent/api_server.py"]
