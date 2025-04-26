from keep_alive import keep_alive
import discord
from discord.ext import commands
import re
import os
import asyncio
from dotenv import load_dotenv

# Cargar las variables de entorno del archivo .env
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

CANAL_RESTRINGIDO_ID = 1257783734682521677  # Cambia esto por tu ID real
YOUTUBE_REGEX = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/")
CANAL_NOTIFICACIONES_ID = 1327809148666122343  # ID del canal de notificaciones, cámbialo por el correcto
advertencia_cache = set()

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user} (ID: {bot.user.id})')

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    print(f"[DEBUG] Mensaje recibido de {message.author} en #{message.channel.name}: {message.content}")

    if message.channel.id == CANAL_RESTRINGIDO_ID:
        tiene_enlace_youtube = bool(YOUTUBE_REGEX.search(message.content))
        tiene_mp4 = any(archivo.filename.lower().endswith('.mp4') for archivo in message.attachments)

        if not tiene_enlace_youtube and not tiene_mp4:
            try:
                await message.delete()
                # Enviar un mensaje de advertencia al canal restringido
                await message.channel.send(
                    f"{message.author.mention} Solo se permiten enlaces de YouTube o archivos `.mp4`.",
                    delete_after=5
                )
            except discord.Forbidden:
                print("❌ No tengo permisos para borrar mensajes.")

            # Notificar en el canal de notificaciones
            canal_notificaciones = bot.get_channel(CANAL_NOTIFICACIONES_ID)
            if canal_notificaciones:
                aviso = await canal_notificaciones.send(
                    f"⚠️ {message.author.name} intentó enviar un enlace no permitido: {message.content}\n"
                    "Este enlace no es de YouTube y debe ser revisado. El mensaje estará disponible durante 20 minutos."
                )
                # Hacer que el mensaje dure 20 minutos
                await asyncio.sleep(1200)  # 20 minutos = 1200 segundos
                await aviso.delete()  # Borrar el mensaje después de 20 minutos

            return

        # Enviar advertencia si aún no se envió recientemente
        cache_key = f"{message.channel.id}-{message.author.id}"
        if cache_key not in advertencia_cache:
            advertencia_cache.add(cache_key)
            await message.channel.send(
                f"⚠️ {message.author.mention} Recuerda respetar las reglas y no compartir contenido explícito. "
                "De lo contrario, podrías recibir una sanción.",
                delete_after=10
            )
            await asyncio.sleep(30)
            advertencia_cache.discard(cache_key)

    await bot.process_commands(message)

# Ejecutar el bot con manejo de errores para evitar bloqueos por rate limit
async def run_bot():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ No se encontró el token. Asegúrate de definir DISCORD_TOKEN en los secrets.")
        return

    while True:
        try:
            await bot.start(token)
        except discord.HTTPException as e:
            if e.status == 429:
                print("⚠️ Rate limit detectado. Esperando 10 minutos...")
                await asyncio.sleep(600)
            else:
                raise
        except Exception as e:
            print(f"⚠️ Error inesperado: {e}")
            await asyncio.sleep(60)

# Mantener vivo el servidor web y ejecutar el bot
keep_alive()
asyncio.run(run_bot())