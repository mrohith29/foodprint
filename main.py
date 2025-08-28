from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import json

from dotenv import load_dotenv

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None


class IngredientOut(BaseModel):
    name: str = Field(..., description="Ingredient name")
    carbon_kg: float = Field(..., description="Estimated carbon emissions in kg CO2e")


class EstimateOut(BaseModel):
    dish: str
    estimated_carbon_kg: float
    ingredients: List[IngredientOut]


class EstimateIn(BaseModel):
    dish: str


MODEL_NAME = "gemini-2.5-flash"


def configure_gemini() -> Optional[object]:
    """Configure Gemini client using API key from .env (GEMINI_API_KEY)."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return None
    genai.configure(api_key=api_key)
    try:
        return genai.GenerativeModel(MODEL_NAME)
    except Exception:
        return None


def build_instruction_for_text(dish: str) -> str:
    return (
        "You are a sustainability assistant. Given a dish name, infer 3-8 likely ingredients "
        "and estimate their carbon footprint in kg CO2e each. Return STRICT JSON with keys: "
        "dish (string), estimated_carbon_kg (number), ingredients (array of {name, carbon_kg}). "
        "Use reasonable, order-of-magnitude values. Do not include any extra commentary.\n\n"
        f"Dish: {dish}"
    )


def build_instruction_for_image() -> str:
    return (
        "You are a vision sustainability assistant. Analyze the image to identify the food dish "
        "or its main ingredients, then produce a JSON object with: dish (string guess), "
        "estimated_carbon_kg (number), ingredients (array of {name, carbon_kg})."
        " Return STRICT JSON only."
    )


def safe_parse_json(text: str) -> Optional[dict]:
    """Attempt to extract and parse JSON from model output."""
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return None
        return None


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = configure_gemini()

"""
POST /estimate
- Accepts a **dish name** in JSON format
    
    Example:
    
    ```json
    { 
    			"dish": "Chicken Biryani"
    }
    ```
    
- The backend should:
    - Use an LLM to infer likely ingredients
    - Estimate the carbon footprint of each ingredient
    - Return a total score with a breakdown
- You can explore this functionality in the 🔍 Search tab of foodprint.reewild.com
"""


@app.post("/estimate", response_model=EstimateOut)
def estimate_text(data: EstimateIn):
    dish = data.dish.strip()
    if not dish:
        raise HTTPException(status_code=400, detail="'dish' must be a non-empty string")

    if model is None:
        raise HTTPException(status_code=500, detail="Gemini client not configured. Ensure GEMINI_API_KEY and google-generativeai are set.")

    instruction = build_instruction_for_text(dish)
    try:
        response = model.generate_content(instruction)
        text = getattr(response, "text", None) or ""
        parsed = safe_parse_json(text) or {"dish": dish, "ingredients": [], "estimated_carbon_kg": 0}
        ingredients = [
            IngredientOut(
                name=str(it.get("name", "Unknown")),
                carbon_kg=float(it.get("carbon_kg", 0.0)),
            )
            for it in (parsed.get("ingredients", []) or [])
            if isinstance(it, dict)
        ]
        total = parsed.get("estimated_carbon_kg")
        total_val = float(total) if (total is not None) else sum(i.carbon_kg for i in ingredients)
        return EstimateOut(dish=str(parsed.get("dish", dish)), estimated_carbon_kg=round(total_val or 0.0, 2), ingredients=ingredients)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Model error: {e}")


"""
`POST /estimate/image`

- Accepts an **image upload** (`multipart/form-data`)
- The backend should:
    - Use a vision model to identify the dish or its ingredients
    - Estimate the carbon score in the same format as above
- You can try this in 📸 Vision tab of foodprint.reewild.com
"""


@app.post("/estimate/image", response_model=EstimateOut)
async def estimate_image(image: UploadFile = File(...)):
    content = await image.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty image upload")

    if model is None:
        raise HTTPException(status_code=500, detail="Gemini client not configured. Ensure GEMINI_API_KEY and google-generativeai are set.")

    instruction = build_instruction_for_image()
    try:
        parts = [
            instruction,
            {"mime_type": image.content_type or "image/jpeg", "data": content},
        ]
        response = model.generate_content(parts)
        text = getattr(response, "text", None) or ""
        parsed = safe_parse_json(text) or {"dish": "Uploaded Dish", "ingredients": [], "estimated_carbon_kg": 0}
        ingredients = [
            IngredientOut(
                name=str(it.get("name", "Unknown")),
                carbon_kg=float(it.get("carbon_kg", 0.0)),
            )
            for it in (parsed.get("ingredients", []) or [])
            if isinstance(it, dict)
        ]
        total = parsed.get("estimated_carbon_kg")
        total_val = float(total) if (total is not None) else sum(i.carbon_kg for i in ingredients)
        dish = str(parsed.get("dish", "Uploaded Dish"))
        return EstimateOut(dish=dish, estimated_carbon_kg=round(total_val or 0.0, 2), ingredients=ingredients)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Model error: {e}")


"""
### Output Format (Example)

```json
{
  "dish": "Chicken Biryani",
  "estimated_carbon_kg": 4.2,
  "ingredients": [
    { "name": "Rice", "carbon_kg": 1.1 },
    { "name": "Chicken", "carbon_kg": 2.5 },
    { "name": "Spices", "carbon_kg": 0.2 },
    { "name": "Oil", "carbon_kg": 0.4 }
  ]
}
```

> You can use mocked values or ask the LLM to infer emissions. No real-world dataset or DB is required.
>
"""