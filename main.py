import discord
from discord.ext import commands
import time
import re
import os
from datetime import timedelta

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")

LOG_CHANNEL_ID = 1491146567548403774
RULES_CHANNEL_ID = 1303892760692265111

WHITELIST = [727612384293814303]

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
lockdown_active = False

# ===== REGEX =====
LINK_REGEX = re.compile(r"(https?://\S+|www\.\S+)")
INVITE_REGEX = re.compile(r"(discord\.gg/|discord\.com/invite/)")

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
            title="📜 Reglas del Servidor",
            description="Lee y respeta las reglas para evitar sanciones.",
            color=discord.Color.dark_theme()
        )

        embed.add_field(
            name="1. Respeto",
            value="No insultos, odio ni toxicidad.",
            inline=False
        )
        embed.add_field(
            name="2. No spam",
            value="Evita flood y mensajes repetidos.",
            inline=False
        )
        embed.add_field(
            name="3. No links",
            value="Links no autorizados = BAN automático.",
            inline=False
        )
        embed.add_field(
            name="4. Sigue las normas",
            value="El staff tiene la última palabra.",
            inline=False
        )

        embed.set_footer(text="KrMan Community")

        await channel.send(embed=embed)

# ===== READY =====
@bot.event
async def on_ready():
    print(f"Bot listo: {bot.user}")

    for guild in bot.guilds:
        await send_rules(guild)

# ===== RAID DETECTOR =====
@bot.event
async def on_member_join(member):
    global join_times, lockdown_active

    now = time.time()
    join_times.append(now)
    join_times = [t for t in join_times if now - t < JOIN_TIME]

    if len(join_times) >= JOIN_LIMIT:
        lockdown_active = True
        await send_log(member.guild, "🚨 RAID DETECTADO → BAN MASIVO")

        for m in member.guild.members:
            if not m.bot:
                try:
                    await m.ban(reason="Raid detectado")
                except:
                    pass

# ===== MENSAJES =====
@bot.event
async def on_message(message):
    global user_messages, user_strikes

    if message.author.bot or message.author.id in WHITELIST:
        return await bot.process_commands(message)

    now = time.time()

    # ===== ANTI LINK =====
    if LINK_REGEX.search(message.content):
        try:
            await message.delete()
            await message.guild.ban(message.author, reason="Envío de links")
            await send_log(message.guild, f"🔗 {message.author} baneado por link")
        except:
            pass
        return

    # ===== SPAM =====
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

        mute_time = MUTE_TIMES[strikes]

        try:
            await message.author.timeout(timedelta(minutes=mute_time))
            await send_log(
                message.guild,
                f"🔇 {message.author} mute {mute_time} min (strike {strikes+1})"
            )
        except:
            pass

        user_strikes[message.author.id] = strikes + 1
        user_messages[message.author.id] = []

    await bot.process_commands(message)

# ===== COMANDOS =====
@bot.command()
@commands.has_permissions(administrator=True)
async def lockdown(ctx):
    global lockdown_active
    lockdown_active = True

    for channel in ctx.guild.text_channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)

    await ctx.send("🔒 Servidor en lockdown")
    await send_log(ctx.guild, "🔒 Lockdown manual activado")

@bot.command()
@commands.has_permissions(administrator=True)
async def unlock(ctx):
    global lockdown_active
    lockdown_active = False

    for channel in ctx.guild.text_channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)

    await ctx.send("🔓 Lockdown desactivado")
    await send_log(ctx.guild, "🔓 Lockdown desactivado")

# ===== RUN =====
bot.run(TOKEN)