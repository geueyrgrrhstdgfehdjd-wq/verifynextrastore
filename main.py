import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands, ui

ticket_counters = {
    "inquire": 0,
    "claim": 0,
    "getkey": 0
}

welcome_config = {}
leave_config = {}

# -------------------------------------------------------------
# 1. ตั้งค่า Intents
# -------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------------------------------------------
# 2. ระบบ ปุ่มกดรับยศ + ปุ่มยืนยันตัวตนผ่านเว็บ
# -------------------------------------------------------------
class RoleButtonView(ui.View):
    def __init__(self, role_id: int, emoji: str = None):
        super().__init__(timeout=None)
        custom_id = f"button_role_toggle:{role_id}"
        
        button = ui.Button(
            label="กดเพื่อรับ / ถอนยศ",
            style=discord.ButtonStyle.success,
            custom_id=custom_id,
            emoji=emoji if emoji else None
        )
        button.callback = self.button_callback
        self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        role_id = int(custom_id.split(":")[1])
        
        guild = interaction.guild
        role = guild.get_role(role_id)

        if not role:
            await interaction.response.send_message("❌ ไม่พบยศนี้ในเซิร์ฟเวอร์", ephemeral=True)
            return

        user = interaction.user
        if role in user.roles:
            try:
                await user.remove_roles(role, reason="ถอนยศผ่านระบบปุ่มกด")
                await interaction.response.send_message(f"➖ ถอนยศ **{role.name}** เรียบร้อยแล้ว!", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ ไม่สามารถถอนยศได้: {e}", ephemeral=True)
        else:
            try:
                await user.add_roles(role, reason="รับยศผ่านระบบปุ่มกด")
                await interaction.response.send_message(f"➕ ได้รับยศ **{role.name}** เรียบร้อยแล้ว!", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ ไม่สามารถเพิ่มยศได้: {e}", ephemeral=True)

# ปุ่มกดเปิดเว็บยืนยันตัวตน
class WebVerifyView(ui.View):
    def __init__(self, web_url: str):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="🌐 คลิกเพื่อยืนยันตัวตนผ่านเว็บ", url=web_url, style=discord.ButtonStyle.link))

# -------------------------------------------------------------
# 3. ระบบ Ticket
# -------------------------------------------------------------
class CloseTicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="ปิดและลบห้อง", style=discord.ButtonStyle.danger, custom_id="ticket_close_channel")
    async def close_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("กำลังลบห้องนี้ใน 3 วินาที...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

async def create_ticket_channel(interaction: discord.Interaction, ticket_type: str, type_title: str, room_prefix: str, category_name: str):
    guild = interaction.guild
    user = interaction.user

    if not guild.me.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ บอทขาดสิทธิ์ `Manage Channels`", ephemeral=True)
        return

    ticket_counters[ticket_type] += 1
    count_str = f"{ticket_counters[ticket_type]:02d}"
    channel_name = f"{room_prefix}-{count_str}"

    category = None
    for cat in guild.categories:
        if cat.name.strip().lower() == category_name.strip().lower():
            category = cat
            break

    if category is None:
        try:
            category = await guild.create_category(name=category_name, reason="สร้างหมวดหมู่สำหรับระบบ Ticket")
        except Exception as e:
            await interaction.response.send_message(f"❌ ไม่สามารถสร้างหมวดหมู่ได้: {e}", ephemeral=True)
            return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
    }

    for role in guild.roles:
        if role.permissions.administrator:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)

    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"สร้างห้อง Ticket โดย {user.name}"
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ ไม่สามารถสร้างห้องได้: {e}", ephemeral=True)
        return

    embed = discord.Embed(
        title="NEXTRA STORE",
        description=f"นี่คือ{type_title}ของคุณ {user.mention}\nทีมงานจะเข้ามาตอบกลับโดยเร็วที่สุดครับ",
        color=discord.Color.from_rgb(0, 150, 255)
    )
    embed.set_footer(text="NEXTRA STORE - กดปุ่มด้านล่างเมื่อต้องการปิดห้องนี้")

    await channel.send(content=f"{user.mention}", embed=embed, view=CloseTicketView())
    await interaction.response.send_message(f"✅ สร้างห้องของคุณเรียบร้อยแล้ว: {channel.mention}", ephemeral=True)

class TicketSelect(ui.Select):
    def __init__(self, emoji_inquire=None, emoji_claim=None, emoji_getkey=None):
        options = [
            discord.SelectOption(label="สอบถาม", value="inquire", description="ติดต่อสอบถามข้อมูลกับแอดมิน", emoji=emoji_inquire if emoji_inquire else None),
            discord.SelectOption(label="เคลมคีย์", value="claim", description="แจ้งปัญหาหรือขอเคลมคีย์สินค้า", emoji=emoji_claim if emoji_claim else None),
            discord.SelectOption(label="รับคีย์", value="getkey", description="รับคีย์สินค้าหลังจากสั่งซื้อ", emoji=emoji_getkey if emoji_getkey else None),
        ]
        super().__init__(placeholder="เลือกหัวข้อที่ต้องการติดต่อ...", min_values=1, max_values=1, custom_id="ticket_select_menu_dynamic", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "inquire":
            await create_ticket_channel(interaction, "inquire", "ห้องสอบถามแอดมิน", "สอบถาม", "สอบถาม")
        elif selected == "claim":
            await create_ticket_channel(interaction, "claim", "ห้องเคลมคีย์", "claim", "เคลมคีย์")
        elif selected == "getkey":
            await create_ticket_channel(interaction, "getkey", "ห้องรับคีย์", "รับคีย์", "รับคีย์")

class TicketSelectView(ui.View):
    def __init__(self, emoji_inquire=None, emoji_claim=None, emoji_getkey=None):
        super().__init__(timeout=None)
        self.add_item(TicketSelect(emoji_inquire, emoji_claim, emoji_getkey))

# -------------------------------------------------------------
# 4. คำสั่ง Slash Commands
# -------------------------------------------------------------

# --- คำสั่ง /ยืนยันตัวตน (ปุ่มลิงก์เปิดเข้าเว็บ) ---
@bot.tree.command(name="ยืนยันตัวตน", description="สร้างการ์ดปุ่มลิงก์เปิดเว็บยืนยันตัวตนเพื่อรับยศ")
@app_commands.describe(
    web_url="URL หน้าเว็บของคุณ (เช่น http://localhost:8000/login หรือ https://yourdomain.com/login)",
    message="ข้อความอธิบายการยืนยันตัวตน"
)
@app_commands.checks.has_permissions(administrator=True)
async def verify_web_setup(interaction: discord.Interaction, web_url: str, message: str):
    embed = discord.Embed(
        title="🔐 ระบบยืนยันตัวตนผ่านเว็บ",
        description=f"{message}\n\n👉 กดปุ่มด้านล่างเพื่อเข้าสู่ระบบยืนยันตัวตนในเว็บและรับยศอัตโนมัติ",
        color=discord.Color.blue()
    )
    view = WebVerifyView(web_url)
    await interaction.response.send_message("สร้างโพสต์ปุ่มลิงก์ยืนยันตัวตนเรียบร้อย!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=view)


@bot.tree.command(name="ticket", description="สร้างการ์ดระบบ Ticket สำหรับ NEXTRA STORE")
@app_commands.describe(
    message="ข้อความที่จะให้แสดงบนการ์ด",
    image_url="ลิงก์รูปภาพ (ใส่หรือไม่ใส่ก็ได้)",
    emoji_inquire="อิโมจิหัวข้อสอบถาม",
    emoji_claim="อิโมจิหัวข้อเคลมคีย์",
    emoji_getkey="อิโมจิหัวข้อรับคีย์"
)
@app_commands.checks.has_permissions(administrator=True)
async def ticket_setup(interaction: discord.Interaction, message: str, image_url: str = None, emoji_inquire: str = None, emoji_claim: str = None, emoji_getkey: str = None):
    embed = discord.Embed(title="NEXTRA STORE", description=message, color=discord.Color.from_rgb(0, 150, 255))
    if image_url:
        embed.set_image(url=image_url)
    embed.set_footer(text="NEXTRA STORE - เลือกหัวข้อที่ต้องการติดต่อจากเมนูด้านล่างได้เลยครับ")

    view = TicketSelectView(emoji_inquire, emoji_claim, emoji_getkey)
    await interaction.response.send_message("สร้างการ์ด Ticket เรียบร้อยแล้ว", ephemeral=True)
    await interaction.channel.send(embed=embed, view=view)


@bot.tree.command(name="รับยศ", description="สร้างโพสต์ปุ่มกดเพื่อรับยศ")
@app_commands.describe(
    role="เลือดยศที่ต้องการแจกให้ผู้ใช้งาน",
    message="ข้อความอธิบายเกี่ยวกับการกดรับยศ",
    emoji="ใส่อิโมจิหน้าปุ่มกด (ใส่หรือไม่ใส่ก็ได้)"
)
@app_commands.checks.has_permissions(administrator=True)
async def role_button_setup(interaction: discord.Interaction, role: discord.Role, message: str, emoji: str = None):
    embed = discord.Embed(
        title="✨ ระบบรับยศอัตโนมัติ",
        description=f"{message}\n\n👉 กดปุ่มด้านล่างเพื่อรับยศ {role.mention} (กดอีกครั้งเพื่อถอนยศ)",
        color=discord.Color.green()
    )
    view = RoleButtonView(role.id, emoji)
    await interaction.response.send_message("สร้างโพสต์ปุ่มกดรับยศเรียบร้อยแล้ว!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=view)


@bot.tree.command(name="คนเข้า", description="ตั้งค่าระบบต้อนรับคนเข้าดิสคอร์ด")
@app_commands.describe(channel="เลือกห้อง", message="ข้อความ", image_url="ลิงก์รูปภาพ")
@app_commands.checks.has_permissions(administrator=True)
async def welcome_setup(interaction: discord.Interaction, channel: discord.TextChannel, message: str, image_url: str = None):
    welcome_config[interaction.guild_id] = {"channel_id": channel.id, "message": message, "image_url": image_url}
    await interaction.response.send_message(f"✅ ตั้งค่าระบบคนเข้าสำเร็จที่ห้อง {channel.mention}", ephemeral=True)


@bot.tree.command(name="คนออก", description="ตั้งค่าระบบแจ้งเตือนคนออกจากดิสคอร์ด")
@app_commands.describe(channel="เลือกห้อง", message="ข้อความ", image_url="ลิงก์รูปภาพ")
@app_commands.checks.has_permissions(administrator=True)
async def leave_setup(interaction: discord.Interaction, channel: discord.TextChannel, message: str, image_url: str = None):
    leave_config[interaction.guild_id] = {"channel_id": channel.id, "message": message, "image_url": image_url}
    await interaction.response.send_message(f"✅ ตั้งค่าระบบคนออกสำเร็จที่ห้อง {channel.mention}", ephemeral=True)


# -------------------------------------------------------------
# 5. Events
# -------------------------------------------------------------
@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    if guild.id in welcome_config:
        config = welcome_config[guild.id]
        channel = guild.get_channel(config["channel_id"])
        if channel:
            embed = discord.Embed(
                title="👋 ยินดีต้อนรับสมาชิกใหม่!",
                description=f"{config['message']}\n\n👤 **สมาชิก:** {member.mention}\n📊 **สมาชิกทั้งหมด:** {guild.member_count} คน",
                color=discord.Color.blue()
            )
            if config["image_url"]: embed.set_image(url=config["image_url"])
            await channel.send(content=f"{member.mention}", embed=embed)

@bot.event
async def on_member_remove(member: discord.Member):
    guild = member.guild
    if guild.id in leave_config:
        config = leave_config[guild.id]
        channel = guild.get_channel(config["channel_id"])
        if channel:
            embed = discord.Embed(
                title="👋 มีสมาชิกออกจากเซิร์ฟเวอร์",
                description=f"{config['message']}\n\n👤 **สมาชิก:** @{member.display_name}\n📊 **สมาชิกคงเหลือ:** {guild.member_count} คน",
                color=discord.Color.red()
            )
            if config["image_url"]: embed.set_image(url=config["image_url"])
            await channel.send(content=f"@{member.display_name} ออกจากเซิร์ฟเวอร์แล้ว", embed=embed)

@bot.event
async def on_ready():
    bot.add_view(CloseTicketView())
    print(f"บอทออนไลน์แล้ว: {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"ซิงก์ Slash Commands เรียบร้อย ({len(synced)} คำสั่ง)")
    except Exception as e:
        print(f"ซิงก์คำสั่งล้มเหลว: {e}")

bot.run("MTU0NjU0MzUxOTc3MzA5ODA3NQ.GCNv_0.eqPt2Eq-6Gos0cKbQM4wuQJS40hnq0ncVKz0eM")
