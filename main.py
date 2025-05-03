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

# Cargar variables de entorno (.env)
load_dotenv()

# Intents de Discord
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configuración de IDs
CANAL_RESTRINGIDO_ID = 1257783734682521677
CANAL_NOTIFICACIONES_ID = 1327809148666122343
MODERADORES_ROLE_ID = 1257783733562376365

# Regex para detectar enlaces
YOUTUBE_REGEX = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/")
TIKTOK_REGEX = re.compile(r"(https?://)?(www\.)?(tiktok\.com|vm\.tiktok\.com)/")

# Estado y cache
advertencia_cache = set()
mensajes_confirmados = {}
state_file = "video_state.json"
playlist_url = "https://www.youtube.com/playlist?list=PLnJiOIcjijbltly7vdQri_zigHLwbUKpv"

# Funciones para guardar y cargar estado
def save_state(last_video_index, time_started):
    with open(state_file, "w") as f:
        json.dump({"last_video_index": last_video_index, "time_started": time_started}, f)

def load_state():
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            return json.load(f)
    return None

# Vista interactiva para moderadores
class RevisarContenidoView(ui.View):
    def __init__(self, autor, mensaje_original, mensaje_id):
        super().__init__(timeout=None)
        self.autor = autor
        self.mensaje_original = mensaje_original
        self.mensaje_notificacion = None
        self.mensaje_id = mensaje_id

    @ui.button(label="✅ Confirmar", style=discord.ButtonStyle.success)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.mensaje_id in mensajes_confirmados:
            await interaction.response.send_message("❌ Este problema ya ha sido gestionado.", ephemeral=True)
            return

        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ No tienes permisos para usar esto.", ephemeral=True)
            return

        try:
            await self.autor.send(
                "⚠️ Has recibido una advertencia por compartir contenido no permitido en el servidor."
            )
        except discord.Forbidden:
            await interaction.response.send_message("❌ No se pudo enviar DM al usuario.", ephemeral=True)
        else:
            await interaction.response.send_message("✅ Advertencia enviada.", ephemeral=True)

        mensajes_confirmados[self.mensaje_id] = interaction.user.id

        await asyncio.sleep(300)
        if self.mensaje_notificacion:
            try:
                await self.mensaje_notificacion.delete()
            except discord.NotFound:
                pass

        canal_notificaciones = bot.get_channel(CANAL_NOTIFICACIONES_ID)
        if canal_notificaciones:
            confirmacion = await canal_notificaciones.send("✅ Acción completada por moderador.")
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

        if self.mensaje_notificacion:
            await self.mensaje_notificacion.delete()

        await interaction.response.send_message("🚫 Reporte ignorado.", ephemeral=True)

        canal_notificaciones = bot.get_channel(CANAL_NOTIFICACIONES_ID)
        if canal_notificaciones:
            confirmacion = await canal_notificaciones.send("✅ Acción completada por moderador.")
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
                    "🔍 **Botones del bot:**\n"
                    "✅ Confirmar: Advierte al usuario.\n"
                    "🚫 Ignorar: Descarta el reporte.\n"
                    "ℹ️ Info: Esta descripción."
                )
                await interaction.response.send_message("📩 Info enviada por DM.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ No se pudo enviar DM.", ephemeral=True)
        else:
            await interaction.response.send_message("🚫 Solo moderadores pueden usar este botón.", ephemeral=True)

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

        if not (tiene_enlace_youtube or tiene_enlace_tiktok or tiene_mp4):
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} Solo se permiten enlaces de YouTube, TikTok o archivos `.mp4`.",
                    delete_after=5
                )
            except discord.Forbidden:
                print("❌ No tengo permisos para borrar mensajes.")

            tiene_adjuntos = len(message.attachments) > 0
            tiene_enlace = "http" in message.content or "www." in message.content

            if tiene_adjuntos o tiene_enlace:
                canal_notificaciones = bot.get_channel(CANAL_NOTIFICACIONES_ID)
                if canal_notificaciones:
                    view = RevisarContenidoView(message.author, message.content, message.id)
                    aviso = await canal_notificaciones.send(
                        f"⚠️ {message.author.name} intentó enviar contenido no permitido:\n"
                        f"> {message.content}\n\n"
                        f"<@&{MODERADORES_ROLE_ID}> revisen esto:",
                        view=view
                    )
                    view.mensaje_notificacion = aviso
        return

    await bot.process_commands(message)

# Mensaje motivacional aleatorio
def obtener_mensaje_aleatorio():
    mensajes = [
        "Recordemos este gran cover, ¡Apoya a la idol Kori! 🎶",
        "¡Kori siempre te trae alegría! 😊",
        "Apoya a Kori, su música siempre nos inspira. 💖"
    ]
    return random.choice(mensajes)

# Subida automática de enlaces de videos (solo un video)
async def upload_videos():
    try:
        # Cargar el estado (último índice de video y tiempo de inicio)
        state = load_state()
        playlist = Playlist(playlist_url)

        if not state:
            state = {"last_video_index": 0, "time_started": time.time()}
            save_state(state["last_video_index"], state["time_started"])

        if time.time() - state["time_started"] > 14 * 24 * 60 * 60:
            state["last_video_index"] = 0
            state["time_started"] = time.time()

        # Asegúrate de que haya videos disponibles en la playlist
        if state["last_video_index"] >= len(playlist.video_urls):
            print("✅ Playlist completada. No hay videos para compartir.")
            return  # No más videos, terminar la ejecución

        # Obtener el canal de Discord donde se enviarán los videos
        canal_restringido = bot.get_channel(CANAL_RESTRINGIDO_ID)
        if not canal_restringido:
            print("❌ No se pudo acceder al canal.")
            return

        # Obtener la URL del video
        video_url = playlist.video_urls[state["last_video_index"]]
        yt = YouTube(video_url)
        mensaje_aleatorio = obtener_mensaje_aleatorio()

        # Esperar 10 segundos antes de enviar el video
        await asyncio.sleep(10)

        # Enviar el mensaje con el título del video y el enlace
        await canal_restringido.send(mensaje_aleatorio)
        await canal_restringido.send(f"🎥 **Nuevo video de Kori:** {yt.title}\n{yt.watch_url}")

        # Actualizar el índice y guardar el estado
        state["last_video_index"] += 1
        save_state(state["last_video_index"], state["time_started"])

    except Exception as e:
        print(f"⚠️ Error en upload_videos: {e}")

    # Solo compartir un video, no esperar entre videos
    print("✅ Video compartido. Finalizando la prueba.")

# Arranque del bot
async def run_bot():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Token no encontrado. Configura DISCORD_TOKEN en el entorno.")
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