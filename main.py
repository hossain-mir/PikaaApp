import os
import json
import requests
import subprocess
from datetime import datetime

# ==========================================
# আপনার চাবিগুলো ঠিক এখানে বসাবেন
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ELEVENLABS_API_KEY = "sk_786438c7af3ba7ff3fdd19d7d83ba9d8b4f85e7e5d20b401"
ELEVENLABS_VOICE_ID = "vBUZv01xPV9QD0BikcXi"
DATA_DIR = "/storage/emulated/0/My.pikaa.ai"
DATA_FILE = os.path.join(DATA_DIR, "pikaa_database.json")

CURRENT_MODEL = "openai/gpt-oss-20b" 

APP_MAP = {
    "whatsapp": "com.whatsapp",
    "youtube": "com.google.android.youtube",
    "facebook": "com.facebook.katana",
    "instagram": "com.instagram.android",
    "chrome": "com.android.chrome",
    "free fire": "com.dts.freefireth",
    "freefire": "com.dts.freefireth",
    "gmail": "com.google.android.gm",
    "calculator": "com.google.android.calculator",
    "camera": "com.android.camera",
    "photos": "com.google.android.apps.photos",
    "maps": "com.google.android.apps.maps",
    "play store": "com.android.vending",
    "settings": "com.android.settings",
    "chatgpt": "com.openai.chatgpt"
}

def load_database():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            pass
    return {"current_user": "Sir", "language": "en", "profiles": {"Sir": {"chat_history": []}}}

def save_database(db):
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(db, file, ensure_ascii=False, indent=4)
    except Exception:
        pass

db = load_database()
if "profiles" not in db:
    db["profiles"] = {}
if "Sir" not in db["profiles"]:
    db["profiles"]["Sir"] = {"chat_history": []}
save_database(db)

user_data = db["profiles"]["Sir"]

strict_system_prompt = {
    "role": "system",
    "content": "You are Pikaa, a smart personal AI assistant. You were created by Mr. Hossain. The user chatting with you is Mr. Hossain (Sir). You MUST understand and speak in Banglish (Bengali written in English letters). If asked 'tomake k create koreche' or similar, reply 'Apni amake create korechen, Sir! Apni Mr. Hossain.'. Keep answers very natural, friendly, short and ALWAYS in Banglish. Do NOT give english translation explanations."
}

if len(user_data["chat_history"]) > 0 and user_data["chat_history"][0]["role"] == "system":
    user_data["chat_history"][0] = strict_system_prompt
else:
    user_data["chat_history"].insert(0, strict_system_prompt)

def speak(text):
    safe_text = str(text).replace('"', '').replace("'", "").replace('\n', ' ')
    print("🗣️ Pikaa is speaking...")
    
    # ElevenLabs-এ কানেক্ট করার চেষ্টা
    if "EKHANE" not in ELEVENLABS_API_KEY:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": ELEVENLABS_API_KEY
            }
            data = {
                "text": safe_text,
                "model_id": "eleven_turbo_v2", # ফাস্ট মডেল
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            response = requests.post(url, json=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                audio_path = os.path.join(DATA_DIR, "reply.mp3")
                with open(audio_path, 'wb') as f:
                    f.write(response.content)
                subprocess.run(["termux-media-player", "play", audio_path], check=False)
                return
            else:
                print(f"[Voice Error: {response.status_code}]")
        except Exception:
            pass

    # ElevenLabs কাজ না করলে বা ইন্টারনেট না থাকলে সাধারণ Termux ভয়েস
    subprocess.run(["termux-tts-speak", "-r", "0.9", safe_text], check=False)

def listen():
    print("\nListening...")
    try:
        res = subprocess.run(["termux-dialog", "speech"], capture_output=True, text=True, check=False)
        data = json.loads(res.stdout)
        return data.get("text", "").strip()
    except Exception:
        return ""

def open_any_app(command_text):
    clean_name = command_text.replace("open", "").strip().lower()
    for name, pkg in APP_MAP.items():
        if name in clean_name:
            res1 = subprocess.run(["am", "start", "--user", "0", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", "-p", pkg], capture_output=True)
            res2 = subprocess.run(["monkey", "-p", pkg, "1"], capture_output=True)
            if res1.returncode == 0 or res2.returncode == 0:
                return f"Opening {name}."
            return f"Failed to open {name}."
    return f"Sorry, {clean_name} is not in my list."

def get_battery_status():
    try:
        result = subprocess.check_output(['termux-battery-status']).decode('utf-8')
        data = json.loads(result)
        return f"Battery level is {data.get('percentage', 'unknown')} percent."
    except Exception:
        return "Battery info unavailable."

def get_time():
    return f"Current time is {datetime.now().strftime('%I:%M %p')}."

def ask_pikaa_ai(user_input):
    global CURRENT_MODEL
    print("🧠 Pikaa is thinking...")
    
    # 400 Error Fix (ডাবল মেসেজ ডিলিট করবে)
    if len(user_data["chat_history"]) > 1 and user_data["chat_history"][-1]["role"] == "user":
        user_data["chat_history"].pop()
        
    user_data["chat_history"].append({"role": "user", "content": user_input})
    
    if len(user_data["chat_history"]) > 31:
        user_data["chat_history"] = [strict_system_prompt] + user_data["chat_history"][-30:]
        
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }

    # মডেল অটো-ডিটেক্ট
    if not CURRENT_MODEL:
        try:
            res_models = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=10)
            if res_models.status_code == 200:
                models = res_models.json().get("data", [])
                for m in models:
                    if "llama" in m["id"].lower():
                        CURRENT_MODEL = m["id"]
                        break
                if not CURRENT_MODEL and models:
                    CURRENT_MODEL = models[0]["id"]
            else:
                user_data["chat_history"].pop()
                return f"API Key Error: {res_models.status_code}"
        except Exception:
            CURRENT_MODEL = "llama-3.3-70b-versatile" # ব্যাকআপ মডেল

    url = "https://api.groq.com/openai/v1/chat/completions"
    data = {
        "model": CURRENT_MODEL,
        "messages": user_data["chat_history"]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=20)
        if response.status_code == 200:
            ai_reply = response.json()['choices'][0]['message']['content']
            user_data["chat_history"].append({"role": "assistant", "content": ai_reply})
            return ai_reply
        else:
            user_data["chat_history"].pop()
            CURRENT_MODEL = "openai/gpt-oss-20b" 
            return f"API Error ({response.status_code}): Check your key."
    except Exception:
        user_data["chat_history"].pop()
        return "Internet connection error."

print("=======================================")
print("           Pikaa.03_HANIYA             ")
print("=======================================")

speak("System online. Yes sir, amake Mr. Hossain create koreche sudhu apnar jonno.")

while True:
    try:
        user_input = input("\nSir: ").strip().lower()
        
        if user_input in ['exit', 'quit', 'bye']:
            speak("Goodbye Sir.")
            break
            
        if user_input == 'v':
            user_input = listen().lower()
            if not user_input:
                continue
            print(f"You: {user_input}")
            
        if not user_input:
            continue
            
        if "open" in user_input:
            reply = open_any_app(user_input)
        elif "battery" in user_input:
            reply = get_battery_status()
        elif "time" in user_input:
            reply = get_time()
        else:
            reply = ask_pikaa_ai(user_input)
            save_database(db)
            
        print(f"Pikaa: {reply}")
        speak(reply)
        
    except KeyboardInterrupt:
        print("\nExiting...")
        break
    except Exception as e:
        print(f"Error: {e}")
        break
