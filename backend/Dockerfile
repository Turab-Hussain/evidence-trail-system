FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
# The gemini extra is included so EVIDENCE_LLM_PROVIDER=gemini works out of the box.
RUN pip install --no-cache-dir ".[gemini]" && useradd -m app && mkdir /data && chown app /data
USER app
ENV EVIDENCE_DB_PATH=/data/evidence_trail.db
EXPOSE 8000
CMD ["uvicorn", "evidence_trail.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
