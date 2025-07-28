# genai_supplychain
MSc Computer Science Project, James Simpson

## Docker Services

| Service   | Port | Purpose                   | Credentials                            |
|-----------|------|---------------------------|----------------------------------------|
| postgres  | 5432 | PostgreSQL database       | `devuser` / `devpass` / `devdb`       |
| pgadmin   | 5050 | Browser-based DB explorer | `admin@example.com` / `adminpass`     |


1) Start FastAPI Backend
------------------------

- Install Uvicorn if not already installed:
    pip install uvicorn
- Run the FastAPI server with:
    uvicorn FastAPI.main:app --reload
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
- Start Docker containers
    docker compose up -d

  pgAdmin http://localhost:5050
  Login: admin@example.com / adminpass


4) Launch Streamlit Dashboard
-----------------------------

- Install Streamlit (if not already installed):
    pip install streamlit pandas

- Run the Streamlit app:
    streamlit run FastAPI/core/dashboard.py

- View in Browser:  
   After launching, Streamlit will print a local URL in the terminal.  
   Open it in your browser to interact with the dashboard.

Note: Streamlit must be run using `streamlit run ...` instead of `python dashboard.py` to enable full interactive 
functionality.