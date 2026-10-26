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
        
        # ১. প্রথমে হেডার ছাড়াই র-ডেটা রিড করা যাতে সঠিক হেডার রো খুঁজে পাওয়া যায়
        df_raw = pd.read_excel(io.BytesIO(contents), header=None)
        
        header_row_idx = None
        for idx, row in df_raw.iterrows():
            row_str = " ".join([str(val) for val in row.values])
            if 'Roll' in row_str and 'Name' in row_str:
                header_row_idx = idx
                break
        
        # যদি হেডার খুঁজে না পাওয়া যায়, তবে ডিফল্টভাবে ১ নম্বর রো ধরব
        if header_row_idx is None:
            header_row_idx = 1

        # ২. সঠিক হেডার ইনডেক্স ব্যবহার করে ডেটাফ্রেম লোড করা
        df = pd.read_excel(io.BytesIO(contents), header=header_row_idx)

        # কলামের নামগুলো পরিষ্কার করে নেওয়া
        df.columns = [str(c).strip() for c in df.columns]

        # কলামগুলো শনাক্ত করা
        roll_col = df.columns[0]
        name_col = df.columns[1]
        
        # Pre-Test এবং Post-Test কলাম খোঁজা
        pre_col = next((col for col in df.columns if 'pre' in col.lower()), df.columns[5] if len(df.columns) > 5 else None)
        post_col = next((col for col in df.columns if 'post' in col.lower()), df.columns[6] if len(df.columns) > 6 else None)

        processed_data = []
        for index, row in df.iterrows():
            r_val = row.get(roll_col, '')
            n_val = row.get(name_col, '')

            # যদি রোল বা নাম খালি থাকে অথবা হেডার নিজেই রো হিসেবে আসে, তবে স্কিপ করব
            if pd.isna(r_val) or str(r_val).strip() == '' or str(r_val).strip().lower() == 'roll':
                continue

            pre_val = row.get(pre_col, 0) if pre_col else 0
            post_val = row.get(post_col, 0) if post_col else 0

            # যদি ন্যান (NaN) হয়
            if pd.isna(pre_val) or str(pre_val).strip() == '': pre_val = 0
            if pd.isna(post_val) or str(post_val).strip() == '': post_val = 0

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
