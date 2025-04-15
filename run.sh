#!/bin/bash
uvicorn app.main:app --reload --port 8000

chmod +x run.sh