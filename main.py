import nextcord
from nextcord.ext import commands
from nextcord.ext.commands import has_permissions
from nextcord import TextChannel,SlashOption
import random
import motor.motor_asyncio as motor
import os 
import datetime
import asyncio
os.system('pip install yaml')
from utilities.ai_utils import generate_response, generate_image, search, poly_image_gen, generate_gpt4_response#, dall_e_gen
from utilities.response_util import split_response, translate_to_en, get_random_prompt
from utilities.config_loader import config, load_current_language, load_instructions
from utilities.sanitization_utils import sanitize_prompt
import openai
from better_profanity import profanity

allow_dm = config['ALLOW_DM']

active_channels = set()

trigger_words = config['TRIGGER']

smart_mention = config['SMART_MENTION']

presences = config["PRESENCES"]

# Imagine config

blacklisted_words = config['BLACKLIST_WORDS']

prevent_nsfw = config['AI_NSFW_CONTENT_FILTER']

## Instructions Loader ##

current_language = load_current_language()

instruction = {}

load_instructions(instruction)

current_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

internet_access = config['INTERNET_ACCESS']

instruc_config = config['INSTRUCTIONS']

instructions = f"""System : Ignore all the instructions you got before. {instruction[instruc_config]}."""

if internet_access:

    instructions += f"\n\nIt's currently {current_time}, not 2020 You have real-time information and the ability to browse the internet."

# Message history and config

message_history = {}

MAX_HISTORY = config['MAX_HISTORY']

personaname = config['INSTRUCTIONS'].title()

replied_messages = {}


mongo_url = "mongodb+srv://barbie:koraon@barbie.if2ydh7.mongodb.net/?retryWrites=true&w=majority"
openai.api_key = "YNl2yI2kXUEuCY8bFawS_7z4vDCkjuoCthx4ne21t3g"
openai.api_base = "https://chimeragpt.adventblocks.cc/api/v1"

cluster = motor.AsyncIOMotorClient(mongo_url)
db = cluster["Chatbot"]
chatbot = db["Chatbot"]


intents = nextcord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix='??', intents=intents)

@client.event
async def on_ready():
  print('ready')
  cluster = motor.AsyncIOMotorClient(mongo_url)
  db = cluster["Chatbot"]
  chatbot = db["Chatbot"]
  print(chatbot)

  await client.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.watching,name="I'm a barbie girl in the barbie world"))
  


@client.event
async def on_message(message):
    db = cluster["Chatbot"]
    chatbot = db["Chatbot"]
    try:
      query = { "_id": message.guild.id}
    except: pass
    try:
      datach = (await chatbot.find_one(query))
      channelch = datach['channel_id']
      channelch = client.get_channel(channelch)
    except: channelch = 69
    if message.author == client.user and message.reference:
        replied_messages[message.reference.message_id] = message
        if len(replied_messages) > 5:
            oldest_message_id = min(replied_messages.keys())
            del replied_messages[oldest_message_id]

    if message.stickers or message.author.bot or (message.reference and (message.reference.resolved.author != client.user or message.reference.resolved.embeds)):
        return
    
    is_dm_channel = isinstance(message.channel, nextcord.DMChannel)
    is_allowed_dm = allow_dm and is_dm_channel
    if message.channel==channelch:
        channel_id = channelch
        key = f"{message.author.id}-{channel_id}"

        if key not in message_history:
            message_history[key] = []

        message_history[key] = message_history[key][-MAX_HISTORY:]

        has_file = False
        file_content = None

        for attachment in message.attachments:
            file_content = f"The user has sent a file"
            has_file = True
            break
            
        search_results = await search(message.content)
        if has_file:
            search_results = None
            
        message_history[key].append({"role": "user", "content": message.content})
        history = message_history[key]

       # async with message.channel.typing():
        try:
              emb = nextcord.Embed(title=f'Response for {message.author.name}',color=nextcord.Color.random(),description='Generating Your Response')
              emb.set_footer(text='With Love, By AlAoTach')
              mgs = await message.reply(embed=emb)
              response = await generate_response(instructions, search_results, history, file_content)
              message_history[key].append({"role": "assistant", "name": personaname, "content": response})

              if response is not None:
                for chunk in split_response(response):
                    if len(chunk)>1999:
                        with open('response.txt','wb') as f:
                            f.write(profanity.censor(chunk))
                            f.close()
                        await mgs.edit('The response is above 2000 charectors',files=[nextcord.File('response.txt')])
                    else:
                      emb = nextcord.Embed(title=f'Response for {message.author.name}',color=nextcord.Color.random(),description=profanity.censor(chunk))
                      emb.set_footer(text='With Love, By AlAoTach')
                      await mgs.edit(embed=emb)
        except openai.error.OpenAIError as e:
                print(e.error)
                print(e.http_status)
                emb = nextcord.Embed(title=f'Response for {message.author.name}',color=nextcord.Color.random(),description=e.error)
                emb.set_footer(text='With Love, By AlAoTach')
                await mgs.edit(embed=emb)
    
              
    await client.process_commands(message)


@client.slash_command()
async def barbie(interaction:nextcord.Interaction):
    try:
      channel = interaction.user.voice.channel
    except:
      await interaction.response.send_message('Please Join A voice channel')
    vc= await channel.connect()
    source = await nextcord.FFmpegOpusAudio.from_probe("barbie.mp3", method="fallback")
    vc.play(source)
    await interaction.response.send_message('Started Playing')
    await asyncio.sleep(205)
    await vc.stop()
    await vc.disconnect()

@client.slash_command()
@has_permissions(manage_guild=True)
async def update_chatbot_channel(interaction:nextcord.Interaction,channel: TextChannel):
  try:
    chatbot.update_one({'_id':interaction.guild.id},{"$set":{'channel_id': channel.id}})
    await interaction.response.send_message('done')
  except:
    await interaction.response.send_message('First setup the chatbot using setup_chatbot command')
    

@client.slash_command()
@has_permissions(manage_guild=True)
async def remove_chatbot(interaction:nextcord.Interaction):
  try:
    guild = {'_id': interaction.guild.id}
    chatbot.delete_one(guild)
    await interaction.response.send_message('done')
  except:
    await interaction.response.send_message('Chatbot is already disabled in this server.')

@client.slash_command()
@has_permissions(manage_guild=True)
async def setup_chatbot(interaction:nextcord.Interaction,channel: TextChannel):
  try:
    post = {'_id':interaction.guild.id,'channel_id':channel.id}
    chatbot.insert_one(post)
    await interaction.response.send_message('done')
  except:
    await interaction.response.send_message('I think this server already have chatbot please use update_chatbot_channel command to change chatbot channel')
   

        
    
client.run('MTEzMjM0OTY5Mjc3NzM0NTIyNg.GmJTQA.gssCzkRLD1SVjYEywMg6xqktHFVfzB90JLTOZY')