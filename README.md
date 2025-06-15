# genai_supplychain
MSc Computer Science Project, James Simpson

1) Start FastAPI Backend
------------------------

- Navigate to the `FastAPI` directory:
    cd FastAPI
- Install Uvicorn if not already installed:
    pip install uvicorn
- Run the FastAPI server with:
    uvicorn main:app --reload
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