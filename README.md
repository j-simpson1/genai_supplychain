# GenAI Supply Chain Platform
MSc Computer Science Project, James Simpson

A comprehensive platform for AI-powered supply chain analysis and automotive industry research, featuring LangGraph-based agents for data analysis, document generation, and finding tariff news.

## Key Features

- **Multi-Agent LangGraph System**: Specialized agents for research, data analysis, simulation, and document generation
- **Automotive Industry Integration**: TecDoc API integration for manufacturers, models, and parts data
- **Interactive React Frontend**: Modern UI built with React, TypeScript, and Material-UI
- **FastAPI Backend**: High-performance API with comprehensive automotive supply chain endpoints
- **Document Generation**: Automated report generation with charts and analysis
- **Market Simulation**: Economic modeling for supply chain scenarios and tariff analysis

## Project Structure

```
├── FastAPI/                    # Backend API server
│   ├── core/                   # Core agents and AI logic
│   │   ├── document_generator.py    # Document generation agent
│   │   ├── research_agent.py        # Research and analysis agent
│   │   ├── simulation_agent.py      # Market simulation agent
│   │   ├── data_agent.py            # Data processing agent
│   │   └── database_agent_react.py  # Database interaction agent
│   ├── automotive_simulation/  # Market simulation models
│   ├── routes/                # API route definitions
│   ├── data/                  # Data handling and validation
│   └── main.py               # FastAPI application entry point
├── frontend/                  # React TypeScript frontend
│   └── src/                  # Frontend source code
├── charts/                   # Generated charts and visualizations
├── exports/                  # Generated reports and exports
└── tmp_uploads/             # Temporary file uploads
```

## Setup Environment

### Option 1: Conda Environment (Recommended)
```bash
# Create conda environment from environment.yml
conda env create -f environment.yml

# If you get "prefix already exists" error, remove the existing environment first:
# conda env remove -n genai_supplychain2
# conda env create -f environment.yml

# Activate the environment
conda activate genai_supplychain2

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### Option 2: Manual Setup
If you prefer not to use conda, install dependencies manually:
```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

## Environment Variables
Copy the example environment file and add your API keys:
```bash
cp .env.example .env
# Edit .env with your actual API keys (OpenAI, LangSmith, etc.)
```

## Running the Application

### 1) Start FastAPI Backend
```bash
python -m uvicorn FastAPI.main:app --reload
```
- API available at: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs

### 2) Start React Frontend
```bash
cd frontend
npm run dev
```
- Application available at: http://localhost:5173

### 3) Docker Deployment
```bash
# Start containerized service
docker compose up -d

# View logs
docker compose logs -f

# Stop containers
docker compose down

# Rebuild and start
docker compose up -d --build
```
- Containerized FastAPI service: http://localhost:8001

## API Endpoints

The FastAPI backend provides comprehensive endpoints for:

- **Automotive Data**: Manufacturers, models, engine types, and parts catalogs
- **AI Agents**: Document generation, research, and data analysis
- **File Management**: CSV upload, validation, and processing

Access the interactive API documentation at `/docs` when running the server.

## Technology Stack

**Backend:**
- FastAPI with Python
- LangGraph for multi-agent workflows
- LangChain for AI/LLM integration
- Pandas for data processing
- TecDoc API for automotive data

**Frontend:**
- React 19 with TypeScript
- Material-UI (MUI) components
- Vite build system
- Tailwind CSS for styling

**AI/ML:**
- OpenAI GPT models
- LangSmith for observability
- Custom prompt engineering
- Multi-agent coordination with LangGraph