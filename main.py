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
        df = pd.read_excel(io.BytesIO(contents), skiprows=1)

        # কলামগুলোর সঠিক নাম খুঁজে বের করা (যাতে ইনডেক্স বা নামের সমস্যায় জিরো না আসে)
        roll_col = df.columns[0]
        name_col = df.columns[1]
        
        # Pre-test এবং Post-test কলামের সঠিক নাম খুঁজে বের করা
        pre_col = next((col for col in df.columns if 'Pre-' in str(col) or 'pre' in str(col).lower()), df.columns[5] if len(df.columns) > 5 else None)
        post_col = next((col for col in df.columns if 'post-' in str(col) or 'post' in str(col).lower()), df.columns[6] if len(df.columns) > 6 else None)

        processed_data = []
        for index, row in df.iterrows():
            r_val = row.get(roll_col, '')
            if pd.isna(r_val) or str(r_val).strip() == '':
                continue
                
            n_val = row.get(name_col, '')
            pre_val = row.get(pre_col, 0) if pre_col else 0
            post_val = row.get(post_col, 0) if post_col else 0

            # যদি কোনো কারণে মান ন্যান (NaN) বা খালি থাকে
            if pd.isna(pre_val): pre_val = 0
            if pd.isna(post_val): post_val = 0

            processed_data.append({
                "name": str(n_val).strip(),
                "roll": str(int(r_val)) if str(r_val).isdigit() else str(r_val).strip(),
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
