"""Run the API: ``python -m evidence_trail``."""

import uvicorn

from evidence_trail.api.app import create_app

if __name__ == "__main__":
    uvicorn.run(create_app(), host="127.0.0.1", port=8000)
