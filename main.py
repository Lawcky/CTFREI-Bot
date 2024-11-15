import discord
import json
from bot_functions import *
from discord.ext import commands
from discord.utils import get
from os import path as p
from os import mkdir


# Load configuration file
with open('conf.json') as conf_file:
    conf = json.load(conf_file)
# Extract token from JSON
TOKEN = conf['DISCORD_TOKEN'] # discord token
DISCORD_GUILD_ID = conf['DISCORD_GUILD_ID'] # discord Guild ID (useless for now)

UPCOMING_CTFTIME_FILE = conf['UPCOMING_CTFTIME_FILE'] # file to save all Events Data (CTFTIME)
EVENT_LOG_FILE = conf['EVENT_LOG_FILE'] # to be removed when new file system complete
CURRENT_CTF_DIR = conf['CURRENT_CTF_DIR'] # directory for the current CTF's
PAST_CTF_DIR = conf['PAST_CTF_DIR'] # directory for the past CTF's 

WEIGHT_RANGE = conf['WEIGHT_RANGE'] # the spread for the research by weight
MAX_EVENT_LIMIT = conf['MAX_EVENT_LIMIT'] - 1 # limit the maximum amount of event to be printed out by the bot in a single message (mostly to avoid crashing) 
CTF_CHANNEL_CATEGORY_ID = conf['CTF_CHANNEL_CATEGORY_ID']# the list of all the categories the bot can modify (one per server)
CTF_JOIN_CHANNEL = conf['CTF_JOIN_CHANNEL'] # channel to send msg

ROLE_DICTIONNARY = conf['ROLE_DICTIONNARY']
reaction_message_roles = {}


# loads reactions messages (for some reason the bot doesnt take it into account for reactions)
async def load_dict():
    global reaction_message_roles
    with open(ROLE_DICTIONNARY, 'r') as dicFile:
        reaction_message_roles = json.load(dicFile)


# Set up the bot with proper intents
intents = discord.Intents.default()
intents.messages = True 
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# role add for the quickadd and add command # LIMIT : if restarted old messages are not taken into account
@bot.event
async def on_reaction_add(reaction, user):

    # Check if the reaction is in the dictionary
    if reaction.message.id in reaction_message_roles and str(reaction.emoji) == "🚩":
        role_id = reaction_message_roles[reaction.message.id]
        role = user.guild.get_role(role_id)
        # Add the role to the user who reacted, if they don't already have it
        if role not in user.roles:
            await user.add_roles(role)
            await user.send(f"You've been given the {role.name} role!")

        # Optional: Remove the user's reaction after assigning the role
        # await reaction.remove(user)

@bot.tree.command(name="quickadd", description="automatically registers a new event for the server (CTFTIME only)", guild=discord.Object(id=DISCORD_GUILD_ID))
async def add_reaction_and_channel(ctx: discord.Interaction, role_name: str, ctf_name: str):
    
    category = get_category_by_id(guild=ctx.guild, category_id=CTF_CHANNEL_CATEGORY_ID[ctx.guild.name])

    CTF_EVENT = await search_ctf_data(filename=UPCOMING_CTFTIME_FILE, query=ctf_name, WEIGHT_RANGE=WEIGHT_RANGE)

    # Create unique ID and check if the event is already registered
    event_id = generate_unique_id(str(CTF_EVENT[0]['title']))
    current_events = list_directory_contents(f"{CURRENT_CTF_DIR}{ctx.guild.id}")
    for event in current_events:
        if event_id in event:
            await ctx.response.send_message("event seems to already be registered to this server, if this is an error please contact Lawcky.", ephemeral=True)
            return None

    if not CTF_EVENT:
        await ctx.response.send_message("Error: no CTF found, please use the /search to make sure you send a valid CTF name.", ephemeral=True)
        return None
    elif len(CTF_EVENT) > 1:
        await ctx.response.send_message("Error: more than one CTF was found, please use the /search to make sure you only send 1 CTF.", ephemeral=True)
        return None

    # Retrieve or create the role
    role = get(ctx.guild.roles, name=role_name)
    if role is None:
        role = await ctx.guild.create_role(name=role_name)
    else:
        await ctx.response.send_message("The role already exists, if this is an error please contact an admin.")
        return None

    # Add the message to join the CTF
    message = await ctx.channel.send("React to this message to get access to the CTF channel!")
    await message.add_reaction("🚩")

    # Store the message ID and role in the dictionary for tracking
    reaction_message_roles[message.id] = role.id

    with open(ROLE_DICTIONNARY, 'w') as dicFile:
        json.dump(reaction_message_roles, dicFile)

    already_exist = get_channel_by_name(ctx.guild, f"🚩-{role.name}")
    if already_exist:
        await ctx.response.send_message(f"A channel by that name has already been created here {already_exist.mention}", ephemeral=True)
        return None

    private_channel = await create_private_channel(ctx.guild, category, role)

    event_info = {
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
        "role_name": role.name,
        "event_id": event_id,
        "add_type": "Quick_Add",
        "users_vote": {},
        "channelID": private_channel.id,
        "join_message_id": message.id
    }

    event_file_name = f"{role.name}-{event_id}-{private_channel.id}"
    complete_event_file_path = f"{CURRENT_CTF_DIR}{ctx.guild.id}/{event_file_name}"
    with open(complete_event_file_path, 'x') as file:
        json.dump(event_info, file, indent=4)

    embeded_message = await send_event_info(event_info=event_info, id=0)
    await private_channel.send(embed=embeded_message)

    await ctx.response.send_message(f"{event_info['title']} has been added to the current events here {private_channel.mention}")


#  SEARCH AND LISTING OF EVENTS COMMANDS

#list all the CTF competitions that are upcoming based on the CTFTIME data, response to user only
@bot.tree.command(name="upcoming", description="List the N upcoming CTFs events...", guild=discord.Object(id=DISCORD_GUILD_ID))
async def upcoming_ctf(ctx: discord.Interaction, max_events: int = MAX_EVENT_LIMIT):
  
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

            event_info = f"Weight: {event['weight']} | {event['format']} | starts : {str(event['start'])[:10:]}" # format for the output of the CTF upcoming lists for each event
            embeded_message.add_field(name=event['title'], value=event_info, inline=False)
            
            count += 1

        if (count > max_events):
            break
    
    embeded_message.set_footer(text="For more event use /upcoming {number}, or you can learn more about a specific event using /search {name of the event}")

    await ctx.response.send_message(embed=embeded_message, ephemeral=True)


#works not on int
#will read both json files and look for a corresponding CTF with either the right weight or name, response to user only, need to change display
@bot.tree.command(name="search", description="Will search the data of the upcoming CTFs, query can be either an integer or a string.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def search_json(ctx: discord.Interaction, query: str = None):

    if (query == None):
        await ctx.response.send_message('Please add a query', ephemeral=True)
        return None

    # check if files exists and arent empty, if either is true it'll start the parsing of the site
    if (not p.isfile(UPCOMING_CTFTIME_FILE) or p.getsize(UPCOMING_CTFTIME_FILE) == 0):
        await  api_call("https://ctftime.org/api/v1/events/?limit=100", UPCOMING_CTFTIME_FILE)

    matches = await search_ctf_data(UPCOMING_CTFTIME_FILE, query, WEIGHT_RANGE)
    #add msg here
    # matches += await search_ctf_data(ONGOING_CTFTIME_FILE, query, WEIGHT_RANGE) # uncomment this if you activated the search through already running CTFs
    # add msg here

    for match in matches: # too long makes it crash
        print(match)
        message = f"**{match['title']}** | {match['weight']} ---> *{match['url']}*\n"
        await ctx.response.send_message(message, ephemeral=True)
    if not matches:
       await ctx.response.send_message("no event could be found.\nRemember: \n-if there are spaces write between \" \".\n-search command does not look for currently running CTFs by default.\n for more info on a specific CTF go on the related channel and enter /info.", ephemeral=True) 

    # TO BE USED WHEN REWORKING OUTPUT OF THE COMMAND
    # embeded_message = discord.Embed(
    #         title="Ongoing CTF Events",  # Title of the embed
    #         description="Here are the lists of known ongoing CTF events in CTFTIME",  # Description of the embed
    #         color=discord.Color.green()  # Color of the side bar (you can change the color)
    #     )

    # for event in events: 
    #     event_info = f"Weight: {event['weight']} | location -> {event['location']} | {event['format']}\n{event['link']}" # format for the output of the CTF upcoming lists for each event
    #     embeded_message.add_field(name=event['title'], value=event_info, inline=False)

    
    # embeded_message.set_footer(text="you can learn more about a specific event using /search {name of the event}")


@bot.tree.command(name="listevents", description="list all registered events on the current server.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def list_registered_events(ctx: discord.Integration):
    
    current_events = list_directory_contents(f"{CURRENT_CTF_DIR}{ctx.guild.id}")
    if not current_events:
        await ctx.response.send_message('No Event could be found.', ephemeral=True)
        return 1
    
    events_data = []
    for individual_event in current_events:
        with open(f"{CURRENT_CTF_DIR}{ctx.guild.id}/{individual_event}") as individual_event_file:
            temp = json.load(individual_event_file)
            full_data = [temp['title'], temp['weight'], temp['start'][:10:], temp['url'], temp['channelID'], temp['join_message_id'], temp['role_name'], temp['event_id'], temp['logo']]
            events_data.append(full_data)

    embeded_message = discord.Embed(
            title="Registered CTF Events",  # Title of the embed
            description="Here is the lists of CTF events currently registered on this server.",  # Description of the embed
            color=discord.Color.dark_grey()  # Color of the side bar (you can change the color)
        )

    for individual_event in events_data: 
        
        event_chan = ctx.guild.get_channel(individual_event[4])

        event_info = f"Weight: {individual_event[1]} | start: {individual_event[2]} | Event ID: {individual_event[7]} | channel: {event_chan.mention}" # format for the output of the Currently registered CTF


        embeded_message.add_field(name=individual_event[0], value=event_info, inline=False)

    
    embeded_message.set_footer(text="you can learn more about a specific event using by joining the event directly or by using /searchregistered {eventID}")

    await ctx.response.send_message(embed=embeded_message, ephemeral=True)

@bot.tree.command(name="searchregistered", description="search data on a currently registered event using its ID.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def search_registered_events(ctx: discord.Integration, event_id: str):

    current_events = list_directory_contents(f"{CURRENT_CTF_DIR}{ctx.guild.id}")

    full_data = []
    for event_file in current_events:
        if event_id in event_file:
            with open(f"{CURRENT_CTF_DIR}{ctx.guild.id}/{event_file}") as individual_event_file:
                temp = json.load(individual_event_file)
                full_data = [temp['title'], temp['weight'], temp['start'][:10:], temp['url'], temp['channelID'], temp['join_message_id'], temp['role_name'], temp['event_id'], temp['logo'], temp['finish'][:10:]]



    event_chan = ctx.guild.get_channel(CTF_JOIN_CHANNEL[ctx.guild.name])

    message_link = f"https://discord.com/channels/{ctx.guild.id}/{event_chan.id}/{full_data[5]}"

    # Set up the embedded message
    color = discord.Color.dark_teal() # if id 0 then dark_gold, else blurple()
    embeded_message = discord.Embed(
        title=f"__{full_data[0]}__", 
        url=full_data[3],
        description=f"Here are the information on {full_data[0]}.",
        color=color
    )
    
    embeded_message.set_author(name="CTF INFORMATION", url=full_data[3])
    embeded_message.add_field(name="Weight", value=f"**{full_data[1]}**", inline=True)
    embeded_message.add_field(name="Starts:", value=f"**{full_data[2]}**", inline=True)
    embeded_message.add_field(name="Ends:", value=f"**{full_data[9]}**", inline=True)
    embeded_message.add_field(name="Joining:", value=f"**{message_link}**", inline=True)
    embeded_message.add_field(name="CTF link:", value=f"**{full_data[3]}**", inline=True)

    embeded_message.set_image(url=full_data[8])

    await ctx.response.send_message(embed=embeded_message, ephemeral=True)

# displays info on current channel's CTF
@bot.tree.command(name="info", description="displays info on current channel's CTF", guild=discord.Object(id=DISCORD_GUILD_ID))
async def get_info(ctx: discord.Interaction):
    
    id = ctx.channel.id 
    # with open(EVENT_LOG_FILE, 'r') as data:
    #     EVENTS_DATA = json.load(data)

    event_list = list_directory_contents(f"{CURRENT_CTF_DIR}{ctx.guild.id}")
    for event_file in event_list:
        if str(id) in event_file:
            with open(f"{CURRENT_CTF_DIR}{ctx.guild.id}/{event_file}", 'r') as data:
                EVENTS_DATA = json.load(data)
    if not EVENTS_DATA:
        ctx.response.send_message('Error retrieving Data, make sure you are running this command inside one of the currently registered event or past. (/listevents and /listpasts)')


    embeded_message = await send_event_info(event_info=EVENTS_DATA, id=1)

    await ctx.response.send_message(embed=embeded_message, ephemeral=True)
        
    return None




# TO BE ADDED

@bot.tree.command(name="listpasts", description="list all past events on the current server.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def list_registered_events(ctx: discord.Integration):
    
    past_events = list_directory_contents(f"{PAST_CTF_DIR}{ctx.guild.id}")
    if not past_events:
        await ctx.response.send_message('No Event could be found.', ephemeral=True)
        return 1
    
    events_data = []
    for individual_event in past_events:
        with open(f"{PAST_CTF_DIR}{ctx.guild.id}/{individual_event}") as individual_event_file:
            temp = json.load(individual_event_file)
            full_data = [temp['title'], temp['weight'], temp['start'][:10:], temp['url'], temp['channelID'], temp['join_message_id'], temp['role_name'], temp['event_id'], temp['logo']]
            events_data.append(full_data)

    embeded_message = discord.Embed(
            title="Past CTF Events",  # Title of the embed
            description="Here is the lists of CTF events that were registered on this server.",  # Description of the embed
            color=discord.Color.dark_grey()  # Color of the side bar (you can change the color)
        )

    for individual_event in events_data: 
        
        event_chan = ctx.guild.get_channel(individual_event[4])

        event_info = f"Weight: {individual_event[1]} | start: {individual_event[2]} | Event ID: {individual_event[7]} | channel: {event_chan.mention}" # format for the output of the Currently registered CTF


        embeded_message.add_field(name=individual_event[0], value=event_info, inline=False)

    
    # embeded_message.set_footer(text="")

    await ctx.response.send_message(embed=embeded_message, ephemeral=True)


@bot.tree.command(name="add", description="Add a CTF event that is not currently on CTFtime", guild=discord.Object(id=DISCORD_GUILD_ID))
async def add(ctx: discord.Interaction):
    await ctx.response.send_message("not yet implemented, this will allow to add CTF events that are not inside the CTFtime data.")

# displays info on current channel's CTF
@bot.tree.command(name="more", description="displays all info on current channel's CTF", guild=discord.Object(id=DISCORD_GUILD_ID))
async def get_more_info(ctx: discord.integrations):
    print(1)

# displays info on current channel's CTF
@bot.tree.command(name="summary", description="displays info and grade on current channel's CTF", guild=discord.Object(id=DISCORD_GUILD_ID))
async def event_summary(ctx: discord.integrations):
    print(1)

# will refresh the event list in the UPCOMING file, response to user only
@bot.tree.command(name="refresh", description="A command to refresh the upcoming CTFs list...", guild=discord.Object(id=DISCORD_GUILD_ID))
async def refresh_data(ctx: discord.Interaction):

    data = api_call("https://ctftime.org/api/v1/events/?limit=100", UPCOMING_CTFTIME_FILE)

    last = str(data[-1]['finish'])[:10:]

    if data is not None:
        await ctx.response.send_message(f"events have been updated up to {last}", ephemeral=True)
    else: 
        await ctx.response.send_message(f"Error updating.", ephemeral=True)







# TROLL AND DEV

# JOKER DONT DO IT
@bot.command(name="BATMAN")
async def testfunc(ctx: discord.Interaction):
    await ctx.send(f"https://cdn.discordapp.com/attachments/1021532723661254707/1297666663407423609/Joker_caught_a_Pokemon.mp4?ex=6716c1c2&is=67157042&hm=2df40f38c86a189ac74125e7b0e81798dd2d8909dc355355cdaba0adf6c53ff8&")

@bot.tree.command(name="test")
async def testfunc(ctx: discord.Interaction):
    print(f"{dir(ctx)} \n\n {dir(ctx.message)}")

@bot.command(name="yvain")
async def yvain_man(ctx: discord.Interaction):
    await ctx.send('https://images-ext-1.discordapp.net/external/OBPLGRvgM9BbzOFYV-GHXm9pbjjeXFYxR3IbQ73SYxo/https/media.tenor.com/2GXG2TIZ35MAAAPo/noryoz-owa-owa.mp4')











@bot.tree.command(name="sync", description="commande pour sync les commandes (dev only)")
async def sync(ctx: discord.Interaction):
    await ctx.response.defer(ephemeral=True) 
    await bot.tree.sync(guild=discord.Object(id=1297601609802711061))
    await ctx.edit_original_response(content="Commands synced successfully!")

#   DO NOT REMOVE

# minimum necessary to start the bot
async def basic_setup():
    if (not p.isdir('log')):
        mkdir('log')
        print(f"Current CTF dir ('/log') has been created ")

    if (not p.isdir(CURRENT_CTF_DIR)): # check for current CTF dir
        mkdir(CURRENT_CTF_DIR)
        print(f"Current CTF dir ({CURRENT_CTF_DIR}) has been created ")

    if (not p.isdir(PAST_CTF_DIR)): # check for past CTF dir
        mkdir(PAST_CTF_DIR)
        print(f"Past CTF dir ({PAST_CTF_DIR}) has been created ")

    if (not p.isfile(UPCOMING_CTFTIME_FILE)):
        temp = {}
        with open(UPCOMING_CTFTIME_FILE, 'x') as filecreation:
            json.dump(temp, filecreation)
    
    if (not p.isfile(ROLE_DICTIONNARY)):
        temp = {}
        with open(ROLE_DICTIONNARY, 'x') as filecreation:
            json.dump(temp, filecreation)
    print('SETUP HAS BEEN CHECKED')

# setup command for each server to setup the file system
@bot.command(name="setup")# sets everything up for the bot
async def setup_dir(ctx: discord.integrations):

    if (not p.isdir(f"{CURRENT_CTF_DIR}{ctx.guild.id}")): # create server's dedicated dir in current
        mkdir(f"{CURRENT_CTF_DIR}{ctx.guild.id}")
        print(f"Discord CTF dir ({CURRENT_CTF_DIR}{ctx.guild.id}) has been created ")

    if (not p.isdir(f"{PAST_CTF_DIR}{ctx.guild.id}")): # create server's dedicated dir in past
        mkdir(f"{PAST_CTF_DIR}{ctx.guild.id}")
        print(f"Discord CTF dir ({PAST_CTF_DIR}{ctx.guild.id}) has been created ")

    print(f"\nSERVER INFORMATIONS:\n\nServer: {ctx.guild.name}\nServer ID: {ctx.guild.id}\nCurrent Channel: {ctx.channel.id}\nCurrent Category: {ctx.channel.category.id}")
    if (p.isdir(f"{CURRENT_CTF_DIR}{ctx.guild.id}") and p.isdir(f"{PAST_CTF_DIR}{ctx.guild.id}") and p.isfile(UPCOMING_CTFTIME_FILE) and p.isfile(ROLE_DICTIONNARY)):
        return 0

@bot.event
async def on_ready():
    await basic_setup()
    await load_dict()
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

if __name__ == '__main__':
    # Run the bot
    bot.run(TOKEN)
