# FastAPI Production Backend

A production-grade FastAPI backend with basic welcome route.

## Features

- FastAPI framework
- CORS middleware support
- Health check endpoint
- Production-ready configuration
- Docker support

## Prerequisites

- Python 3.8+
- pip

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

```bash
uvicorn main:app --reload
```

The application will be available at `http://localhost:8000`

## API Documentation

Swagger UI: `http://localhost:8000/docs`

## Endpoints

- `GET /`: Welcome endpoint that returns a JSON response with welcome message and timestamp
