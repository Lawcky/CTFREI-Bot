import discord
import json
from bot_functions import extract_ctf_data, search_ctf_data, create_private_channel, get_category_by_id, get_channel_by_name, reply_message, search_event_data
from discord.ext import commands
from discord.utils import get
import time
from os import path as p

# Load configuration file
with open('conf.json') as conf_file:
    conf = json.load(conf_file)
# Extract token from JSON
TOKEN = conf['DISCORD_TOKEN'] # discord token
CTFTIME_REFRESH_TIME = conf['CTFTIME_REFRESH_TIME'] # number of seconds between each refresh of the ctftime data (about once a day is good enough)

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
@bot.command(name="upcoming")
async def upcoming_ctf(ctx, max_events: int = MAX_EVENT_LIMIT):
    global last_refresh_upcoming, UPCOMING_CTFTIME_FILE
    
    max_events -= 1 # when asked for 5 will print 5 instead of 6
    
    timestamps = int(time.time())
    if ((last_refresh_upcoming + CTFTIME_REFRESH_TIME) > timestamps): # if the last time it was fetched + the given delay is more than the actual timestamp a new parsing is done to refresh the data 
        events = await extract_ctf_data("https://ctftime.org/event/list/upcoming", UPCOMING_CTFTIME_FILE)
        last_refresh_upcoming = timestamps
    else:
        # Load already parsed data
        with open(UPCOMING_CTFTIME_FILE) as data_file:
            events = json.load(data_file)

    embeded_message = discord.Embed(
            title="Upcoming CTF Events",  # Title of the embed
            description="Here are the lists of known upcoming CTF events on CTFTIME",  # Description of the embed
            color=discord.Color.blue()  # Color of the side bar (you can change the color)
        )


    count = 0 # variable to limit the amount of output per message (discord limits)
    for event in events: 
        if (event['location'] == 'On-line'):

            event_info = f"Weight: {event['weight']} | {event['format']}" # format for the output of the CTF upcoming lists for each event
            embeded_message.add_field(name=event['name'], value=event_info, inline=False)
            
            count += 1

        if (count > max_events):
            break
    
    embeded_message.add_field(name="Note", value="For more event use /upcoming {number}, or you can learn more about a specific event using /search {name of the event}", inline=False)

    await ctx.send(embed=embeded_message)

#list all the CTF competitions that are currently running
@bot.command(name="ongoing")
async def ongoing_ctf(ctx):
    global last_refresh_ongoing, ONGOING_CTFTIME_FILE
    
    timestamps = int(time.time())
    if ((last_refresh_ongoing + CTFTIME_REFRESH_TIME) > timestamps): # if the last time it was fetched + the given delay is more than the actual timestamp a new parsing is done to refresh the data 
        events = await extract_ctf_data("https://ctftime.org/event/list/?now=true", ONGOING_CTFTIME_FILE)
        last_refresh_ongoing = timestamps
    else:
        # Load already parsed data
        with open(ONGOING_CTFTIME_FILE) as data_file:
            events = json.load(data_file)

    embeded_message = discord.Embed(
            title="Ongoing CTF Events",  # Title of the embed
            description="Here are the lists of known ongoing CTF events in CTFTIME",  # Description of the embed
            color=discord.Color.green()  # Color of the side bar (you can change the color)
        )

    count = 0 # variable to limit the amount of output per message (discord limits)
    for event in events: 
        event_info = f"Weight: {event['weight']} | location -> {event['location']} | {event['format']}" # format for the output of the CTF upcoming lists for each event
        embeded_message.add_field(name=event['name'], value=event_info, inline=False)
        
        count += 1

        if (count > MAX_EVENT_LIMIT):
            break
    
    embeded_message.add_field(name="Note", value="you can learn more about a specific event using /search {name of the event}", inline=False)

    await ctx.send(embed=embeded_message)

#will read both json files and look for a corresponding CTF with either the right weight or name
@bot.command(name="search")
async def search_json(ctx, query: str = None):

    if (query == None):
        await ctx.send('Please add a query')
        return None

    # check if files exists and arent empty, if either is true it'll start the parsing of the site
    if (not p.isfile(UPCOMING_CTFTIME_FILE) or p.getsize(UPCOMING_CTFTIME_FILE) == 0):
        await extract_ctf_data("https://ctftime.org/event/list/upcoming", UPCOMING_CTFTIME_FILE)
    if (not p.isfile(ONGOING_CTFTIME_FILE) or p.getsize(ONGOING_CTFTIME_FILE) == 0):
        await extract_ctf_data("https://ctftime.org/event/list/?now=true", ONGOING_CTFTIME_FILE)

    matches = await search_ctf_data(UPCOMING_CTFTIME_FILE, query, WEIGHT_RANGE)
    #add msg here
    matches += await search_ctf_data(ONGOING_CTFTIME_FILE, query, WEIGHT_RANGE)
    # add msg here

    for match in matches: # too long makes it crash
        message = f"**{match['name']}** | {match['weight']} ---> *{match['link']}*\n"
        await ctx.send(message)

#
#  CHANNEL & ROLE MANAGEMENT RELATED COMMANDS
#

@bot.command(name="quickadd")
async def add_reaction_and_channel(ctx, role_name: str, ctf_name: str):

    global CTF_CHANNEL_CATEGORY_ID, UPCOMING_CTFTIME_FILE, ONGOING_CTFTIME_FILE, CTF_JOIN_CHANNEL, EVENT_LOG_FILE

    # Load event file
    with open(EVENT_LOG_FILE, 'r') as file:
        EVENTS_DATA = json.load(file)

    
    category = get_category_by_id(ctx.guild, category_id=CTF_CHANNEL_CATEGORY_ID[ctx.guild.name]) # use the name of the server to look for the category id in which he'll create the channel (to be setup in conf.json)

    CTF_EVENT = await search_ctf_data(UPCOMING_CTFTIME_FILE, ctf_name, WEIGHT_RANGE) # look for the CTF in the upcoming list
    #CTF_EVENT += await search_ctf_data(ONGOING_CTFTIME_FILE, ctf_name, WEIGHT_RANGE) # (Optional) look for CTFs in the Ongoing list

    # makes sure 1 CTF will be registered for the channel
    if not CTF_EVENT: 
        await ctx.send(f"Error : no CTF found, please use the /search to make sure your send a valid CTF for this channel (between \" \").")
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

    CTF_EVENT = {
        role.name: {
            "name": CTF_EVENT[0]['name'],
            "weight": CTF_EVENT[0]['weight'],
            "link": CTF_EVENT[0]['link'],
            "date": CTF_EVENT[0]['date'],
            "format": CTF_EVENT[0]['format'],
            "location": CTF_EVENT[0]['location'],
            "add_type": "Quick_Add",
            "channelID": private_channel.id,
            "join_message_id": message.id
        }
    }
    EVENTS_DATA.append(CTF_EVENT)

    event_info = CTF_EVENT[role.name]


    with open(EVENT_LOG_FILE, 'w') as file:
        json.dump(EVENTS_DATA, file, indent=4)
            
    # TODO FROM HERE
    embeded_message = discord.Embed(
            title="CTF INFORMATION",
            description=f"Here are the information on the {event_info['name']} event.",  # Description of the embed
            color=discord.Color.dark_gold(), # Color of the side bar (you can change the color)
            # timestamp=event_info['date']
        )
    
    embeded_message.set_author(name=event_info['name'], url=event_info['link'])
    embeded_message.add_field(name="ici il y aura toute les infos (pas encore add pcq flemme)", value="YES")

    await private_channel.send(embed=embeded_message)


@bot.command(name="info")
async def add_reaction_and_channel(ctx):
    global EVENT_LOG_FILE

    channelrolename = ctx.channel.name[2::] # since the channel are created by "🚩-" + the role we can retrieve the role like this (but its lowercase)
    roles = ctx.guild.roles # an array of all the roles of the server
    event_info = None # var for the data

    for role in roles:
        if str(role).lower() == str(channelrolename):
            event_info = await search_event_data(EVENT_LOG_FILE, role)
            print(event_info)
    
    if event_info is None:
        await ctx.send("No info could be found for this channel. make sure you are using this command in one of the CTF event channel.")
        return None
    
    # TODO FROM HERE
    embeded_message = discord.Embed(
            title="CTF INFORMATION",
            description=f"Here are the information on the {event_info['name']} event.",  # Description of the embed
            color=discord.Color.blurple(), # Color of the side bar (you can change the color)
            # timestamp=event_info['date']
        )
    
    embeded_message.set_author(name=event_info['name'], url=event_info['link'])
    embeded_message.add_field(name="ici il y aura toute les infos (pas encore add pcq flemme)", value="YES")

    await ctx.send(embed=embeded_message)
        
            
    return None
    # print(event_info)
    # search_event_data(EVENT_LOG_FILE, ctx.channel.name)

















@bot.command(name="GET_DATA")
async def testfunc(ctx):
    print(f"{ctx.guild.name}")


@bot.command(name="test")
async def testfunc(ctx):
    channelID = CTF_JOIN_CHANNEL[str(ctx.guild.name)]
    print(channelID)

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
