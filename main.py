import discord
from discord.ext import commands
from discord import app_commands
import time
import re
import os
from datetime import timedelta

TOKEN = os.getenv("TOKEN")

LOG_CHANNEL_ID = 1491146567548403774

WHITELIST = [727612384293814303]

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

LINK_REGEX = re.compile(r"(https?://\S+|www\.\S+)")

# ===== LOG =====
async def send_log(guild, msg):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(msg)

# =========================
# 🛠️ COMANDOS
# =========================
@tree.command(name="comandos", description="Ver comandos disponibles")
async def comandos(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛠️ KRBOT | COMANDOS",
        color=discord.Color.blue()
    )

    embed.add_field(name="/ban", value="Banear usuario", inline=False)
    embed.add_field(name="/kick", value="Expulsar usuario", inline=False)
    embed.add_field(name="/mute", value="Mutear usuario", inline=False)
    embed.add_field(name="/warn", value="Advertir usuario", inline=False)
    embed.add_field(name="/warnings", value="Ver advertencias", inline=False)
    embed.add_field(name="/clearwarns", value="Borrar advertencias", inline=False)
    embed.add_field(name="/removewarn", value="Eliminar advertencia", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

# =========================
# 🔨 BAN
# =========================
@tree.command(name="ban")
async def ban(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):

    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    await usuario.ban(reason=razon)

    await interaction.response.send_message(f"🔨 {usuario} baneado")

    await send_log(interaction.guild, f"🔨 BAN {usuario} | {razon}")

# =========================
# 👢 KICK
# =========================
@tree.command(name="kick")
async def kick(interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):

    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    await usuario.kick(reason=razon)

    await interaction.response.send_message(f"👢 {usuario} expulsado")

    await send_log(interaction.guild, f"👢 KICK {usuario} | {razon}")

# =========================
# 🔇 MUTE
# =========================
@tree.command(name="mute")
async def mute(interaction: discord.Interaction, usuario: discord.Member, minutos: int, razon: str = "Sin razón"):

    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    await usuario.timeout(timedelta(minutes=minutos))

    await interaction.response.send_message(f"🔇 {usuario} muteado {minutos} min")

    await send_log(interaction.guild, f"🔇 MUTE {usuario} | {razon}")

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

    total = len(warnings_db[usuario.id])

    embed = discord.Embed(
        title="⚠️ Advertencia",
        description=f"{usuario}\n📌 {razon}\n📊 Total: {total}",
        color=discord.Color.orange()
    )

    await interaction.response.send_message(embed=embed)

    await send_log(interaction.guild, f"⚠️ WARN {usuario} | {razon}")

# =========================
# 📋 VER WARNS
# =========================
@tree.command(name="warnings")
async def warnings(interaction: discord.Interaction, usuario: discord.Member):

    warns = warnings_db.get(usuario.id, [])

    if not warns:
        return await interaction.response.send_message("✅ Sin advertencias")

    texto = "\n".join([f"{i+1}. {w}" for i, w in enumerate(warns)])

    embed = discord.Embed(
        title=f"⚠️ {usuario}",
        description=texto,
        color=discord.Color.orange()
    )

    await interaction.response.send_message(embed=embed)

# =========================
# 🧹 CLEAR WARNS
# =========================
@tree.command(name="clearwarns")
async def clearwarns(interaction: discord.Interaction, usuario: discord.Member):

    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ Sin permisos", ephemeral=True)

    warnings_db[usuario.id] = []

    await interaction.response.send_message(f"🧹 Warns borrados de {usuario}")

# =========================
# ❌ REMOVE WARN
# =========================
@tree.command(name="removewarn")
async def removewarn(interaction: discord.Interaction, usuario: discord.Member, numero: int):

    warns = warnings_db.get(usuario.id, [])

    if not warns or numero < 1 or numero > len(warns):
        return await interaction.response.send_message("❌ Número inválido")

    removed = warns.pop(numero - 1)

    await interaction.response.send_message(f"❌ Eliminado: {removed}")

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

    if len(message.content) < 3:
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