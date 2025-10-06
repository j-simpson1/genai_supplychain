# GenAI Supply Chain Platform - System Manual

**MSc Computer Science Project by James Simpson**

## System Overview

The GenAI Supply Chain Platform is a comprehensive AI-powered solution for automotive industry supply chain analysis and research. It combines multiple specialized AI agents built on LangGraph with a modern React frontend and FastAPI backend.

### Key Technologies
- **Backend**: FastAPI (Python 3.11), LangGraph, LangChain
- **Frontend**: React 19, TypeScript, Material-UI, Vite
- **AI/ML**: OpenAI GPT models, LangSmith observability
- **Data**: Pandas, SQLite, PostgreSQL, TecDoc API integration
- **Deployment**: Docker, Docker Compose

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React Frontend│    │   FastAPI Backend│    │  AI Agent Layer │
│                 │    │                  │    │                 │
│ - TypeScript    │◄──►│ - Python 3.11    │◄──►│ - LangGraph     │
│ - Material-UI   │    │ - FastAPI        │    │ - LangChain     │
│ - Vite          │    │ - Uvicorn        │    │ - OpenAI        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Interface│    │   Data Layer     │    │  External APIs  │
│                 │    │                  │    │                 │
│ - Port 5173     │    │ - CSV Processing │    │ - TecDoc API    │
│ - Dev Server    │    │                  │    │ - Tavily Search │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Code Organization

### Directory Structure

```
genai_supplychain/
├── FastAPI/                          # Backend API server
│   ├── core/                         # AI agents and core logic
│   ├── routes/                       # API route definitions
│   ├── automotive_simulation/        # Simulation
│   ├── data/                         # Data handling and validation
│   ├── document_builders/            # Document creation utilities
│   ├── reports_and_graphs/           # Generated reports and visualizations
│   ├── utils/                        # Backend utilities
│   └── main.py                       # FastAPI application entry point
├── frontend/                         # React TypeScript frontend
│   ├── src/                          # Source code (components, pages, sections, layouts)
│   ├── package.json                  # Node.js dependencies
│   └── vite.config.ts                # Vite build configuration
├── output/                           # Generated outputs and exports
├── test-data/                        # Test datasets
├── requirements.txt                  # Python dependencies (pip)
├── environment.yml                   # Conda environment specification
├── Dockerfile                        # Container image definition
├── docker-compose.yml                # Docker service configuration
├── .env.example                      # Environment variables template
└── README.md                         # Quick start guide
```

### Core Components

#### AI Agents (`FastAPI/core/`)
- **Research Agent** (`research_agent.py`): Performs web research and data analysis
- **Simulation Agent** (`simulation_agent.py`): Runs economic and supply chain simulations
- **Data Agent** (`data_agent.py`): Processes and analyzes uploaded data files
- **Document Generator** (`document_generator.py`): Creates reports and documentation
- **Deep Research Agent** (`deep_research_agent.py`): Advanced research capabilities
- **Code Editor Agent** (`code_editor_agent.py`): Code analysis and modification

#### Frontend Structure (`frontend/src/`)
- **Components**: Reusable UI elements built with Material-UI
- **Pages**: Top-level page components with routing
- **Sections**: Modular page sections
- **Layouts**: Application layout templates

## Development Environment Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git
- Docker (optional)

### Method 1: Conda Environment (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd genai_supplychain

# Create conda environment
conda env create -f environment.yml

# Activate environment
conda activate genai_supplychain2

# Install frontend dependencies
cd frontend
npm install
cd ..

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Method 2: Manual Setup

```bash
# Clone the repository
git clone <repository-url>
cd genai_supplychain

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Required API Keys
Configure these in your `.env` file:
- `OPENAI_API_KEY`: OpenAI API access
- `LANGCHAIN_API_KEY`: LangSmith observability
- `TAVILY_API_KEY`: Web search capabilities

## Build & Deployment

### Development Mode

**Terminal 1 - Backend:**
```bash
conda activate genai_supplychain2
python -m uvicorn FastAPI.main:app --reload
```
- Backend available at: http://127.0.0.1:8000
- API docs at: http://127.0.0.1:8000/docs

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```
- Frontend available at: http://localhost:5173

### Production Build

**Frontend Build:**
```bash
cd frontend
npm run build
```
Build output: `frontend/dist/`

**Backend Production:**
```bash
python -m uvicorn FastAPI.main:app --host 0.0.0.0 --port 8000
```

### Docker Deployment

```bash
# Build and start containers
docker compose up -d

# View logs
docker compose logs -f

# Stop containers
docker compose down

# Rebuild and restart
docker compose up -d --build
```
- Containerized service: http://localhost:8001

### Build Commands Reference

| Component | Command | Purpose |
|-----------|---------|---------|
| Frontend Dev | `npm run dev` | Start development server |
| Frontend Build | `npm run build` | Create production build |
| Frontend Lint | `npm run lint` | Run ESLint |
| Backend Dev | `uvicorn FastAPI.main:app --reload` | Start development server |
| Full Stack | `docker compose up` | Start all services |

## API Documentation

### Base URL
- Development: `http://127.0.0.1:8000`
- Docker: `http://localhost:8001`

### Interactive Documentation
- Swagger UI: `/docs`
- ReDoc: `/redoc`

### Key Endpoints

#### Automotive Data Management
- `GET /manufacturers` - Get automotive manufacturers from TecDoc API
- `GET /manufacturers/models?id={id}` - Get vehicle models for a manufacturer
- `GET /manufacturers/models/engine_type?manufacturerId={id}&modelSeriesId={id}` - Get engine types
- `GET /manufacturers/models/engine_type/category_v3?vehicleId={id}&manufacturerId={id}` - Get parts categories
- `GET /manufacturers/models/engine_type/category_v3/article_list?manufacturerId={id}&vehicleId={id}&productGroupId={id}` - Get article list
- `GET /countries` - Get available countries from TecDoc API

#### Data Processing & Analysis
- `POST /find_countries` - Extract unique countries from uploaded CSV data files
- `POST /run_report_generator` - Main report generation endpoint

#### Main Simulation Workflow
The `/run_report_generator` endpoint handles:
- Vehicle details and simulation parameters
- Multiple tariff rate scenarios (3 rates + VAT)
- Manufacturing location and tariff shock country configuration
- CSV file uploads (parts data, articles data, optional tariff data)
- AI-powered analysis and report generation

## Configuration Management

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API access | Yes |
| `LANGCHAIN_API_KEY` | LangSmith observability | Optional |
| `TAVILY_API_KEY` | Web search API | Optional |
| `ENVIRONMENT` | Deployment environment | No |
| `DEBUG` | Debug mode flag | No |

### Configuration Files
- `.env`: Environment variables (not committed)
- `.env.example`: Template for environment variables
- `environment.yml`: Conda environment specification
- `requirements.txt`: Python dependencies
- `frontend/package.json`: Node.js dependencies

## Development Workflow

### Code Style
- **Python**: Follow PEP 8 standards
- **TypeScript**: ESLint configuration in `frontend/`
- **React**: Functional components with hooks

### Adding New AI Agents
1. Create agent file in `FastAPI/core/`
2. Implement LangGraph workflow
3. Add prompts to `prompts.py`
4. Create API endpoint in `routes/api.py`
5. Add frontend integration

### Adding New Frontend Components
1. Create component in `frontend/src/components/`
2. Follow Material-UI patterns
3. Add TypeScript types
4. Integrate with existing layouts

## Troubleshooting

### Common Issues

#### Environment Setup
- **Conda conflicts**: Remove existing environment first
  ```bash
  conda env remove -n genai_supplychain2
  conda env create -f environment.yml
  ```

#### API Issues
- **CORS errors**: Ensure frontend origin is in `FastAPI/main.py`
- **404 errors**: Check FastAPI routes in `routes/api.py`
- **Import errors**: Verify PYTHONPATH includes project root

#### Docker Issues
- **Port conflicts**: Check if ports 8000/8001/5173 are available
- **Build failures**: Clear Docker cache with `docker system prune`

#### Frontend Issues
- **Module not found**: Run `npm install` in frontend directory
- **TypeScript errors**: Check `frontend/src/vite-env.d.ts`

### Logging
- **Backend**: Logs to console (uvicorn output)
- **Frontend**: Browser console for client-side issues
- **Docker**: `docker compose logs -f`

### Performance
- **Memory usage**: Monitor Python processes during AI agent execution
- **Response times**: Check API response times in browser dev tools

## Maintenance

### Regular Updates
- Update Python dependencies: `pip install -r requirements.txt --upgrade`
- Update Node.js dependencies: `npm update`
- Update Docker images: `docker compose pull`

### Backup Procedures
- Generated reports: Backup `reports_and_graphs/` directory
- Configuration: Version control `.env.example` updates

### Monitoring
- API health checks via `/docs` endpoint
- Frontend availability at configured port
- Docker container status: `docker compose ps`

### Security
- Rotate API keys regularly
- Keep dependencies updated
- Review generated reports for sensitive data
- Ensure `.env` files are not committed

---

**Last Updated**: September 2025
**Version**: 1.0
**Maintainer**: James Simpson