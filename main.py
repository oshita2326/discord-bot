from keep_alive import keep_alive
import discord
from discord.ext import commands
from discord import ui
import re
import os
import asyncio
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configuración de IDs
CANAL_RESTRINGIDO_ID = 1257783734682521677
CANAL_NOTIFICACIONES_ID = 1327809148666122343
MODERADORES_ROLE_ID = 1257783733562376365  # ID del rol de moderadores

# Regex para validar contenido permitido
YOUTUBE_REGEX = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/")
TIKTOK_REGEX = re.compile(r"(https?://)?(www\.)?(tiktok\.com|vm\.tiktok\.com)/")

advertencia_cache = set()

# Vista con botones de Confirmar / Ignorar
class RevisarContenidoView(ui.View):
    def __init__(self, autor, mensaje_original):
        super().__init__(timeout=None)
        self.autor = autor
        self.mensaje_original = mensaje_original
        self.mensaje_notificacion = None

    @ui.button(label="✅ Confirmar", style=discord.ButtonStyle.success)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ No tienes permisos para usar esto.", ephemeral=True)
            return

        try:
            await self.autor.send(
                f"⚠️ Has recibido una advertencia por compartir contenido no permitido en el servidor. Por favor revisa las reglas."
            )
        except discord.Forbidden:
            await interaction.response.send_message("❌ No se pudo enviar DM al usuario.", ephemeral=True)
        else:
            await interaction.response.send_message("✅ Advertencia enviada al usuario.", ephemeral=True)

        await asyncio.sleep(600)  # 10 minutos
        try:
            if self.mensaje_notificacion:
                await self.mensaje_notificacion.delete()
        except discord.NotFound:
            pass

    @ui.button(label="🚫 Ignorar", style=discord.ButtonStyle.danger)
    async def ignorar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ No tienes permisos para usar esto.", ephemeral=True)
            return

        await interaction.response.send_message("🚫 Reporte ignorado. El mensaje será eliminado en 10 minutos.", ephemeral=True)
        await asyncio.sleep(600)
        try:
            if self.mensaje_notificacion:
                await self.mensaje_notificacion.delete()
        except discord.NotFound:
            pass


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
        tiene_imagen = any(archivo.filename.lower().endswith(('.jpg', '.jpeg', '.png')) for archivo in message.attachments)

        if not (tiene_enlace_youtube or tiene_enlace_tiktok or tiene_mp4 or tiene_imagen):
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} Solo se permiten enlaces de YouTube, TikTok, archivos `.mp4` o imágenes válidas.",
                    delete_after=5
                )
            except discord.Forbidden:
                print("❌ No tengo permisos para borrar mensajes.")

            canal_notificaciones = bot.get_channel(CANAL_NOTIFICACIONES_ID)
            if canal_notificaciones:
                view = RevisarContenidoView(message.author, message.content)
                aviso = await canal_notificaciones.send(
                    f"⚠️ {message.author.name} intentó enviar contenido no permitido en el canal restringido:\n"
                    f"> {message.content}\n\n"
                    f"<@&{MODERADORES_ROLE_ID}> revisen este contenido y actúen con los botones abajo.",
                    view=view
                )
                view.mensaje_notificacion = aviso

            return

        # Envío de advertencia leve si el contenido es válido
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


# Función para ejecutar el bot
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

# Inicia el bot
keep_alive()
asyncio.run(run_bot())