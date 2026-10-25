import uuid
from typing import Dict
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

app = FastAPI(title="Mark AutoFill API")

# সিকিউরিটির জন্য CORS সেটিংস (যাতে ব্রাউজার থেকে নিরাপদে ডেটা আদান-প্রদান করা যায়)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # প্রয়োজন অনুযায়ী পরবর্তীতে নির্দিষ্ট ডোমেইন দেওয়া যাবে
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# সাময়িকভাবে ইউজার সেশন ডেটা রাখার জন্য ইন-মেমোরি ক্যাশ ডিকশনারি
# (সিকিউরিটি: প্রতি ইউজারের ডেটা আলাদা রাখতে ইউনিক টোকেন কি হিসেবে ব্যবহার হবে)
sessions_db: Dict[str, dict] = {}


@app.get("/")
def home():
    return {"message": "Mark AutoFill API System is Running Smoothly!"}


@app.post("/upload")
async def upload_excel(file: UploadFile = File(...)):
    # ১. ফাইল ফরম্যাট চেক
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        raise HTTPException(status_code=400, detail="শুধুমাত্র এক্সেল (.xlsx বা .xls) ফাইল আপলোড করুন।")

    try:
        # ২. এক্সেল ফাইলের কন্টেন্ট রিড করা
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # ৩. ডাটা ক্লিন করা ও ফরম্যাট করা
        # ধরে নিচ্ছি এক্সেল ফাইলে Name, Roll, PreTest, PostTest কলামগুলো আছে
        processed_data = []
        for index, row in df.iterrows():
            processed_data.append({
                "name": str(row.get('Name', '')).strip(),
                "roll": str(row.get('Roll', '')).strip(),
                "pre_test": str(row.get('PreTest', 0)).strip(),
                "post_test": str(row.get('PostTest', 0)).strip()
            })

        # ৪. প্রফেশনাল সিকিউরিটির জন্য Cryptographic Unique Token (UUIDv4) জেনারেট
        token = str(uuid.uuid4())

        # ৫. ইউনিক টোকেনের সাথে সেই ইউজার ডেটা সাময়িকভাবে মেমোরিতে সংরক্ষণ
        sessions_db[token] = processed_data

        return {
            "status": "success",
            "message": "ফাইল সফলভাবে প্রসেস করা হয়েছে!",
            "token": token,
            "total_records": len(processed_data)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ফাইল পড়তে সমস্যা হয়েছে: {str(e)}")


@app.get("/get-data/{token}")
def get_user_data(token: str):
    # ইউনিক টোকেন মিলিয়ে নির্দিষ্ট ইউজারের ডেটা রিটার্ন
    if token not in sessions_db:
        raise HTTPException(status_code=404, detail="মেয়াদ উত্তীর্ণ বা ভুল টোকেন!")
    
    return {
        "status": "success",
        "data": sessions_db[token]
    }