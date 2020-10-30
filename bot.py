import discord
from discord.ext import commands, tasks
from discord.voice_client import VoiceClient
import youtube_dl
import asyncio
from random import choice
from urllib import parse, request
import re


youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    #'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

#prefijo para llamar los comandos
client = commands.Bot(command_prefix='!')

status = ['Escuchando', 'Hey there!', 'Sleeping!']
queue = []

@client.event
async def on_ready():
    change_status.start()
    print('Bot is online!')

@client.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.channels, name='general')
    await channel.send(f'Bienvenido {member.mention}!  Listo para escuchar? escribe `!help` para ver los comandos!')
        
@client.command(name='ping', help='Este comando retorna la latencia')
async def ping(ctx):
    await ctx.send(f'**Pong!** Latency: {round(client.latency * 1000)}ms')

@client.command(name='hello', help='Este comando muestra un mensaje de ramdon de bienvenida')
async def hello(ctx):
    responses = ['Que xopa!', 'Hola!', 'Hello, how are you?','Wenas!']
    await ctx.send(choice(responses))

@client.command(name='credits', help='Este comando retorna los creditos')
async def credits(ctx):
    await ctx.send('Made by `Jonathan Guaynora`')

@client.command(name='creditz', help='Este comando retorna los verdaderos creditos')
async def creditz(ctx):
    await ctx.send('**Nadie mas, solo yo :3!**')

@client.command(name='join', help='comando para unirse al canal de voz')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("No estas conectado en un canal de voz")
        return
    
    else:
        channel = ctx.message.author.voice.channel

    await channel.connect()

@client.command(name='queue', help='Este comando es para agregar canciones a la cola')
async def queue_(ctx, *,url):
    global queue
    query_string = parse.urlencode({'search_query': url})

    html_content = request.urlopen('http://www.youtube.com/results?' + query_string)
    search_results = re.findall( r"watch\?v=(\S{11})", html_content.read().decode())
    print(search_results)
    await ctx.send('https://www.youtube.com/watch?v=' + search_results[0])
    url = ('https://www.youtube.com/watch?v=' + search_results[0])

    queue.append(url)
    await ctx.send(f'`{url}` added to queue!')

@client.command(name='remove', help='Este comando elimina un elemento de la lista')
async def remove(ctx, number):
    global queue

    try:
        del(queue[int(number)])
        await ctx.send(f'Your queue is now `{queue}!`')
    
    except:
        await ctx.send('Tu cola esta **vacia** o el indice esta **fuera de rango**')
        
@client.command(name='play', help='Este comando reproduce las canciones')
async def play(ctx):
    global queue

    server = ctx.message.guild
    voice_channel = server.voice_client

    async with ctx.typing():
        player = await YTDLSource.from_url(queue[0], loop=client.loop)
        voice_channel.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
        del(queue[0])
    await ctx.send('**Now playing:** {}'.format(player.title))

@client.command(name='stream', help='Este comando stremea las canciones')
async def stream(ctx):
    global queue

    server = ctx.message.guild
    voice_channel = server.voice_client

    async with ctx.typing():
        player = await YTDLSource.from_url(queue[0], loop=client.loop, stream= True)
        voice_channel.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
        del(queue[0])
    await ctx.send('**Now playing:** {}'.format(player.title))

@client.command(name='pause', help='Este comando pausa las canciones')
async def pause(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client

    voice_channel.pause()

@client.command(name='resume', help='Este comando reanuda las canciones!')
async def resume(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client

    voice_channel.resume()

@client.command(name='view', help='Este comando muestra tu queue')
async def view(ctx):
    await ctx.send(f'Your queue is now `{queue}!`')

@client.command(name='leave', help='Este comando hace que el bot abandone el canal de voz')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    await voice_client.disconnect()

@client.command(name='stop', help='Este comando detiene la cancion!')
async def stop(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client

    voice_channel.stop()

@tasks.loop(seconds=20)
async def change_status():
    await client.change_presence(activity=discord.Game(choice(status)))

client.run('Token')
