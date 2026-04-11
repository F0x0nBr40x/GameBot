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
tree = bot.tree

# ===== VARIABLES =====
join_times = []
user_messages = {}
user_strikes = {}
sent_videos = set()

LINK_REGEX = re.compile(r"(https?://\S+|www\.\S+)")

# ===== LOG =====
async def send_log(guild, msg):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(msg)

# =========================
# 🛠️ LISTA DE COMANDOS
# =========================
@tree.command(name="comandos", description="Ver comandos disponibles")
async def comandos(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛠️ KRBOT | COMANDOS",
        description="Sistema de moderación:",
        color=discord.Color.blue()
    )
    embed.add_field(name="/ban", value="Banear usuario", inline=False)
    embed.add_field(name="/kick", value="Expulsar usuario", inline=False)
    embed.add_field(name="/mute", value="Mutear usuario", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

# =========================
# 🔨 BAN (SLASH)
# =========================
@tree.command(name="ban", description="Banear usuario")
@app_commands.describe(usuario="Usuario", razon="Razón")
async def slash_ban(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):

    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    await usuario.ban(reason=razon)

    embed = discord.Embed(
        title="🔨 Usuario baneado",
        description=f"👤 {usuario}\n📌 {razon}",
        color=discord.Color.red()
    )

    await interaction.response.send_message(embed=embed)

    await send_log(interaction.guild, f"🔨 BAN {usuario} | {razon}")

# =========================
# 👢 KICK (SLASH)
# =========================
@tree.command(name="kick", description="Expulsar usuario")
@app_commands.describe(usuario="Usuario", razon="Razón")
async def slash_kick(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):

    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    await usuario.kick(reason=razon)

    embed = discord.Embed(
        title="👢 Usuario expulsado",
        description=f"👤 {usuario}\n📌 {razon}",
        color=discord.Color.orange()
    )

    await interaction.response.send_message(embed=embed)

    await send_log(interaction.guild, f"👢 KICK {usuario} | {razon}")

# =========================
# 🔇 MUTE (SLASH)
# =========================
@tree.command(name="mute", description="Mutear usuario")
@app_commands.describe(usuario="Usuario", minutos="Tiempo", razon="Razón")
async def slash_mute(interaction: discord.Interaction, usuario: discord.Member, minutos: int, razon: str = "Sin razón"):

    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    await usuario.timeout(timedelta(minutes=minutos))

    embed = discord.Embed(
        title="🔇 Usuario muteado",
        description=f"👤 {usuario}\n⏱ {minutos} min\n📌 {razon}",
        color=discord.Color.dark_gray()
    )

    await interaction.response.send_message(embed=embed)

    await send_log(interaction.guild, f"🔇 MUTE {usuario} {minutos}min | {razon}")

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    await tree.sync()
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
        await send_log(message.guild, f"🔨 BAN {message.author} (link)")
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