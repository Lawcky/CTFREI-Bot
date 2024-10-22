import discord
import json
from bot_functions import extract_ctf_data, search_ctf_data, create_private_channel, get_category_by_id, get_channel_by_name, reply_message, search_event_data, send_event_info, api_call
from discord.ext import commands
from discord.utils import get
import time
from os import path as p

# Load configuration file
with open('conf.json') as conf_file:
    conf = json.load(conf_file)
# Extract token from JSON
TOKEN = conf['DISCORD_TOKEN'] # discord token
DISCORD_GUILD_ID = conf['DISCORD_GUILD_ID']

UPCOMING_CTFTIME_FILE = conf['UPCOMING_CTFTIME_FILE']
ONGOING_CTFTIME_FILE = conf['ONGOING_CTFTIME_FILE']
EVENT_LOG_FILE = conf['EVENT_LOG_FILE']
last_refresh_upcoming = 0 #initiate at 0 
last_refresh_ongoing = 0 #initiate at 0 

WEIGHT_RANGE = conf['WEIGHT_RANGE'] # the spread for the research by weight
MAX_EVENT_LIMIT = conf['MAX_EVENT_LIMIT'] - 1 # limit the maximum amount of event to be printed out by the bot in a single message (mostly to avoid crashing) 

CTF_CHANNEL_CATEGORY_ID = conf['CTF_CHANNEL_CATEGORY_ID']# the list of all the categories the bot can modify (one per server)
CTF_JOIN_CHANNEL = conf['CTF_JOIN_CHANNEL'] # the list of all the channels in which the bot will send messages to join CTFs (one per server)



# Set up the bot with proper intents
intents = discord.Intents.default()
intents.messages = True 
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')
#
#   CTFTIME RELATED COMMANDS
#
#list all the CTF competitions that are upcoming based on the CTFTIME data
@bot.command(name="upcoming")
async def upcoming_ctf(ctx, max_events: int = MAX_EVENT_LIMIT):
    global last_refresh_upcoming, UPCOMING_CTFTIME_FILE
    
    max_events -= 1 # when asked for 5 will print 5 instead of 6
    with open(UPCOMING_CTFTIME_FILE) as data_file:
        events = json.load(data_file)

    embeded_message = discord.Embed(
            title="Upcoming CTF Events",  # Title of the embed
            description="Here are the lists of known upcoming CTF events on CTFTIME",  # Description of the embed
            color=discord.Color.blue()  # Color of the side bar (you can change the color)
        )


    count = 0 # variable to limit the amount of output per message (discord limits)
    for event in events: 
        if (event['location'] == ''):

            event_info = f"Weight: {event['weight']} | {event['format']}" # format for the output of the CTF upcoming lists for each event
            embeded_message.add_field(name=event['title'], value=event_info, inline=False)
            
            count += 1

        if (count > max_events):
            break
    
    embeded_message.set_footer(text="For more event use /upcoming {number}, or you can learn more about a specific event using /search {name of the event}")

    await ctx.send(embed=embeded_message)

# works well
@bot.command(name="refresh")
async def refresh_data(ctx):

    data = api_call("https://ctftime.org/api/v1/events/?limit=100", UPCOMING_CTFTIME_FILE)

    if data is not None:
        await ctx.send(f"events have been updated up to {str(data[-1]['finish'])[:10:]}")
    else: 
        await ctx.send(f"Error updating.")

#list all the CTF competitions that are currently running # to be changed but not urgent
@bot.command(name="ongoing")
async def ongoing_ctf(ctx):
    global ONGOING_CTFTIME_FILE

    events = await extract_ctf_data("https://ctftime.org/event/list/?now=true", ONGOING_CTFTIME_FILE) #deprecated in the other functions but whatever works fine for this

    embeded_message = discord.Embed(
            title="Ongoing CTF Events",  # Title of the embed
            description="Here are the lists of known ongoing CTF events in CTFTIME",  # Description of the embed
            color=discord.Color.green()  # Color of the side bar (you can change the color)
        )

    count = 0 # variable to limit the amount of output per message (discord limits to avoid crash)
    for event in events: 
        event_info = f"Weight: {event['weight']} | location -> {event['location']} | {event['format']}\n{event['link']}" # format for the output of the CTF upcoming lists for each event
        embeded_message.add_field(name=event['name'], value=event_info, inline=False)
        
        count += 1

        if (count > MAX_EVENT_LIMIT):
            break
    
    embeded_message.set_footer(text="you can learn more about a specific event using /search {name of the event}")

    await ctx.send(embed=embeded_message)

#will read both json files and look for a corresponding CTF with either the right weight or name
@bot.command(name="search")
async def search_json(ctx, query: str = None):

    if (query == None):
        await ctx.send('Please add a query')
        return None

    # check if files exists and arent empty, if either is true it'll start the parsing of the site
    if (not p.isfile(UPCOMING_CTFTIME_FILE) or p.getsize(UPCOMING_CTFTIME_FILE) == 0):
        await  api_call("https://ctftime.org/api/v1/events/?limit=100", UPCOMING_CTFTIME_FILE)
    # if (not p.isfile(ONGOING_CTFTIME_FILE) or p.getsize(ONGOING_CTFTIME_FILE) == 0): #(Optionnal) to be able to search through already running CTFs
    #     await extract_ctf_data("https://ctftime.org/event/list/?now=true", ONGOING_CTFTIME_FILE)

    matches = await search_ctf_data(UPCOMING_CTFTIME_FILE, query, WEIGHT_RANGE)
    #add msg here
    # matches += await search_ctf_data(ONGOING_CTFTIME_FILE, query, WEIGHT_RANGE) # uncomment this if you activated the search through already running CTFs
    # add msg here

    for match in matches: # too long makes it crash
        print(match)
        message = f"**{match['title']}** | {match['weight']} ---> *{match['url']}*\n"
        await ctx.send(message)
    if not matches:
       await ctx.send("no event could be found.\nRemember: \n-if there are spaces write between \" \".\n-search command does not look for currently running CTFs by default.\n for more info on a specific CTF go on the related channel and enter /info.") 


#  CHANNEL & ROLE MANAGEMENT RELATED COMMANDS
#
# to be added
@bot.command(name="add")
async def add(ctx):
    await ctx.send("not yet implemented, this will allow to add CTF events that are not inside the CTFtime data.")

# quickly add a channel, role, and data about a specified CTF event, the event NEEDS to be able to be found by the /search endpoint, and the other string you'll give will be used
# to create the role and the channel's name (the channels adds a "🚩-" before the string)
@bot.command(name="quickadd")
async def add_reaction_and_channel(ctx, role_name: str, ctf_name: str):

    global CTF_CHANNEL_CATEGORY_ID, UPCOMING_CTFTIME_FILE, ONGOING_CTFTIME_FILE, CTF_JOIN_CHANNEL, EVENT_LOG_FILE

    # Load event file
    with open(EVENT_LOG_FILE, 'r') as file:
        EVENTS_DATA = json.load(file)

    
    category = get_category_by_id(guild=ctx.guild, category_id=CTF_CHANNEL_CATEGORY_ID[ctx.guild.name]) # use the name of the server to look for the category id in which he'll create the channel (to be setup in conf.json)

    CTF_EVENT = await search_ctf_data(filename=UPCOMING_CTFTIME_FILE, query=ctf_name, WEIGHT_RANGE=WEIGHT_RANGE) # look for the CTF in the upcoming list
    #CTF_EVENT += await search_ctf_data(filename=ONGOING_CTFTIME_FILE, query=ctf_name, WEIGHT_RANGE=WEIGHT_RANGE) # (Optional) look for CTFs in the Ongoing list

    # makes sure 1 CTF will be registered for the channel
    if not CTF_EVENT: 
        await ctx.send(f"Error : no CTF found, please use the /search to make sure you send a valid CTF name for this command (between \" \").")
        return None
    elif len(CTF_EVENT) > 1 :
        await ctx.send(f"Error : more than one CTF was found, please use the /search to make sure you only send 1 CTF for this channel (between \" \").")
        return None

    # retrieve all the roles of the server
    role = get(ctx.guild.roles, name=role_name)

    if role is None: # role doesnt exists, its created
        role = await ctx.guild.create_role(name=role_name)
    else: # already exists, either a missinput or a role that wasnt created by 
        await ctx.send("the role already exists, if this is an error please contact an admin.") # the role has already been created

        event_info = await search_event_data(EVENT_LOG_FILE, role=role) # tries to retrieve the data (if the role has been created by the Bot)

        if not event_info:
            await ctx.send("No event found matching that role.")
            return None

        channelID = CTF_JOIN_CHANNEL[str(ctx.guild.name)] # retrieve the id of the channel based on the server name (in conf.json)
        channel = bot.get_channel(int(channelID)) # retrieve the channel

        if (await reply_message(ctx, channel, event_info['join_message_id'], f"{ctx.author.mention} Here is the link to the original message.") == None):
            await ctx.send('Error : Original join message couldnt be found.')

        return None # keep this to avoid someone retrieving a role he shouldnt



    # add the message to join the CTF
    message = await ctx.send("React to this message to get access to the CTF channel!")
    await message.add_reaction("🚩")
    @bot.event
    async def on_reaction_add(reaction, user):
        if reaction.message.id == message.id and str(reaction.emoji) == "🚩":
            if (role not in user.roles): # check if user already has it (to avoid spam)
                # Add the role to the user who reacted
                await user.add_roles(role)
                await user.send(f"You've been given the {role_name} role!")

        # (Optional) Remove the user's reaction after assigning the role
        # await reaction.remove(user)


    already_exist = get_channel_by_name(ctx.guild, f"🚩-{role.name}") # this channel already exists. returns None
    if already_exist:
        await ctx.send(f"A channel by that name has already been created here {already_exist.mention}")
        return None # remove the comment


    private_channel = await create_private_channel(ctx.guild, category, role)


    # print(CTF_EVENT)

    CTF_EVENT = {
        role.name: {
            # event info
            "title": CTF_EVENT[0]['title'],
            "weight": CTF_EVENT[0]['weight'],
            "url": CTF_EVENT[0]['url'],
            "ctftime_url": CTF_EVENT[0]['ctftime_url'],
            "start": CTF_EVENT[0]['start'],
            "finish": CTF_EVENT[0]['finish'],
            "duration": CTF_EVENT[0]['duration'],
            "format": CTF_EVENT[0]['format'],
            "location": CTF_EVENT[0]['location'],
            "logo": CTF_EVENT[0]['logo'],
            "description": CTF_EVENT[0]['description'],
            "onsite": CTF_EVENT[0]['onsite'],

            # personal info
            "add_type": "Quick_Add",
            "is_over_now": False,
            "is_votable_now": False,
            "channelID": private_channel.id, # the channel dedicated to this CTF
            "join_message_id": message.id # the message that was sent to join it
        }
    }
    EVENTS_DATA.append(CTF_EVENT)

    event_info = CTF_EVENT[role.name]


    with open(EVENT_LOG_FILE, 'w') as file:
        json.dump(EVENTS_DATA, file, indent=4)
            
    embeded_message = await send_event_info(event_info=event_info, id=0)

    await private_channel.send(embed=embeded_message)

# DEPRECATED
# @bot.command(name="info")
# async def get_info(ctx):
#     global EVENT_LOG_FILE

#     channelrolename = ctx.channel.name[2::] # since the channel are created by "🚩-" + the role we can retrieve the role like this (but its lowercase)
#     roles = ctx.guild.roles # an array of all the roles of the server
#     event_info = None # var for the data

#     for role in roles:
#         if str(role).lower() == str(channelrolename):
#             event_info = await search_event_data(EVENT_LOG_FILE, role)
    
#     if event_info is None:
#         await ctx.send("No info could be found for this channel. make sure you are using this command in one of the CTF event channel.")
#         return None
    
#     embeded_message = await send_event_info(event_info=event_info, id=1)

#     await ctx.send(embed=embeded_message)
  
#     return None


@bot.command(name="info")
async def get_info(ctx):
    global EVENT_LOG_FILE

    with open(EVENT_LOG_FILE, 'r') as data:
        EVENTS_DATA = json.load(data)

    id = ctx.channel.id 
    event_info = None # var for the data

    for event in EVENTS_DATA:
        for role in event:

            role_id = event[role]['channelID']
            if int(id) == int(role_id):
                event_info = event[role]


    if event_info is None:
        await ctx.send("No info could be found for this channel. make sure you are using this command in one of the CTF event channel.")
        return None
    
    embeded_message = await send_event_info(event_info=event_info, id=1)

    await ctx.send(embed=embeded_message)
        
            
    return None


@bot.command(name="BATMAN")
async def testfunc(ctx):
    await ctx.send(f"https://cdn.discordapp.com/attachments/1021532723661254707/1297666663407423609/Joker_caught_a_Pokemon.mp4?ex=6716c1c2&is=67157042&hm=2df40f38c86a189ac74125e7b0e81798dd2d8909dc355355cdaba0adf6c53ff8&")

@bot.command(name="GET_DATA")
async def testfunc(ctx):
    print(f"{ctx.guild.name}")



import datetime
@bot.command(name="test")
async def testfunc(ctx):
    test = datetime.datetime.now().timestamp()
    print(test)

#
#   TROLL
#
@bot.command(name="yvain")
async def yvain_man(ctx):
    await ctx.send('https://images-ext-1.discordapp.net/external/OBPLGRvgM9BbzOFYV-GHXm9pbjjeXFYxR3IbQ73SYxo/https/media.tenor.com/2GXG2TIZ35MAAAPo/noryoz-owa-owa.mp4')

#
#   DO NOT REMOVE
#

if __name__ == '__main__':
    # Run the bot
    bot.run(TOKEN)
