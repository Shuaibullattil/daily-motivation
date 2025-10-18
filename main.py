from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json, os, random, datetime, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

# --- LOAD ENVIRONMENT VARIABLES ---
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, encoding='utf-8')

# --- CONFIGURATION ---
JSON_FILE = os.getenv("JSON_FILE", "profile.json")
EMAIL = os.getenv("EMAIL")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

tones = ["inspirational", "energetic", "calm", "reflective", "bold"]

# Configure Gemini API key
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini model
model = genai.GenerativeModel("gemini-2.0-flash")

# --- FASTAPI INIT ---
app = FastAPI(title="Daily Motivation API")

# --- Pydantic Models ---
class About(BaseModel):
    background: str
    dreams: str
    challenges: str
    values: str

class UserData(BaseModel):
    name: str
    role: str
    about: About

class UpdateData(BaseModel):
    role: str | None = None
    about: About | None = None

# --- Helper Functions ---
def read_data():
    if not os.path.exists(JSON_FILE):
        with open(JSON_FILE, "w") as f:
            json.dump({}, f)
    with open(JSON_FILE, "r") as f:
        return json.load(f)

def write_data(data):
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=4)

def send_email(subject, body, to_email):
    msg = MIMEMultipart()
    msg["From"] = EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    # msg.attach(MIMEText(body, "plain"))
    # HTML template for email
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height:1.6; color:#333;">
            <p>{body.replace('\n', '<br>')}</p>
            <p style="margin-top:20px; font-weight:bold;">- Your Daily Motivation App</p>
        </body>
    </html>
    """

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)

def generate_motivation(about: dict) -> str:
    tone = random.choice(tones)
    today = datetime.date.today().strftime("%B %d, %Y")
    prompt = f"""
    Today is {today}.
    Write a {tone} and heartfelt good morning motivational paragraph for Shuaib, 
    a Final Year B.Tech student at CUSAT. 
    Background: {about.get('background')}
    Dreams: {about.get('dreams')}
    Challenges: {about.get('challenges')}
    Values: {about.get('values')}
    
    Write as if you're someone who has seen his struggles and growth — 
    make it real, emotional, and personal. Avoid sounding robotic or generic.
    Output only a single short paragraph (no bullet points, no greetings).
    """

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.95,
                max_output_tokens=250,
            ),
        )
        if not response or not response.text:
            return "You’ve already proved that effort beats everything. Keep pushing forward — your story is just getting started."
        return response.text.strip()
    except Exception as e:
        print("Error from Gemini:", e)
        return "You’ve already proved that effort beats everything. Keep pushing forward — your story is just getting started."

# --- API Endpoints ---
@app.post("/create_user")
def create_user(user: UserData):
    data = {"user": user.dict()}
    write_data(data)
    return {"message": "User data saved successfully", "data": user.dict()}

@app.get("/get_user")
def get_user():
    data = read_data()
    if "user" not in data:
        raise HTTPException(status_code=404, detail="User not found")
    return {"data": data["user"]}

@app.put("/update_user")
def update_user(update: UpdateData):
    data = read_data()
    if "user" not in data:
        raise HTTPException(status_code=404, detail="User not found")
    if update.role:
        data["user"]["role"] = update.role
    if update.about:
        data["user"]["about"] = update.about.dict()
    write_data(data)
    return {"message": "User data updated successfully", "data": data["user"]}

@app.get("/motivation")
def motivation():
    data = read_data()
    if "user" not in data:
        raise HTTPException(status_code=404, detail="User not found")
    about = data["user"].get("about", {})
    if not about:
        raise HTTPException(status_code=400, detail="No about section found")

    message = generate_motivation(about)
    message = message.replace("**", "") 
    send_email(subject="Your Daily Motivation", body=message, to_email="shuaibkaloor123@gmail.com")
    return {"motivation": message, "email_sent_to": "shuaibkaloor123@gmail.com"}
