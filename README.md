# ☁️ Cloud-Native AI Meeting Insights

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

> **Self-hostable meeting intelligence platform** — Transform hours of audio into actionable insights with microservices architecture, async processing, and multi-language AI transcription.

A production-ready, **cloud-native** meeting assistant powered by **React/Next.js** frontend, **FastAPI** backend, **PostgreSQL** database, **Redis** queue, and **AI models** including faster-whisper and GPT.

---

## 🏗️ Architecture

**Microservices Design:**
- **Frontend Service** (React/Next.js) - User interface and API interactions
- **API Service** (FastAPI) - REST API, file uploads, job queueing
- **Worker Service** (Python) - Async transcription and AI processing
- **Database** (PostgreSQL) - Meeting data and metadata storage
- **Cache/Queue** (Redis) - Job queuing and background processing

**Processing Pipeline:**
1. Upload audio → API saves file and queues job
2. Worker picks up job → Transcribes with faster-whisper
3. Worker generates summary → Updates database
4. Frontend polls for results → Displays insights

---

## ✨ Features

🎙️ **Multi-Language Transcription (5+ Languages)**
- English, Chinese (Mandarin), Spanish, French, Japanese
- Automatic language detection
- High-accuracy speech-to-text with faster-whisper

🧠 **AI-Powered Summarization**
- GPT-generated meeting summaries
- Action items and key decisions extraction
- Keyword identification and tagging

🚀 **Async Processing & Scaling**
- Redis-based job queuing
- Worker retry logic and error handling
- Horizontal scaling ready

📊 **Rich Metadata & Search**
- Duration tracking and file management
- Full-text search across transcripts
- Meeting history and organization

☁️ **Cloud-Native & Self-Hostable**
- Docker Compose for local development
- Production-ready microservices
- Easy deployment to any cloud provider

---

## 🚀 Deployment Options

### Local Development (3 Steps)

#### Step 1: Clone and Configure
```bash
git clone https://github.com/yourusername/cloud-native-ai-meeting-insights.git
cd cloud-native-ai-meeting-insights

# Create environment file
cp .env.example .env
```

#### Step 2: Set Environment Variables
Edit `.env` with your configuration:
```env
# Database
POSTGRES_USER=meetinguser
POSTGRES_PASSWORD=yourpassword
POSTGRES_DB=meeting_insights

# OpenAI API (for summaries)
OPENAI_API_KEY=your_openai_api_key

# Optional: API security
API_KEY=your_optional_api_key

# Model configuration
FW_MODEL=base.en
FW_COMPUTE_TYPE=float32
```

#### Step 3: Start All Services
```bash
docker compose up --build
```

**Local Access Points:**
- 🌐 **Frontend**: http://localhost:3000
- 🔧 **API Docs**: http://localhost:8000/docs
- 📊 **Worker Health**: http://localhost:8001/health
- 🗄️ **Database**: localhost:5433
- 🔄 **Redis**: localhost:6379

### ☁️ AWS EKS Production Deployment

**🚀 TRUE ONE-CLICK DEPLOYMENT** - Deploy everything with a single command! Zero configuration required.

```bash
cd infra
./one-click-deploy.sh
```

✨ **Completely automated:** Auto-detects AWS config, generates unique names, builds images, deploys infrastructure (10–20 minutes).

**Prerequisites (one-time setup):**
```bash
# 1. Install AWS CLI and configure credentials
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install
aws configure  # Enter your AWS credentials

# 2. Set OpenAI API key (for AI summaries)
export OPENAI_API_KEY="your-key-here"
```

#### Alternative: GitHub Actions Deployment

#### GitHub Secrets Required
```
AWS_ACCESS_KEY_ID     # AWS access key
AWS_SECRET_ACCESS_KEY # AWS secret key  
OPENAI_API_KEY        # OpenAI API key for summaries
API_KEY               # Optional API security key
```

#### Automated Deployment via GitHub Actions

1. **Manual Trigger**: Go to Actions → "Deploy to AWS EKS" → Run workflow
2. **Select Environment**: Choose `dev`, `staging`, or `prod`
3. **Choose Action**: 
   - `plan` - Review infrastructure changes (always run first)
   - `apply` - Deploy infrastructure and application
   - `destroy` - Remove all AWS resources

#### Local Terraform Deployment

```bash
# Navigate to infrastructure directory
cd infra

# Check prerequisites and initialize
./deploy.sh check
./deploy.sh init

# Plan infrastructure (review costs and resources)
./deploy.sh plan

# Deploy to AWS (10-20 minutes)
./deploy.sh apply

# Configure kubectl and deploy application
./deploy.sh deploy-app

# Get cluster information
./deploy.sh info
```

#### Cost Optimization Features
- **t3.micro/t3.medium instances** (free tier eligible where possible)
- **Single NAT Gateway** (vs 3 for HA)
- **Minimal node count** (2 nodes, auto-scaling to 4)
- **Small database** (db.t3.micro, 20GB storage)
- **Cost monitoring** via AWS resource tags

#### Infrastructure Components
- **EKS Cluster** (Kubernetes v1.28)
- **RDS PostgreSQL** (managed database)
- **ElastiCache Redis** (managed cache)
- **VPC with public/private subnets**
- **Application Load Balancer**
- **Auto-scaling node groups**

#### Estimated Monthly Costs (US-West-2)
- **Development**: ~$50-80/month
- **Production**: ~$150-250/month
- **Note**: Costs vary by usage, region, and AWS pricing changes

---

## ⚡ Performance & Scaling

Our platform is optimized for **<150ms median API latency** and **real-time audio processing**:

### Database Optimizations
- **PostgreSQL indexes**: `created_at`, `(filename, language)`, GIN indexes for full-text search
- **Query optimization**: Selective indexes reduce query time from ~300ms to <50ms
- **Connection pooling**: Async database connections with SQLAlchemy

### Caching Strategy  
- **Redis read-through cache**: 60s TTL for `/meetings` and `/search` endpoints
- **Cache invalidation**: Smart cache clearing on new meeting uploads
- **Hit ratio**: Typical 85%+ cache hit rate for list/search operations

### Performance Results
📊 **API Latency Report**: [View detailed results](docs/latency_report.txt)
- `/meetings` endpoint: **89ms median latency** (target: <150ms) 
- `/search` endpoint: **125ms median latency** (target: <150ms) 
- Concurrent load: 10 connections, 30s duration tests

### Ray Serve Integration
- **Distributed processing**: CPU-optimized summarization service
- **Auto-scaling**: 2 replicas with dynamic batching
- **Service endpoints**:
  - Summarization: `POST /ray-summary` 
  - Health check: `GET /ray-health`
  - Dashboard: http://localhost:8265

### Triton Inference Server
- **GPU-ready inference**: Keyword extraction model (CPU demo included)
- **Model repository**: `triton_models/keyword_extractor/`
- **Test command**: `python scripts/test_triton.py`
- **Inference API**: http://localhost:8003

### Real-time Processing
📈 **Faster-Whisper Performance**: [View benchmark report](docs/realtime_factor_report.txt)
- **Real-time factor**: 0.43 (lower is better)
- **Processing speed**: **2.3× faster than real-time** ✅
- **Scalability**: Consistent performance across 10s-60s audio files

### Testing Performance
```bash
# Run API latency tests
./scripts/load_test.sh

# Test Ray Serve summarization
curl -X POST http://localhost:10001/SummarizationService \
  -H "Content-Type: application/json" \
  -d '{"text": "Your meeting text here"}'

# Test Triton inference
python scripts/test_triton.py

# Measure transcription real-time factor  
python scripts/measure_realtime_factor.py
```

---

## 🎯 Language Samples Demo

Visit `/language-samples` to see the platform process 5 different languages:

![Language Demo Screenshot](docs/language-demo-screenshot.png)

**Demo includes:**
- Real-time processing status
- Language detection accuracy
- Keyword extraction in native languages
- Culturally-aware summarization
- Performance metrics

---

## 📡 API Reference

### Core Endpoints

**Upload & Queue Processing**
```http
POST /analyze-meeting
Content-Type: multipart/form-data

Returns: {"status": "queued", "meeting_id": 123, "job_id": "job_xyz"}
```

**Check Job Status**
```http
GET /job-status/{job_id}

Returns: {"status": "processing|completed|failed", "result": {...}}
```

**Meeting Management**
```http
GET /meetings                    # List all meetings
GET /meetings/{id}              # Get meeting details
DELETE /meetings/{id}           # Delete meeting
GET /search?q=keyword           # Search meetings
```

**System Status**
```http
GET /health                     # API service health
GET /queue-stats               # Queue length and processing count
GET /worker/health             # Worker service health (port 8001)
```

---

## 🛠️ Tech Stack

**Frontend**
- Next.js 14 with App Router
- TypeScript and Tailwind CSS
- Responsive design and real-time updates

**Backend Services**
- FastAPI with async/await
- SQLAlchemy ORM with PostgreSQL
- Redis for job queuing
- Pydantic for data validation

**AI & Processing**
- faster-whisper for transcription (2.3× real-time speed)
- OpenAI GPT for summarization  
- Ray Serve for distributed inference
- Triton for GPU-accelerated models
- Multi-language support (5+ languages)

**Infrastructure**
- Docker & Docker Compose
- Microservices architecture
- Health checks and monitoring
- Horizontal scaling ready

---

## 🔧 Development

**Local Development (with hot reload):**
```bash
# Start database and Redis only
docker compose up db redis -d

# Run API service locally
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Run worker service locally  
python app/worker.py

# Run frontend locally
cd frontend
npm install
npm run dev
```

**Production Deployment:**
```bash
# Build optimized containers
docker compose -f docker-compose.prod.yml up -d

# Scale workers horizontally
docker compose up --scale backend-worker=3
```

---

## 📈 Monitoring & Scaling

**Health Checks**
- API service: `/health`
- Worker service: `:8001/health` 
- Database connectivity validation
- Redis queue monitoring

**Scaling Options**
- Horizontal worker scaling: `docker compose up --scale backend-worker=N`
- Redis cluster for high availability
- PostgreSQL read replicas
- Load balancer for API instances

**Queue Monitoring**
- Queue length tracking
- Processing time metrics
- Failed job retry logic
- Worker health status

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

**Development Setup:**
1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and test locally
4. Submit pull request with clear description

---

## 📜 License

MIT License © 2025 - See [LICENSE](LICENSE) for details.

---

## 🌟 Showcase

This project demonstrates:
- **Full-stack development** with modern frameworks
- **Microservices architecture** and async processing
- **AI integration** with real-world applications
- **DevOps practices** with containerization
- **Production-ready** code with testing and monitoring

⭐ **Star this repo** if you find it useful for your projects or learning!

---

*Built with ❤️ for developers who want to understand modern cloud-native applications.*