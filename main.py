import discord
from discord.ext import commands, tasks
import time
import re
import os
from datetime import timedelta
import requests
import xml.etree.ElementTree as ET

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")

LOG_CHANNEL_ID = 1491146567548403774
RULES_CHANNEL_ID = 1303892760692265111
NOTIFY_CHANNEL_ID = 1491682538710896640

WHITELIST = [727612384293814303]

# 🔥 TU RSS (YA FUNCIONANDO)
RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw"  # ⚠️ luego cambiamos por el tuyo real

YOUTUBE_LINK = "https://youtube.com/@krmanx"
TIKTOK_LINK = "https://www.tiktok.com/@krmanx0"

JOIN_LIMIT = 5
JOIN_TIME = 10

SPAM_LIMIT = 5
SPAM_TIME = 5

MUTE_TIMES = [3, 5, 10, 15, 20, 30]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

join_times = []
user_messages = {}
user_strikes = {}

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
        embed = discord.Embed(title="📜 REGLAS", color=discord.Color.dark_theme())
        embed.add_field(name="Respeto", value="No insultos", inline=False)
        embed.add_field(name="Links", value="🚫 BAN automático", inline=False)
        embed.set_footer(text="Kr Community")
        await channel.send(embed=embed)

# ===== READY =====
@bot.event
async def on_ready():
    print(f"Bot listo: {bot.user}")

    for guild in bot.guilds:
        await send_rules(guild)

    check_youtube.start()

# ===== RAID =====
@bot.event
async def on_member_join(member):
    global join_times

    now = time.time()
    join_times.append(now)
    join_times = [t for t in join_times if now - t < JOIN_TIME]

    if len(join_times) >= JOIN_LIMIT:
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

    if LINK_REGEX.search(message.content):
        try:
            await message.delete()
            await message.guild.ban(message.author)
        except:
            pass
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

        try:
            await message.author.timeout(timedelta(minutes=MUTE_TIMES[strikes]))
        except:
            pass

        user_strikes[message.author.id] = strikes + 1
        user_messages[message.author.id] = []

    await bot.process_commands(message)

# ===== YOUTUBE RSS =====
last_video_id = None

@tasks.loop(minutes=2)
async def check_youtube():
    global last_video_id

    try:
        response = requests.get(RSS_URL)
        root = ET.fromstring(response.content)

        entries = root.findall("{http://www.w3.org/2005/Atom}entry")

        if not entries:
            return

        latest = entries[0]
        video_id = latest.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
        title = latest.find("{http://www.w3.org/2005/Atom}title").text

        if last_video_id is None:
            last_video_id = video_id
            return

        if video_id != last_video_id:
            last_video_id = video_id

            for guild in bot.guilds:
                channel = guild.get_channel(NOTIFY_CHANNEL_ID)
                if channel:
                    embed = discord.Embed(
                        title="🚀 NUEVO VIDEO",
                        description=f"🔥 {title}\n\n🎥 https://youtu.be/{video_id}",
                        color=discord.Color.red()
                    )
                    embed.set_footer(text="Kr Community")
                    await channel.send(embed=embed)

    except Exception as e:
        print(e)

# ===== COMANDO =====
@bot.command()
async def redes(ctx):
    await ctx.send(f"YouTube: {YOUTUBE_LINK}\nTikTok: {TIKTOK_LINK}")

# ===== RUN =====
bot.run(TOKEN)