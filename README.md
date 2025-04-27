# Compliwave

A B2B compliance document review platform that helps organizations ensure their documents meet regulatory and compliance requirements.

## Features

- Document Management
  - Upload and store documents (PDF, DOCX, PPTX)
  - Version control
  - Audit trails
- Compliance Checking
  - Rule-based checks
  - AI-powered analysis
  - Violation detection
- Organization Management
  - Multi-tenant support
  - Role-based access control
  - Compliance rule management

## Tech Stack

- Backend: FastAPI, Python
- Database: PostgreSQL
- Storage: AWS S3
- AI: Azure OpenAI
- Containerization: Docker
- Orchestration: Kubernetes

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/compliwave.git
cd compliwave
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Install dependencies:
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

4. Set up the database:
```bash
cd backend
./init_db.sh
```

5. Run the application:
```bash
# Backend
cd backend
uvicorn main:app --reload

# Frontend
cd frontend
npm run dev
```

## Development

- Backend API documentation: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Deployment

See [deployment/README.md](deployment/README.md) for deployment instructions.

## License

MIT 