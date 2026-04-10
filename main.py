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
            title="📜 KRHUB | REGLAMENTO OFICIAL",
            description=(
                "Bienvenido a la comunidad oficial de KrMan.\n\n"
                "Este servidor sigue las normas de Discord y busca un ambiente sano, seguro y divertido para todos.\n\n"
                "📌 Lee y respeta todas las reglas para permanecer en la comunidad."
            ),
            color=discord.Color.dark_red()
        )

        # 🖼️ IMAGEN
        embed.set_image(url="https://cdn.discordapp.com/attachments/1490502904832852168/1491645919148376215/BF8B437C-234D-4AEE-9BD9-18B9E71600E0.png")

        # 🔹 REGLAS
        embed.add_field(
            name="🤝 Respeto y convivencia",
            value="No se permite acoso, insultos, amenazas o discriminación.",
            inline=False
        )

        embed.add_field(
            name="🚫 Contenido prohibido",
            value="Prohibido contenido +18, gore, ilegal o que viole las normas de Discord.",
            inline=False
        )

        embed.add_field(
            name="🔗 Enlaces",
            value="❌ Está prohibido enviar cualquier tipo de link.\n🚨 Sanción directa: BAN permanente.",
            inline=False
        )

        embed.add_field(
            name="💬 Spam y flood",
            value="No spam, mensajes repetidos o uso excesivo de emojis.",
            inline=False
        )

        embed.add_field(
            name="👮 Staff",
            value="Las decisiones del staff deben respetarse en todo momento.",
            inline=False
        )

        embed.add_field(
            name="🧑 Identidad y comportamiento",
            value="No suplantación de identidad ni nombres ofensivos.",
            inline=False
        )

        embed.add_field(
            name="⚙️ Hacks / trampas",
            value="Prohibido promover hacks, exploits o actividades ilegales.",
            inline=False
        )

        embed.add_field(
            name="🔒 Privacidad",
            value="No compartas información personal (tuya o de otros).",
            inline=False
        )

        embed.add_field(
            name="⚖️ Normas de Discord",
            value=(
                "Este servidor sigue las normas oficiales de Discord.\n"
                "📖 Léelas aquí:\nhttps://discord.com/guidelines"
            ),
            inline=False
        )

        embed.add_field(
            name="🚨 Sanciones",
            value="Dependiendo del caso:\n⚠️ Advertencia\n🔇 Mute\n🚫 Kick\n🔨 Ban permanente",
            inline=False
        )

        embed.set_footer(text="Kr Community | Sistema de moderación activo")

        await channel.send(embed=embed)

# ===== READY =====
@bot.event
async def on_ready():
    print(f"Bot listo: {bot.user}")

@bot.command()
@commands.has_permissions(administrator=True)
async def reglas(ctx):
    await send_rules(ctx.guild)
    await send_log(ctx.guild, "📜 Reglas enviadas manualmente")

  @bot.event
async def on_ready():
    print(f"Bot listo: {bot.user}")
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

def load_videos():
    try:
        with open("/app/videos.txt", "r") as f:
            data = set(f.read().splitlines())
            print("📂 Videos cargados:", data)
            return data
    except:
        print("📂 No hay archivo, creando nuevo")
        return set()

def save_video(video_id):
    try:
        with open("/app/videos.txt", "a") as f:
            f.write(video_id + "\n")
        print(f"💾 Guardado: {video_id}")
    except Exception as e:
        print("❌ ERROR GUARDANDO:", e)

@bot.event
async def on_ready():
    global sent_videos
    sent_videos = load_videos()
    check_youtube.start()
    print(f"Bot listo: {bot.user}")

@tasks.loop(minutes=1)
async def check_youtube():
    global sent_videos

    print("🔍 Revisando YouTube...")

    try:
        r = requests.get(RSS_URL)
        root = ET.fromstring(r.content)

        entries = root.findall("{http://www.w3.org/2005/Atom}entry")

        if not entries:
            print("❌ No hay videos en RSS")
            return

        for entry in entries[:5]:  # revisa últimos 5 videos
            video_id = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
            title = entry.find("{http://www.w3.org/2005/Atom}title").text

            if video_id in sent_videos:
                print(f"⏭️ Ya enviado: {title}")
                continue

            print(f"🚀 Nuevo video detectado: {title}")

            sent_videos.add(video_id)
            save_video(video_id)

            for guild in bot.guilds:
                channel = bot.get_channel(NOTIFY_CHANNEL_ID)

                if channel:
                    await channel.send(
                        f"🚀 NUEVO VIDEO\n🔥 {title}\nhttps://youtu.be/{video_id}"
                    )
                    print("✅ Enviado a Discord")
                else:
                    print("❌ Canal no encontrado")

    except Exception as e:
        print("💥 ERROR RSS:", e)

# ===== RUN =====
bot.run(TOKEN)
