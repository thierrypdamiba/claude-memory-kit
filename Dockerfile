FROM python:3.11-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
RUN uv pip install --system -e .
EXPOSE 7749
CMD ["uvicorn", "claude_memory_kit.api.app:app", "--host", "0.0.0.0", "--port", "7749"]
