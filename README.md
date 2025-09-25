# genai_supplychain
MSc Computer Science Project, James Simpson

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
```

## Environment Variables
Copy the example environment file and add your API keys:
```bash
cp .env.example .env
# Edit .env with your actual API keys
```

## Docker Services

| Service   | Port | Purpose                   | Credentials                            |
|-----------|------|---------------------------|----------------------------------------|
| postgres  | 5432 | PostgreSQL database       | `devuser` / `devpass` / `devdb`       |
| pgadmin   | 5050 | Browser-based DB explorer | `admin@example.com` / `adminpass`     |


1) Start FastAPI Backend
------------------------

- Run the FastAPI server with:
    python -m uvicorn FastAPI.main:app --reload
  The API will be available at: http://127.0.0.1:8000  
  Swagger UI: http://127.0.0.1:8000/docs


2) Start React Frontend
------------------------

- Navigate to the `frontend` directory:
    cd frontend
- Install dependencies:
    npm install
- Start the development server:
    npm run dev
  The app will run at: http://localhost:5173

3) Start Docker
------------------------
- Start Docker containers:
    docker compose up -d

- View logs:
    docker compose logs -f

- Stop containers:
    docker compose down

- Rebuild and start:
    docker compose up -d --build

  The FastAPI service will be available at: http://localhost:8001


4) Launch Streamlit Dashboard
-----------------------------

- Install Streamlit (if not already installed):
    pip install streamlit pandas

- Run the Streamlit app:
    streamlit run FastAPI/dashboard/dashboard.py

- View in Browser:  
   After launching, Streamlit will print a local URL in the terminal.  
   Open it in your browser to interact with the dashboard.

Note: Streamlit must be run using `streamlit run ...` instead of `python dashboard.py` to enable full interactive 
functionality.