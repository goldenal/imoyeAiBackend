# ImoyeAI - RAG-Powered Document Intelligence Platform

## 🚀 Overview
ImoyeAI is a sophisticated Retrieval-Augmented Generation (RAG) platform built on FastAPI and Google Cloud's Vertex AI. It enables seamless management of document collections and provides intelligent querying capabilities through natural language processing.

## ✨ Key Features

- **Document Management**
  - Create and manage document corpora
  - Upload and store documents (PDF, TXT, DOCX)
  - Delete documents and corpora with confirmation
  - List available document collections

- **AI-Powered Search**
  - Natural language querying of document collections
  - Context-aware responses using Google's Gemini model
  - Support for both text and voice interactions

- **Technical Highlights**
  - FastAPI backend with WebSocket support for real-time communication
  - Google Cloud Storage integration for document storage
  - Production-ready with Docker support
  - Comprehensive API documentation with Swagger UI
  - CORS middleware for cross-origin requests

## 🛠️ Prerequisites

- Python 3.8+
- Google Cloud account with Vertex AI and Cloud Storage enabled
- Google Cloud SDK installed and configured
- Required environment variables set in `.env` file

## 🔧 Environment Variables

Create a `.env` file in the project root with the following variables:

```
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=your-gcp-region
GCS_BUCKET_NAME=your-bucket-name
```

## 🚀 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/imoyeai-backend.git
   cd imoyeai-backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 🏃 Running the Application

### Development Mode
```bash
uvicorn app.main:app --reload
```

### Production Mode (Using Gunicorn)
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

The application will be available at `http://localhost:8000`

## 📚 API Documentation

- **Interactive API Docs**: `http://localhost:8000/docs`
- **Alternative Docs**: `http://localhost:8000/redoc`

## 🌐 API Endpoints

### Document Management
- `POST /rag/corpora` - Create a new corpus
- `DELETE /rag/corpora/{corpus_name}` - Delete a corpus
- `GET /rag/corpora` - List all corpora
- `GET /rag/corpora/{corpus_name}` - Get corpus details

### Document Operations
- `POST /rag/documents` - Add documents to a corpus
- `DELETE /rag/documents/{document_id}` - Delete a document
- `POST /upload` - Upload a document to GCS and add to corpus

### Querying
- `POST /chat` - Send a query to the RAG agent
- `GET /ws/{session_id}` - WebSocket endpoint for real-time interaction

## 🐳 Docker Support

Build and run the application using Docker:

```bash
# Build the Docker image
docker build -t imoyeai-backend .

# Run the container
docker run -p 8000:8000 --env-file .env imoyeai-backend
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Endpoints

- `GET /`: Welcome endpoint that returns a JSON response with welcome message and timestamp
