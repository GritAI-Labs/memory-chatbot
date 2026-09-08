FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Cloud demo narrates via Claude (can't reach a local fleet); ANTHROPIC_API_KEY is a Space secret.
# NOTE: memory.db lives in the container FS — persists within a run, resets on rebuild (fine for a demo).
ENV PORT=7860 MEMBOT_LLM_BACKEND=claude ANTHROPIC_MODEL=claude-haiku-4-5 PYTHONUNBUFFERED=1
EXPOSE 7860
CMD ["python", "app.py"]
