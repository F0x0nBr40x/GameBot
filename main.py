import discord
from discord.ext import commands, tasks
import time
import re
import os
from datetime import timedelta

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")

LOG_CHANNEL_ID = 1491146567548403774
RULES_CHANNEL_ID = 1303892760692265111
NOTIFY_CHANNEL_ID = 1491682538710896640

WHITELIST = [727612384293814303]

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

# ===== REGEX =====
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

        embed.add_field(name="🔹 1. Respeto ante todo",
                        value="No acoso, insultos o discriminación.",
                        inline=False)

        embed.add_field(name="🔹 2. Contenido inapropiado",
                        value="Prohibido +18, gore o ilegal.",
                        inline=False)

        embed.add_field(name="🔹 3. No spam ni flood",
                        value="No mensajes repetidos ni promociones.",
                        inline=False)

        embed.add_field(name="🔹 4. 🚫 LINKS PROHIBIDOS",
                        value="BAN PERMANENTE sin advertencia.",
                        inline=False)

        embed.add_field(name="🔹 5. Uso de canales",
                        value="Usa cada canal correctamente.",
                        inline=False)

        embed.add_field(name="🔹 6. Respeta al staff",
                        value="Sigue indicaciones siempre.",
                        inline=False)

        embed.add_field(name="🔹 7. Nombres adecuados",
                        value="Nada ofensivo o suplantación.",
                        inline=False)

        embed.add_field(name="🔹 8. No hacks",
                        value="Prohibido exploits o trampas.",
                        inline=False)

        embed.add_field(name="🔹 9. Privacidad",
                        value="No compartas info personal.",
                        inline=False)

        embed.add_field(name="🔹 10. Sanciones",
                        value="Warn / Mute / Kick / Ban",
                        inline=False)

        embed.add_field(name="🔹 11. Aceptación",
                        value="Al entrar aceptas las reglas.",
                        inline=False)

        embed.set_footer(text="Kr Community")

        await channel.send(embed=embed)

# ===== READY =====
@bot.event
async def on_ready():
    print(f"Bot listo: {bot.user}")

    for guild in bot.guilds:
        await send_rules(guild)

    youtube_notifier.start()

# ===== RAID =====
@bot.event
async def on_member_join(member):
    global join_times

    now = time.time()
    join_times.append(now)
    join_times = [t for t in join_times if now - t < JOIN_TIME]

    if len(join_times) >= JOIN_LIMIT:
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
            await message.guild.ban(message.author, reason="Links prohibidos")
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
                f"🔇 {message.author} mute {mute_time} min"
            )
        except:
            pass

        user_strikes[message.author.id] = strikes + 1
        user_messages[message.author.id] = []

    await bot.process_commands(message)

# ===== NOTIFICACIONES =====
last_video = None

@tasks.loop(minutes=5)
async def youtube_notifier():
    global last_video

    for guild in bot.guilds:
        channel = guild.get_channel(NOTIFY_CHANNEL_ID)

        if not channel:
            continue

        if last_video is None:
            last_video = "init"
            return

        new_video = YOUTUBE_LINK

        if new_video != last_video:
            last_video = new_video

            embed = discord.Embed(
                title="🚀 NUEVO VIDEO DISPONIBLE",
                description=f"🔥 KrMan subió video\n\n🎥 {YOUTUBE_LINK}",
                color=discord.Color.dark_red()
            )
            embed.set_footer(text="Kr Community")

            await channel.send(embed=embed)

# ===== COMANDO REDES =====
@bot.command()
async def redes(ctx):
    embed = discord.Embed(title="🌐 Redes de KrMan", color=discord.Color.blue())
    embed.add_field(name="YouTube", value=YOUTUBE_LINK, inline=False)
    embed.add_field(name="TikTok", value=TIKTOK_LINK, inline=False)

    await ctx.send(embed=embed)

# ===== RUN =====
bot.run(TOKEN)