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

# ===== REGLAS =====
async def send_rules(guild):
    channel = guild.get_channel(RULES_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="📜 KRHUB | REGLAMENTO OFICIAL",
            description=(
                "Bienvenido a la comunidad oficial de KrMan.\n\n"
                "Este servidor sigue las normas de Discord y busca un ambiente sano, seguro y divertido para todos.\n\n"
                "📌 Lee y respeta todas las reglas para permanecer en la comunidad."
            ),
            color=discord.Color.dark_red()
        )

        embed.set_image(url="https://cdn.discordapp.com/attachments/1490502904832852168/1491645919148376215/BF8B437C-234D-4AEE-9BD9-18B9E71600E0.png")

        embed.add_field(name="🤝 Respeto y convivencia", value="No acoso, insultos o discriminación.", inline=False)
        embed.add_field(name="🚫 Contenido prohibido", value="Prohibido contenido +18, gore o ilegal.", inline=False)
        embed.add_field(name="🔗 Enlaces", value="❌ Prohibidos.\n🚨 BAN permanente.", inline=False)
        embed.add_field(name="💬 Spam y flood", value="No mensajes repetidos o flood.", inline=False)
        embed.add_field(name="👮 Staff", value="Respeta decisiones del staff.", inline=False)
        embed.add_field(name="🧑 Identidad", value="No suplantación ni nombres ofensivos.", inline=False)
        embed.add_field(name="⚙️ Hacks", value="Prohibido promover hacks o exploits.", inline=False)
        embed.add_field(name="🔒 Privacidad", value="No compartas info personal.", inline=False)

        embed.add_field(
            name="⚖️ Normas de Discord",
            value="https://discord.com/guidelines",
            inline=False
        )

        embed.add_field(
            name="🚨 Sanciones",
            value="⚠️ Advertencia\n🔇 Mute\n🚫 Kick\n🔨 Ban permanente",
            inline=False
        )

        embed.set_footer(text="Kr Community | Sistema de moderación activo")

        await channel.send(embed=embed)

# ===== YOUTUBE FILE =====
def load_videos():
    try:
        with open("/app/videos.txt", "r") as f:
            return set(line.strip() for line in f if line.strip())
    except:
        return set()

def save_video(video_id):
    with open("/app/videos.txt", "a") as f:
        f.write(video_id + "\n")

# ===== READY =====
@bot.event
async def on_ready():
    global sent_videos

    sent_videos = load_videos()

    if not check_youtube.is_running():
        check_youtube.start()

    for guild in bot.guilds:
        await send_log(guild, "KrBot encendido correctamente... ✅")

    print(f"Bot listo: {bot.user}")

# ===== COMANDO REGLAS =====
@bot.command()
@commands.has_permissions(administrator=True)
async def reglas(ctx):
    await send_rules(ctx.guild)
    await send_log(ctx.guild, "📜 Reglas enviadas manualmente")

# ===== RAID =====
@bot.event
async def on_member_join(member):
    global join_times

    now = time.time()
    join_times.append(now)
    join_times = [t for t in join_times if now - t < JOIN_TIME]

    if len(join_times) >= JOIN_LIMIT:
        await send_log(member.guild, "🚨 RAID DETECTADO\n🔨 Acciones automáticas ejecutadas")

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

    # ANTI LINK
    if LINK_REGEX.search(message.content):
        try:
            await message.delete()
            await message.guild.ban(message.author, reason="Links prohibidos")
            await send_log(
                message.guild,
                f"🔨 BAN\n👤 Usuario: {message.author}\n📌 Razón: Envío de links"
            )
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
            await send_log(
                message.guild,
                f"🔇 MUTE\n👤 Usuario: {message.author}\n⏱ Tiempo: {MUTE_TIMES[strikes]} min\n📌 Razón: Spam"
            )
        except:
            pass

        user_strikes[message.author.id] = strikes + 1
        user_messages[message.author.id] = []

    await bot.process_commands(message)

# ===== YOUTUBE =====
@tasks.loop(minutes=1)
async def check_youtube():
    global sent_videos

    try:
        r = requests.get(RSS_URL)
        root = ET.fromstring(r.content)

        entries = root.findall("{http://www.w3.org/2005/Atom}entry")

        # 🔥 PRIMER ARRANQUE → NO MANDA VIDEOS
        if not sent_videos:
            for entry in entries[:5]:
                video_id = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
                sent_videos.add(video_id)
                save_video(video_id)

            print("📂 Videos iniciales guardados (no enviados)")
            return

        # 🚀 SOLO NUEVOS
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
                    await channel.send(
                        f"🚀 NUEVO VIDEO\n🔥 {title}\nhttps://youtu.be/{video_id}"
                    )

    except Exception as e:
        print("ERROR YOUTUBE:", e)

# ===== RUN =====
bot.run(TOKEN)