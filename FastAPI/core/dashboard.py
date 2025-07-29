import streamlit as st
import pandas as pd
import os

# --- File paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
articles_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data", "RAV4_brake_articles_data.csv")
parts_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data", "RAV4_brake_parts_data.csv")

# --- Load CSVs ---
@st.cache_data
def load_csv(file_path):
    return pd.read_csv(file_path)

st.title("Toyota RAV4 Brake System Data")

# --- Parts Data ---
st.header("Brake Parts Data")
parts_df = load_csv(parts_path)
st.dataframe(parts_df, use_container_width=True)

# --- Articles Data ---
st.header("Brake Articles Data")
articles_df = load_csv(articles_path)
st.dataframe(articles_df, use_container_width=True)
