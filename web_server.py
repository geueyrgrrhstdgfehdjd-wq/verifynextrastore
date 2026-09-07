import requests
import asyncio
import discord
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

# -------------------------------------------------------------
# ตั้งค่าข้อมูล OAuth2 และ บอท (กรุณาเปลี่ยนข้อมูลของคุณตรงนี้)
# -------------------------------------------------------------
CLIENT_ID = "1546543519773098075"
CLIENT_SECRET = "v3Veg3WLvNj6VLPVvXvYagLqjt2wNOnb"
REDIRECT_URI = "http://localhost:8000/callback" # เปลี่ยนเป็น URL จริงเมื่อขึ้น Server
BOT_TOKEN = "MTU0NjU0MzUxOTc3MzA5ODA3NQ.GCNv_0.eqPt2Eq-6Gos0cKbQM4wuQJS40hnq0ncVKz0eM"
GUILD_ID = 1542142656241602651      # ใส่ Server ID (ตัวเลข)
VERIFIED_ROLE_ID = 1546216964198891530 # ใส่ ID ของยศที่จะให้เมื่อยืนยันผ่าน (ตัวเลข)

app = FastAPI()

# ฟังก์ชันสั่งบอทให้ยศเมื่อยืนยันสำเร็จ
async def add_verified_role(user_id: int):
    intents = discord.Intents.default()
    intents.members = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        try:
            guild = client.get_guild(GUILD_ID)
            if guild:
                member = await guild.fetch_member(user_id)
                role = guild.get_role(VERIFIED_ROLE_ID)
                if member and role:
                    await member.add_roles(role, reason="ยืนยันตัวตนผ่านระบบเว็บสำเร็จ")
                    print(f"✅ แจกยศให้ {member.name} เรียบร้อยแล้ว")
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการแจกยศ: {e}")
        finally:
            await client.close()

    await client.start(BOT_TOKEN)

# หน้าแรกสำหรับส่งผู้ใช้ออกไปล็อกอินที่ Discord
@app.get("/login")
def login():
    discord_auth_url = (
        f"https://discord.com/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
    )
    return RedirectResponse(discord_auth_url)

# หน้า Callback รับข้อมูล OAuth2 จาก Discord
@app.get("/callback")
async def callback(code: str):
    # 1. ส่ง Request ไปแลกเปลี่ยน Authorization Code
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    token_res = requests.post('https://discord.com/api/v10/oauth2/token', data=data, headers=headers)
    token_json = token_res.json()
    
    access_token = token_json.get('access_token')
    if not access_token:
        return HTMLResponse("<h1 style='color:red;'>❌ ยืนยันตัวตนไม่สำเร็จ (Invalid Token)</h1>")

    # 2. ดึงข้อมูล User Profile
    user_res = requests.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'})
    user_data = user_res.json()
    user_id = int(user_data['id'])

    # 3. สั่งบอทแจกยศ
    await add_verified_role(user_id)

    # 4. แสดงหน้าจอสวยงามส่งกลับผู้ใช้งาน
    return HTMLResponse(f"""
    <!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ระบบยืนยันตัวตน - Discord</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        body {
            background-color: #0f172a;
            color: #ffffff;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        .card {
            background-color: #1e293b;
            padding: 40px 30px;
            border-radius: 20px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.6);
            text-align: center;
            max-width: 420px;
            width: 100%;
            border: 1px solid #334155;
            position: relative;
        }
        .icon-container {
            width: 80px;
            height: 80px;
            background-color: rgba(34, 197, 94, 0.15);
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0 auto 20px auto;
            border: 2px solid #22c55e;
        }
        .icon {
            font-size: 40px;
        }
        h1 {
            color: #22c55e;
            font-size: 24px;
            margin-bottom: 12px;
            font-weight: 700;
        }
        p {
            color: #94a3b8;
            font-size: 15px;
            line-height: 1.6;
            margin-bottom: 20px;
        }
        .user-badge {
            background-color: #0f172a;
            padding: 10px 16px;
            border-radius: 10px;
            display: inline-block;
            border: 1px solid #334155;
            margin-bottom: 20px;
        }
        .username {
            color: #38bdf8;
            font-weight: bold;
        }
        .info-box {
            background-color: rgba(56, 189, 248, 0.1);
            border-left: 4px solid #38bdf8;
            padding: 12px;
            border-radius: 6px;
            text-align: left;
            font-size: 13px;
            color: #cbd5e1;
            margin-bottom: 25px;
        }
        .footer-note {
            font-size: 12px;
            color: #64748b;
        }
    </style>
</head>
<body>

    <div class="card">
        <div class="icon-container">
            <span class="icon">✅</span>
        </div>
        
        <h1>ยืนยันตัวตนสำเร็จ!</h1>
        
        <p>ยินดีต้อนรับสู่เซิร์ฟเวอร์ ระบบได้ตรวจสอบข้อมูลและมอบยศให้คุณเรียบร้อยแล้ว</p>
        
        <div class="user-badge">
            👤 สมาชิก: <span class="username">@{username}</span>
        </div>

        <div class="info-box">
            📌 <b>หมายเหตุ:</b> ยศของคุณจะแสดงผลใน Discord ภายในไม่กี่วินาที คุณสามารถปิดหน้าต่างนี้ได้ทันที
        </div>

        <p class="footer-note">ขอบคุณที่ทำการยืนยันตัวตนเพื่อความปลอดภัยของเซิร์ฟเวอร์</p>
    </div>

</body>
</html>
