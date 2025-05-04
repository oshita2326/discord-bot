from keep_alive import keep_alive
import discord
from discord.ext import commands
from discord import ui
import re
import os
import asyncio
from dotenv import load_dotenv
import time
import json
import random
import datetime

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

# Lista de enlaces disponibles para compartir
ENLACES = [
    "https://youtu.be/D5pGJLYK-ws?si=6WejtROV7lQEH0U6",
    "https://youtu.be/nE0YuQMHxu4?si=4sBuM2Xxc1zIvMy7",  # Reemplaza estos enlaces con los reales
    "https://youtu.be/ousRbTGDXmc?si=1t0zPyVszJU8Q5-l",
    "https://youtu.be/sp_ozq3pOIQ?si=RRr04wyuVf9ynfZB",
    "https://youtu.be/BcOhuoRYJBE?si=cjF5PqO3gy5G5tv9",
    "https://youtu.be/OES7zPn4dLo?si=ckRZVoADtoNEuNSC",
    "https://youtu.be/ChMBbtoyOo8?si=8weBzu2IZ2Ebfm-Q",
    "https://youtu.be/c4IE18IeJUc?si=13VhFsz03IEg1V38",
    "https://youtu.be/4-tjbCvEMfM?si=2yoo1PT8aCQ7jek-",
    "https://youtu.be/Bbo7TT1yh0U?si=5gyaQZAKKJfug6Z9",
    "https://youtu.be/Ojj4vPRBUQw?si=b8jTbfXU-M8ogofW",
    "https://youtu.be/IeljL-b4naw?si=SS9A5HxZQeGhaTe7",
    "https://youtu.be/V1ej8iSjdyU?si=939KIxBaKhkZNO6g",
    "https://youtu.be/6zwJVs9qsVg?si=-gK0QJywaDu8IR5X",
    "https://youtu.be/iups8Yq1voU?si=5LPPGg0ajXhVaAN-",
    "https://youtu.be/7LtrBjrzw-4?si=ioY4nYyegSBf9F_z",
    "https://youtu.be/JFcYlwlV2lo?si=6RC56-cSO0KTUzkA",
    "https://youtu.be/kZcOa_8PsjM?si=zCYhzVBJsRIB4tYC",
    "https://youtu.be/2UfziTwxbBA?si=1sMYNaJzDKasGvOY",
    "https://youtu.be/PntuoKkDR4c?si=J6C3tQTHFwzaPUmI",
    "https://youtu.be/baozXQFVfG8?si=Z_dWm3VUFTxzG-PX",
    "https://youtu.be/lcGuFZpCZR4?si=RIxz9q9_Vrv0czZv"
]
ENLACES_ORIGINALES = ENLACES.copy()
# Estado del bot (cuando se tomará el descanso de una semana)
estado = {"ultimo_enlace": None, "fecha_descanso": None, "fecha_ultimo_envio": None}

# Cargar estado desde un archivo
def cargar_estado():
    global estado
    try:
        with open('estado.json', 'r') as f:
            estado = json.load(f)
    except FileNotFoundError:
        print("⚠️ No se encontró el archivo de estado. Se creará uno nuevo.")

# Guardar estado en un archivo
def guardar_estado():
    global estado
    with open('estado.json', 'w') as f:
        json.dump(estado, f)

# Mensaje motivacional aleatorio
def obtener_mensaje_aleatorio():
    mensajes = [
        "Recordemos este gran cover, ¡Apoya a la idol Kori! 🎶",
        "¡Kori siempre te trae alegría! 😊",
        "Apoya a Kori, su música siempre nos inspira. 💖"
    ]
    return random.choice(mensajes)

# Enviar un enlace aleatorio una vez al día
async def enviar_video_una_vez():
    # Cargar el estado
    cargar_estado()

    # Verificar si el bot está en pausa
    if estado["fecha_descanso"]:
        fecha_descanso = datetime.datetime.fromisoformat(estado["fecha_descanso"])
        if datetime.datetime.now() < fecha_descanso:
            print(f"🛑 El bot está en pausa hasta {fecha_descanso.strftime('%Y-%m-%d %H:%M:%S')}.")
            return

        # Si ha pasado la pausa, reiniciar el proceso
        print("✅ Pausa terminada, el bot volverá a compartir enlaces.")
        estado["fecha_descanso"] = None  # Terminar la pausa
        ENLACES.clear()
        ENLACES.extend(ENLACES_ORIGINALES)
        guardar_estado()

    # Verificar si ya ha pasado el día para enviar un nuevo enlace
    if estado["fecha_ultimo_envio"] == str(datetime.date.today()):
        print("🛑 Ya se ha enviado un enlace hoy.")
        return

    # Si no hay enlaces disponibles, hacer una pausa de una semana
    if len(ENLACES) == 0:
        estado["fecha_descanso"] = (datetime.datetime.now() + datetime.timedelta(weeks=1)).isoformat()
        guardar_estado()
        print("⚠️ Los enlaces se han agotado. El bot entrará en pausa por una semana.")
        return

    # Elegir un enlace aleatorio
    enlace = random.choice(ENLACES)
    mensaje = obtener_mensaje_aleatorio()

    canal = await bot.fetch_channel(CANAL_RESTRINGIDO_ID)
    if canal:
        await asyncio.sleep(15)  # Esperar 15 segundos
        await canal.send(mensaje)
        await canal.send(f"🎥 **Video destacado:**\n{enlace}")
        print("✅ Video enviado con éxito.")

        # Eliminar el enlace de la lista
        ENLACES.remove(enlace)

        # Guardar el estado con el enlace que se acaba de enviar y la fecha actual
        estado["ultimo_enlace"] = enlace
        estado["fecha_ultimo_envio"] = str(datetime.date.today())  # Guardar la fecha del último envío
        guardar_estado()
    else:
        print("❌ No se encontró el canal.")

mensajes_confirmados = {}

class RevisarContenidoView(ui.View):
    def __init__(self, autor, mensaje_original, mensaje_id):
        super().__init__(timeout=None)
        self.autor = autor
        self.mensaje_original = mensaje_original
        self.mensaje_notificacion = None
        self.mensaje_id = mensaje_id

    @ui.button(label="✅ Confirmar", style=discord.ButtonStyle.success)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar si ya fue gestionado
        if self.mensaje_id in mensajes_confirmados:
            await interaction.response.send_message("❌ Este problema ya fue gestionado por otro moderador.", ephemeral=True)
            return

        # Verificar permisos del moderador
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
            return

        try:
            # Intentar enviar la advertencia por DM
            await self.autor.send("⚠️ Has recibido una advertencia por compartir contenido no permitido.")
        except discord.Forbidden:
            await interaction.response.send_message("❌ No se pudo enviar DM al usuario.", ephemeral=True)
        else:
            await interaction.response.send_message("✅ Advertencia enviada.", ephemeral=True)
            print(f"✔️ Advertencia enviada a {self.autor.name}.")

        # Registrar la acción del moderador
        mensajes_confirmados[self.mensaje_id] = interaction.user.id

        # Esperar 5 minutos antes de borrar la notificación
        await asyncio.sleep(300)
        if self.mensaje_notificacion:
            try:
                await self.mensaje_notificacion.delete()
            except discord.NotFound:
                pass

        # Enviar confirmación en el canal de notificaciones
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
            await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
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
                    "🔍 **Botones del bot:**\n✅ Confirmar: Advierte al usuario.\n🚫 Ignorar: Descarta el reporte.\nℹ️ Info: Muestra esta ayuda."
                )
                await interaction.response.send_message("📩 Info enviada por DM.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ No se pudo enviar DM.", ephemeral=True)
        else:
            await interaction.response.send_message("🚫 Solo moderadores pueden usar este botón.", ephemeral=True)
async def tarea_diaria():
    await bot.wait_until_ready()
    await enviar_video_una_vez()
    while not bot.is_closed():
        await enviar_video_una_vez()
        await asyncio.sleep(86400)  # Espera de 24 horas
# Configuración de los eventos del bot
@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user} (ID: {bot.user.id})')
    bot.loop.create_task(tarea_diaria())  # Ejecuta la tarea diaria automáticamente

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

            if tiene_adjuntos or tiene_enlace:
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

# Función para ejecutar el bot
async def run_bot():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ No se encontró el token. Asegúrate de definir DISCORD_TOKEN en Render (secrets).")
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
