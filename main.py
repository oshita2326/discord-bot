from keep_alive import keep_alive
import discord
from discord.ext import commands
from discord import ui
import re
import os
import asyncio
from dotenv import load_dotenv
from pytube import YouTube, Playlist
import time
import json
import random

# Cargar .env
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# IDs de configuración
CANAL_RESTRINGIDO_ID = 1257783734682521677  # Canal donde se suben los videos
CANAL_NOTIFICACIONES_ID = 1327809148666122343
MODERADORES_ROLE_ID = 1257783733562376365

# Regex para validar enlaces
YOUTUBE_REGEX = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/")
TIKTOK_REGEX = re.compile(r"(https?://)?(www\.)?(tiktok\.com|vm\.tiktok\.com)/")

advertencia_cache = set()

# Diccionario para registrar los mensajes que ya fueron gestionados
mensajes_confirmados = {}

# Diccionario para almacenamiento del estado de la playlist
state_file = "video_state.json"

# Playlist URL (tu enlace específico)
playlist_url = "https://www.youtube.com/playlist?list=PLnJiOIcjijbltly7vdQri_zigHLwbUKpv"

# Función para guardar el estado de la playlist
def save_state(last_video_index, time_started):
    with open(state_file, "w") as f:
        json.dump({"last_video_index": last_video_index, "time_started": time_started}, f)

# Función para cargar el estado de la playlist
def load_state():
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            return json.load(f)
    return None

class RevisarContenidoView(ui.View):
    def __init__(self, autor, mensaje_original, mensaje_id):
        super().__init__(timeout=None)
        self.autor = autor
        self.mensaje_original = mensaje_original
        self.mensaje_notificacion = None
        self.mensaje_id = mensaje_id  # ID del mensaje original

    @ui.button(label="✅ Confirmar", style=discord.ButtonStyle.success)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verifica si el mensaje ya fue confirmado
        if self.mensaje_id in mensajes_confirmados:
            await interaction.response.send_message("❌ Este problema ya ha sido gestionado por otro moderador.", ephemeral=True)
            return

        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ No tienes permisos para usar esto.", ephemeral=True)
            return

        try:
            await self.autor.send(
                "⚠️ Has recibido una advertencia por compartir contenido no permitido en el servidor. Por favor revisa las reglas."
            )
        except discord.Forbidden:
            await interaction.response.send_message("❌ No se pudo enviar DM al usuario.", ephemeral=True)
        else:
            await interaction.response.send_message("✅ Advertencia enviada al usuario.", ephemeral=True)

        # Marcar el mensaje como confirmado
        mensajes_confirmados[self.mensaje_id] = interaction.user.id

        await asyncio.sleep(300)  # Esperar 5 minutos
        try:
            if self.mensaje_notificacion:
                await self.mensaje_notificacion.delete()
        except discord.NotFound:
            pass

        canal_notificaciones = bot.get_channel(CANAL_NOTIFICACIONES_ID)
        if canal_notificaciones:
            confirmacion = await canal_notificaciones.send("✅ Buen trabajo, moderador. Acción completada.")
            await asyncio.sleep(15)
            try:
                await confirmacion.delete()
            except discord.NotFound:
                pass

    @ui.button(label="🚫 Ignorar", style=discord.ButtonStyle.danger)
    async def ignorar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ No tienes permisos para usar esto.", ephemeral=True)
            return

        # Eliminar inmediatamente el mensaje de notificación cuando se hace clic en "Ignorar"
        if self.mensaje_notificacion:
            await self.mensaje_notificacion.delete()

        await interaction.response.send_message("🚫 Reporte ignorado. Mensaje eliminado inmediatamente.", ephemeral=True)

        canal_notificaciones = bot.get_channel(CANAL_NOTIFICACIONES_ID)
        if canal_notificaciones:
            confirmacion = await canal_notificaciones.send("✅ Buen trabajo, moderador. Acción completada.")
            await asyncio.sleep(15)
            try:
                await confirmacion.delete()
            except discord.NotFound:
                pass

    @ui.button(label="ℹ️ Info", style=discord.ButtonStyle.secondary)
    async def info(self, interaction: discord.Interaction, button: discord.ui.Button):
        if any(role.id == MODERADORES_ROLE_ID for role in interaction.user.roles):
            try:
                await interaction.user.send(
                    "🔍 **Información sobre los botones del bot:**\n\n"
                    "✅ **Confirmar**: Envía una advertencia por DM al usuario que intentó compartir contenido no permitido.\n"
                    "🚫 **Ignorar**: Descarta el reporte y borra el mensaje de notificación sin tomar medidas.\n"
                    "ℹ️ **Info**: Envía esta descripción a ti como moderador para recordar su función."
                )
                await interaction.response.send_message("📩 Te he enviado la información por DM.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ No pude enviarte un mensaje directo. Asegúrate de tenerlos activados.", ephemeral=True)
        else:
            await interaction.response.send_message("🚫 Solo los moderadores pueden usar este botón.", ephemeral=True)


@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user} (ID: {bot.user.id})')


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == CANAL_RESTRINGIDO_ID:
        tiene_enlace_youtube = bool(YOUTUBE_REGEX.search(message.content))
        tiene_enlace_tiktok = bool(TIKTOK_REGEX.search(message.content))
        tiene_mp4 = any(archivo.filename.lower().endswith('.mp4') for archivo in message.attachments)
        
        # YA NO se permite imagen, así que no evaluamos "tiene_imagen"

        if not (tiene_enlace_youtube or tiene_enlace_tiktok or tiene_mp4):
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} Solo se permiten enlaces de YouTube, TikTok o archivos `.mp4`.",
                    delete_after=5
                )
            except discord.Forbidden:
                print("❌ No tengo permisos para borrar mensajes.")

            # Notificar a moderadores si el mensaje tiene archivos o enlaces
            tiene_adjuntos = len(message.attachments) > 0
            tiene_enlace = "http" in message.content or "www." in message.content

            if tiene_adjuntos or tiene_enlace:
                canal_notificaciones = bot.get_channel(CANAL_NOTIFICACIONES_ID)
                if canal_notificaciones:
                    view = RevisarContenidoView(message.author, message.content, message.id)
                    aviso = await canal_notificaciones.send(
                        f"⚠️ {message.author.name} intentó enviar contenido no permitido en el canal restringido:\n"
                        f"> {message.content}\n\n"
                        f"<@&{MODERADORES_ROLE_ID}> revisen este contenido y actúen con los botones abajo.",
                        view=view
                    )
                    view.mensaje_notificacion = aviso
        return
        # Advertencia leve si es válido
        cache_key = f"{message.channel.id}-{message.author.id}"
        if cache_key not in advertencia_cache:
            advertencia_cache.add(cache_key)
            await message.channel.send(
                f"⚠️ {message.author.mention} Recuerda respetar las reglas y no compartir contenido explícito.",
                delete_after=10
            )
            await asyncio.sleep(30)
            advertencia_cache.discard(cache_key)

    await bot.process_commands(message)


# Función para obtener un mensaje de apoyo aleatorio
def obtener_mensaje_aleatorio():
    mensajes = [
        "Recordemos este gran cover, ¡Apoya a la idol Kori! 🎶",
        "¡Kori siempre te trae alegría! 😊",
        "Apoya a Kori, su música siempre nos inspira. 💖"
    ]
    return random.choice(mensajes)


# Función para subir los videos de la playlist
async def upload_videos():
    state = load_state()

    # Obtenemos la playlist
    playlist = Playlist(playlist_url)
    
    # Si no hay estado guardado, comenzamos desde el primer video
    if not state:
        state = {"last_video_index": 0, "time_started": time.time()}
        save_state(state["last_video_index"], state["time_started"])

    # Verificamos si pasaron 2 semanas desde la última subida
    if time.time() - state["time_started"] > 14 * 24 * 60 * 60:  # 2 semanas en segundos
        state["last_video_index"] = 0  # Volver al inicio de la playlist
        state["time_started"] = time.time()  # Resetear el tiempo

    canal_restringido = bot.get_channel(CANAL_RESTRINGIDO_ID)  # Obtener el canal restringido
    
    # Subir los videos
    for i in range(state["last_video_index"], len(playlist.video_urls)):
        try:
            yt = YouTube(playlist.video_urls[i])
            video_stream = yt.streams.filter(file_extension="mp4").first()
            print(f"Subiendo el video: {yt.title}")
            
            # Subir el video al canal restringido
            mensaje_aleatorio = obtener_mensaje_aleatorio()
            await canal_restringido.send(mensaje_aleatorio)
            await canal_restringido.send(f"🎥 Subiendo el video: {yt.title}")

            # Espera un día entre cada subida
            await asyncio.sleep(86400)  # 86400 segundos = 24 horas

            # Actualizar el índice del video y guardar el estado
            state["last_video_index"] = i + 1
            save_state(state["last_video_index"], state["time_started"])

        except Exception as e:
            print(f"Error al intentar subir el video: {e}")
            continue

    print("Playlist terminada. El bot esperará 2 semanas antes de reiniciar.")
    # Guardar el estado después de terminar la playlist
    save_state(state["last_video_index"], state["time_started"])

# Ejecutar bot
async def run_bot():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ No se encontró el token. Asegúrate de definir DISCORD_TOKEN en Render.")
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

keep_alive()

# Ejecutar la subida de videos y el bot en paralelo
async def main():
    # Iniciar la tarea de subida de videos
    asyncio.create_task(upload_videos())
    # Ejecutar el bot
    await run_bot()

# Iniciar el servidor web y correr el bucle principal
if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())

# Ejecutar la subida de videos en paralelo con el bot
asyncio.create_task(upload_videos())  # Subir videos desde la playlist
asyncio.run(run_bot())  # Ejecutar el bot de Discord
