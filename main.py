import uuid
from typing import Dict
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

app = FastAPI(title="Mark AutoFill API")

# সিকিউরিটির জন্য CORS সেটিংস
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# সাময়িকভাবে ইউজার সেশন ডেটা রাখার জন্য ইন-মেমোরি ক্যাশ ডিকশনারি
sessions_db: Dict[str, dict] = {}


@app.get("/")
def home():
    return {"message": "PB Tutorials Backend is running live!"}


@app.post("/upload")
async def upload_excel(file: UploadFile = File(...)):
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        raise HTTPException(status_code=400, detail="শুধুমাত্র এক্সেল (.xlsx বা .xls) ফাইল আপলোড করুন।")

    try:
        contents = await file.read()
        # সরাসরি হেডার বাদ দিয়ে ১ নম্বর রো থেকে ডেটা রিড করা (যেখানে রো-১ হলো হেডার)
        df = pd.read_excel(io.BytesIO(contents), skiprows=1)

        processed_data = []
        for index, row in df.iterrows():
            # পজিশনভিত্তিক নিরাপদ ডেটা ফেচিং
            r_val = row.iloc[0] if len(row) > 0 else ''  # 0 নম্বর কলাম = Roll
            n_val = row.iloc[1] if len(row) > 1 else ''  # 1 নম্বর কলাম = Name
            pre_val = row.iloc[5] if len(row) > 5 else 0 # 5 নম্বর কলাম = Pre-Test
            post_val = row.iloc[6] if len(row) > 6 else 0# 6 নম্বর কলাম = Post-Test

            # যদি রোল ফাঁকা থাকে বা হেডার লেখা আবার চলে আসে তবে স্কিপ করবে
            if pd.isna(r_val) or str(r_val).strip() == '' or str(r_val).strip().lower() == 'roll':
                continue

            # ন্যান (NaN) ভ্যালু হ্যান্ডেল করা
            if pd.isna(pre_val): pre_val = 0
            if pd.isna(post_val): post_val = 0

            processed_data.append({
                "name": str(n_val).strip(),
                "roll": str(r_val).strip(),
                "pre_test": str(pre_val).strip(),
                "post_test": str(post_val).strip()
            })

        token = str(uuid.uuid4())
        sessions_db[token] = processed_data

        return {
            "status": "success",
            "message": "ফাইল সফলভাবে প্রসেস করা হয়েছে!",
            "token": token,
            "total_records": len(processed_data),
            "data": processed_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ফাইল পড়তে সমস্যা হয়েছে: {str(e)}")


@app.get("/get-data/{token}")
def get_user_data(token: str):
    if token not in sessions_db:
        raise HTTPException(status_code=404, detail="মেয়াদ উত্তীর্ণ বা ভুল টোকেন!")
    
    return {
        "status": "success",
        "data": sessions_db[token]
    }
