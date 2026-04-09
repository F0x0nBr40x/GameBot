import discord
from discord.ext import commands, tasks
import time
import re
import os
import requests
import xml.etree.ElementTree as ET
from datetime import timedelta

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")

LOG_CHANNEL_ID = 1491146567548403774
RULES_CHANNEL_ID = 1303892760692265111
NOTIFY_CHANNEL_ID = 1491682538710896640

WHITELIST = [727612384293814303]

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCce7nHkQfNDKfZh4Z8MCG_Q"

YOUTUBE_LINK = "https://youtube.com/@krmanx"
TIKTOK_LINK = "https://www.tiktok.com/@krmanx0"

JOIN_LIMIT = 5
JOIN_TIME = 10

SPAM_LIMIT = 5
SPAM_TIME = 5

MUTE_TIMES = [3, 5, 10, 15, 20, 30]

# ===== INTENTS =====
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== VARIABLES =====
join_times = []
user_messages = {}
user_strikes = {}
last_video_id = None

LINK_REGEX = re.compile(r"(https?://\S+|www\.\S+)")

# ===== LOG =====
async def send_log(guild, msg):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(msg)

# ===== REGLAS =====
async def send_rules(guild):
    channel = guild.get_channel(RULES_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="📜 REGLAMENTO OFICIAL DEL SERVIDOR",
            color=discord.Color.dark_theme()
        )

        embed.description = """
🔹 1. Respeto ante todo
• Trata a todos con respeto.
• No acoso, insultos o discriminación.

🔹 2. Prohibido contenido inapropiado
• Nada de contenido +18, gore o ilegal.

🔹 3. No spam ni flood
• No mensajes repetidos ni exceso de emojis.
• No promociones sin permiso.

🔹 4. 🚫 LINKS PROHIBIDOS
❌ Prohibido cualquier tipo de link.
🚨 BAN PERMANENTE.

🔹 5. Uso correcto de canales
• Usa cada canal correctamente.

🔹 6. Respeta al staff
• Sigue indicaciones del staff.

🔹 7. Nombres adecuados
• No ofensivos ni suplantación.

🔹 8. No hacks
• Prohibido exploits.

🔹 9. Privacidad
• No compartas info personal.

🔹 10. Sanciones
⚠️ Warn
🔇 Mute
🚫 Kick
🔨 Ban

🔹 11. Aceptación
• Al entrar aceptas reglas.

Kr Community
"""
        await channel.send(embed=embed)

# ===== READY =====
@bot.event
async def on_ready():
    print(f"Bot listo: {bot.user}")

    for guild in bot.guilds:
        await send_rules(guild)
        await send_log(guild, "✅ Bot encendido correctamente")

    check_youtube.start()

# ===== RAID =====
@bot.event
async def on_member_join(member):
    global join_times

    now = time.time()
    join_times.append(now)
    join_times = [t for t in join_times if now - t < JOIN_TIME]

    if len(join_times) >= JOIN_LIMIT:
        await send_log(member.guild, "🚨 RAID DETECTADO")

        for m in member.guild.members:
            if not m.bot:
                try:
                    await m.ban(reason="Raid")
                except:
                    pass

# ===== MENSAJES =====
@bot.event
async def on_message(message):
    global user_messages, user_strikes

    if message.author.bot or message.author.id in WHITELIST:
        return await bot.process_commands(message)

    now = time.time()

    # ANTI LINK = BAN
    if LINK_REGEX.search(message.content):
        try:
            await message.delete()
            await message.guild.ban(message.author, reason="Links prohibidos")
            await send_log(message.guild, f"🔨 {message.author} baneado por link")
        except:
            pass
        return

    # SPAM
    if message.author.id not in user_messages:
        user_messages[message.author.id] = []

    user_messages[message.author.id].append(now)
    user_messages[message.author.id] = [
        t for t in user_messages[message.author.id] if now - t < SPAM_TIME
    ]

    if len(user_messages[message.author.id]) >= SPAM_LIMIT:
        strikes = user_strikes.get(message.author.id, 0)

        if strikes >= len(MUTE_TIMES):
            strikes = len(MUTE_TIMES) - 1

        try:
            await message.author.timeout(timedelta(minutes=MUTE_TIMES[strikes]))
            await send_log(message.guild, f"🔇 {message.author} mute {MUTE_TIMES[strikes]} min")
        except:
            pass

        user_strikes[message.author.id] = strikes + 1
        user_messages[message.author.id] = []

    await bot.process_commands(message)

# ===== YOUTUBE =====
# ===== YOUTUBE =====

# GUARDAR ÚLTIMO VIDEO
def load_last_video():
    try:
        with open("last_video.txt", "r") as f:
            return f.read().strip()
    except:
        return None

def save_last_video(video_id):
    with open("last_video.txt", "w") as f:
        f.write(video_id)

last_video_id = load_last_video()

@tasks.loop(minutes=1)
async def check_youtube():
    global last_video_id

    print("🔍 Revisando YouTube...")

    try:
        r = requests.get(RSS_URL)
        root = ET.fromstring(r.content)

        entries = root.findall("{http://www.w3.org/2005/Atom}entry")

        if not entries:
            print("❌ No hay videos")
            return

        latest = None

        for entry in entries:
            vid = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
            
            if vid != last_video_id:
                latest = entry
                break

        if latest is None:
            print("⚠️ No hay nuevos videos")
            return

        video_id = latest.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
        title = latest.find("{http://www.w3.org/2005/Atom}title").text

        print(f"🚀 Nuevo video: {title}")

        last_video_id = video_id
        save_last_video(video_id)

        for guild in bot.guilds:
            channel = guild.get_channel(NOTIFY_CHANNEL_ID)

            if channel:
                await channel.send(
                    f"🚀 NUEVO VIDEO\n🔥 {title}\nhttps://youtu.be/{video_id}"
                )
                print("✅ Enviado a Discord")
            else:
                print("❌ Canal no encontrado")

    except Exception as e:
        print("💥 ERROR:", e)

# ===== RUN =====
bot.run(TOKEN)
