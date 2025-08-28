import os
import json
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Foodprint Estimator", page_icon="🥗", layout="centered")

st.title("Foodprint Estimator")
st.caption("Estimate the carbon footprint of dishes via text or image. Powered by Gemini 2.5 Flash.")

health = None
try:
    r = requests.get(f"{BACKEND_URL}/health", timeout=5)
    health = r.json()
except Exception:
    pass

if health:
    st.success(f"Backend: {health.get('status')} (model: {health.get('model')})")
else:
    st.warning("Backend not reachable. Start FastAPI at http://localhost:8000")

search_tab, vision_tab = st.tabs(["🔍 Search", "📸 Vision"])

with search_tab:
    st.subheader("Type a dish name")
    dish = st.text_input("Dish", placeholder="e.g., Chicken Biryani")
    if st.button("Estimate from Text", type="primary"):
        if not dish.strip():
            st.error("Please enter a dish name.")
        else:
            with st.spinner("Estimating..."):
                try:
                    payload = {"dish": dish.strip()}
                    res = requests.post(f"{BACKEND_URL}/estimate", json=payload, timeout=30)
                    res.raise_for_status()
                    data = res.json()
                    st.success(f"Estimated carbon: {data.get('estimated_carbon_kg')} kg CO2e")
                    st.json(data)
                    # Pretty display
                    ingredients = data.get("ingredients", [])
                    if ingredients:
                        st.markdown("**Ingredients breakdown**")
                        for ing in ingredients:
                            st.write(f"- {ing.get('name')}: {ing.get('carbon_kg')} kg")
                except Exception as e:
                    st.error(f"Error: {e}")

with vision_tab:
    st.subheader("Upload a dish image")
    uploaded = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])
    if st.button("Estimate from Image", type="primary"):
        if not uploaded:
            st.error("Please upload an image.")
        else:
            with st.spinner("Estimating..."):
                try:
                    files = {"image": (uploaded.name, uploaded.getvalue(), uploaded.type or "image/jpeg")}
                    res = requests.post(f"{BACKEND_URL}/estimate/image", files=files, timeout=60)
                    res.raise_for_status()
                    data = res.json()
                    st.success(f"Estimated carbon: {data.get('estimated_carbon_kg')} kg CO2e")
                    st.json(data)
                    ingredients = data.get("ingredients", [])
                    if ingredients:
                        st.markdown("**Ingredients breakdown**")
                        for ing in ingredients:
                            st.write(f"- {ing.get('name')}: {ing.get('carbon_kg')} kg")
                except Exception as e:
                    st.error(f"Error: {e}")
