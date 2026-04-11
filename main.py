import discord
from discord.ext import commands, tasks
import time
import re
import os
import requests
import xml.etree.ElementTree as ET
from datetime import timedelta
import os
TOKEN = os.getenv("TOKEN")

# ===== CONFIG =====
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
# 📜 COMANDOS LISTA
# =========================
@bot.command()
async def comandos(ctx):
    embed = discord.Embed(
        title="🛠️ KRBOT | COMANDOS",
        description="Sistema de moderación disponible:",
        color=discord.Color.blue()
    )

    embed.add_field(name="🔨 !ban", value="!ban @user razón", inline=False)
    embed.add_field(name="👢 !kick", value="!kick @user razón", inline=False)
    embed.add_field(name="🔇 !mute", value="!mute @user minutos razón", inline=False)

    embed.set_footer(text="KrBot | Moderación activa")

    await ctx.send(embed=embed)

# =========================
# 🔨 BAN
# =========================
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, razon="Sin razón"):
    try:
        await member.ban(reason=razon)
        await ctx.send(f"🔨 {member} fue baneado")

        await send_log(
            ctx.guild,
            f"🔨 BAN\n👤 Usuario: {member}\n📌 Razón: {razon}\n👮 Mod: {ctx.author}"
        )
    except:
        await ctx.send("❌ Error al banear")

# =========================
# 👢 KICK
# =========================
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, razon="Sin razón"):
    try:
        await member.kick(reason=razon)
        await ctx.send(f"👢 {member} fue expulsado")

        await send_log(
            ctx.guild,
            f"👢 KICK\n👤 Usuario: {member}\n📌 Razón: {razon}\n👮 Mod: {ctx.author}"
        )
    except:
        await ctx.send("❌ Error al expulsar")

# =========================
# 🔇 MUTE
# =========================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutos: int, *, razon="Sin razón"):
    try:
        await member.timeout(timedelta(minutes=minutos))
        await ctx.send(f"🔇 {member} muteado {minutos} min")

        await send_log(
            ctx.guild,
            f"🔇 MUTE\n👤 Usuario: {member}\n⏱ Tiempo: {minutos} min\n📌 Razón: {razon}\n👮 Mod: {ctx.author}"
        )
    except:
        await ctx.send("❌ Error al mutear")

# ===== READY =====
@bot.event
async def on_ready():
    global sent_videos

    sent_videos = load_videos()

    if not check_youtube.is_running():
        check_youtube.start()

    for guild in bot.guilds:
        await send_log(guild, "🟢 KrBot encendido correctamente")

    print(f"Bot listo: {bot.user}")

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

    # ANTI LINK
    if LINK_REGEX.search(message.content):
        try:
            await message.delete()
            await message.guild.ban(message.author, reason="Links")
            await send_log(message.guild, f"🔨 BAN {message.author} (link)")
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
            await send_log(message.guild, f"🔇 MUTE {message.author}")
        except:
            pass

        user_strikes[message.author.id] = strikes + 1
        user_messages[message.author.id] = []

    await bot.process_commands(message)

# ===== YOUTUBE FILE =====
def load_videos():
    try:
        with open("videos.txt", "r") as f:
            return set(line.strip() for line in f if line.strip())
    except:
        return set()

def save_video(video_id):
    with open("videos.txt", "a") as f:
        f.write(video_id + "\n")

# ===== YOUTUBE =====
@tasks.loop(minutes=1)
async def check_youtube():
    global sent_videos

    try:
        r = requests.get(RSS_URL)
        root = ET.fromstring(r.content)
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")

        if not sent_videos:
            for entry in entries[:5]:
                video_id = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
                sent_videos.add(video_id)
                save_video(video_id)
            return

        for entry in entries[:5]:
            video_id = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
            title = entry.find("{http://www.w3.org/2005/Atom}title").text

            if video_id in sent_videos:
                continue

            sent_videos.add(video_id)
            save_video(video_id)

            for guild in bot.guilds:
                channel = bot.get_channel(NOTIFY_CHANNEL_ID)
                if channel:
                    await channel.send(f"🚀 NUEVO VIDEO\n🔥 {title}\nhttps://youtu.be/{video_id}")

    except Exception as e:
        print("ERROR YOUTUBE:", e)

# ===== RUN =====
bot.run(TOKEN)
