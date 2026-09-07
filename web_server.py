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
        <title>ยืนยันตัวตนสำเร็จ</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #ffffff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .card {{ background-color: #1e293b; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; max-width: 400px; border: 1px solid #334155; }}
            .icon {{ font-size: 50px; margin-bottom: 10px; }}
            h1 {{ color: #22c55e; margin-bottom: 10px; font-size: 24px; }}
            p {{ color: #94a3b8; line-height: 1.5; }}
            .user {{ color: #38bdf8; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">✅</div>
            <h1>ยืนยันตัวตนสำเร็จ!</h1>
            <p>ยินดีต้อนรับคุณ <span class="user">@{user_data['username']}</span><br>ระบบได้ทำการยศเข้าบัญชีของคุณใน Discord เรียบร้อยแล้ว</p>
            <p style="font-size: 12px; margin-top: 20px;">สามารถปิดหน้านี้และกลับไปใช้งาน Discord ได้เลยครับ</p>
        </div>
    </body>
    </html>
    """)
