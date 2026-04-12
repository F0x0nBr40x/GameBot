import discord
from discord.ext import commands, tasks
from discord import app_commands
import time
import re
import os
import requests
import xml.etree.ElementTree as ET
from datetime import timedelta

TOKEN = os.getenv("TOKEN")

LOG_CHANNEL_ID = 1491146567548403774
NOTIFY_CHANNEL_ID = 1491682538710896640

WHITELIST = [727612384293814303]

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCce7nHkQfNDKfZh4Z8MCG_Q"

SPAM_LIMIT = 7
SPAM_TIME = 5

MUTE_TIMES = [3, 5, 10, 15, 20, 30]

# ===== INTENTS =====
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ===== VARIABLES =====
user_messages = {}
user_strikes = {}
warnings_db = {}
sent_videos = set()

LINK_REGEX = re.compile(r"(https?://\S+|www\.\S+)")

# ===== LOG =====
async def send_log(guild, msg):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(msg)

# =========================
# 📂 YOUTUBE FILE
# =========================
def load_videos():
    try:
        with open("videos.txt", "r") as f:
            return set(line.strip() for line in f if line.strip())
    except:
        return set()

def save_video(video_id):
    with open("videos.txt", "a") as f:
        f.write(video_id + "\n")

# =========================
# 🔨 BAN
# =========================
@tree.command(name="ban")
async def ban(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    await usuario.ban(reason=razon)

    embed = discord.Embed(title="🔨 Usuario baneado", description=f"{usuario}\n{razon}", color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

    await send_log(interaction.guild, f"🔨 BAN {usuario} | {razon}")

# =========================
# 🔓 UNBAN
# =========================
@tree.command(name="unban")
async def unban(interaction: discord.Interaction, user_id: str):
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    user = await bot.fetch_user(int(user_id))
    await interaction.guild.unban(user)

    await interaction.response.send_message(f"🔓 {user} desbaneado")

# =========================
# 👢 KICK
# =========================
@tree.command(name="kick")
async def kick(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):
    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    await usuario.kick(reason=razon)

    embed = discord.Embed(title="👢 Usuario expulsado", description=f"{usuario}\n{razon}", color=discord.Color.orange())
    await interaction.response.send_message(embed=embed)

    await send_log(interaction.guild, f"👢 KICK {usuario} | {razon}")

# =========================
# 🔇 MUTE
# =========================
@tree.command(name="mute")
async def mute(interaction: discord.Interaction, usuario: discord.Member, minutos: int, razon: str = "Sin razón"):
    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    await usuario.timeout(timedelta(minutes=minutos))

    embed = discord.Embed(title="🔇 Usuario muteado", description=f"{usuario}\n{minutos} min\n{razon}", color=discord.Color.dark_gray())
    await interaction.response.send_message(embed=embed)

    await send_log(interaction.guild, f"🔇 MUTE {usuario} | {razon}")

# =========================
# 🔊 UNMUTE
# =========================
@tree.command(name="unmute")
async def unmute(interaction: discord.Interaction, usuario: discord.Member):
    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    await usuario.timeout(None)
    await interaction.response.send_message(f"🔊 {usuario} desmuteado")

# =========================
# 💀 SOFTBAN
# =========================
@tree.command(name="softban")
async def softban(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    await usuario.ban(reason=razon)
    await usuario.unban()

    await interaction.response.send_message(f"💀 {usuario} softbaneado")
    await send_log(interaction.guild, f"💀 SOFTBAN {usuario}")

# =========================
# ⚠️ WARN
# =========================
@tree.command(name="warn")
async def warn(interaction: discord.Interaction, usuario: discord.Member, razon: str):
    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    if usuario.id not in warnings_db:
        warnings_db[usuario.id] = []

    warnings_db[usuario.id].append(razon)

    await interaction.response.send_message(f"⚠️ {usuario} advertido")
    await send_log(interaction.guild, f"⚠️ WARN {usuario} | {razon}")

# =========================
# 📋 WARNINGS
# =========================
@tree.command(name="warnings")
async def warnings(interaction: discord.Interaction, usuario: discord.Member):
    warns = warnings_db.get(usuario.id, [])

    if not warns:
        return await interaction.response.send_message("✅ Sin advertencias")

    texto = "\n".join([f"{i+1}. {w}" for i, w in enumerate(warns)])

    embed = discord.Embed(title=f"⚠️ {usuario}", description=texto, color=discord.Color.orange())
    await interaction.response.send_message(embed=embed)

# =========================
# 🧹 CLEAR WARNS
# =========================
@tree.command(name="clearwarns")
async def clearwarns(interaction: discord.Interaction, usuario: discord.Member):
    warnings_db[usuario.id] = []
    await interaction.response.send_message(f"🧹 Warns borrados de {usuario}")

# =========================
# 🧹 PURGE
# =========================
@tree.command(name="purge")
async def purge(interaction: discord.Interaction, cantidad: int):
    if not interaction.user.guild_permissions.manage_messages:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    await interaction.channel.purge(limit=cantidad)
    await interaction.response.send_message(f"🧹 {cantidad} mensajes eliminados", ephemeral=True)

# =========================
# 🐢 SLOWMODE
# =========================
@tree.command(name="slowmode")
async def slowmode(interaction: discord.Interaction, segundos: int):
    await interaction.channel.edit(slowmode_delay=segundos)
    await interaction.response.send_message(f"🐢 Slowmode: {segundos}s")

# =========================
# 🔒 LOCK
# =========================
@tree.command(name="lock")
async def lock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("🔒 Canal bloqueado")

# =========================
# 🔓 UNLOCK
# =========================
@tree.command(name="unlock")
async def unlock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("🔓 Canal desbloqueado")

# =========================
# 🚀 YOUTUBE LOOP (SIN SPAM)
# =========================
@tasks.loop(minutes=2)
async def check_youtube():
    global sent_videos

    try:
        r = requests.get(RSS_URL)
        root = ET.fromstring(r.content)

        entries = root.findall("{http://www.w3.org/2005/Atom}entry")

        # 🔥 PRIMER ARRANQUE
        if not sent_videos:
            for entry in entries[:5]:
                video_id = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
                sent_videos.add(video_id)
                save_video(video_id)
            print("📂 Videos guardados (inicio)")
            return

        for entry in entries[:5]:
            video_id = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
            title = entry.find("{http://www.w3.org/2005/Atom}title").text

            if video_id in sent_videos:
                continue

            sent_videos.add(video_id)
            save_video(video_id)

            channel = bot.get_channel(NOTIFY_CHANNEL_ID)
            if channel:
                await channel.send(f"🚀 NUEVO VIDEO\n🔥 {title}\nhttps://youtu.be/{video_id}")

    except Exception as e:
        print("ERROR YOUTUBE:", e)

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    global sent_videos

    sent_videos = load_videos()

    if not check_youtube.is_running():
        check_youtube.start()

    try:
        synced = await tree.sync()
        print(f"✅ Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(e)

    print(f"🔥 KrBot listo: {bot.user}")

# =========================
# ANTISPAM / ANTILINK
# =========================
@bot.event
async def on_message(message):
    if message.author.bot or message.author.id in WHITELIST:
        return await bot.process_commands(message)

    now = time.time()

    if LINK_REGEX.search(message.content):
        await message.delete()
        await message.guild.ban(message.author, reason="Links")
        await send_log(message.guild, f"🔨 BAN {message.author}")
        return

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

        await message.author.timeout(timedelta(minutes=MUTE_TIMES[strikes]))
        await send_log(message.guild, f"🔇 MUTE {message.author}")

        user_strikes[message.author.id] = strikes + 1
        user_messages[message.author.id] = []

    await bot.process_commands(message)

# =========================
# RUN
# =========================
bot.run(TOKEN)