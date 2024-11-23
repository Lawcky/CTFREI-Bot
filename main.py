import discord
import json
from bot_functions import *
from discord.ext import commands
from discord.ui import Button, View
from discord.utils import get
from os import path as p
from os import mkdir


"""CONFIGURATION LOADING"""

CTFREI = "__GOATS__"
with open('conf.json') as conf_file:
    conf = json.load(conf_file)

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

intents = discord.Intents.default()
intents.messages = True 
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)


"""EVENT REGISTRATION: FILE EDITING"""


# allow to add an event to the current events on a server, needs a role name (str) and a ctf name (that can be found using /search)
@bot.tree.command(name="quickadd", description="Automatically registers a new event for the server (CTFTIME only).", guild=discord.Object(id=DISCORD_GUILD_ID))
async def add_reaction_and_channel(ctx: discord.Interaction, role_name: str, ctf_name: str):


    """RETRIEVE ALL THE DATA HERE"""


    try:
        category = get_category_by_id(guild=ctx.guild, category_id=CTF_CHANNEL_CATEGORY_ID[ctx.guild.name])
        CTF_EVENT = await search_ctf_data(filename=UPCOMING_CTFTIME_FILE, query=ctf_name, WEIGHT_RANGE=WEIGHT_RANGE)
        current_events = list_directory_contents(f"{CURRENT_CTF_DIR}{ctx.guild.id}")
        role = get(ctx.guild.roles, name=role_name)
        ctfChannel = get_channel_by_name(ctx.guild, f"🚩-{role_name}")
    except ValueError:
        await ctx.response.send_message('Error retrieving data from the server. If this persists, please contact an admin.')
        return 1


    """CHECK FOR ALREADY EXISTING DATA (if there is, stop function and return error)"""


    try:
        if not CTF_EVENT:
            await ctx.response.send_message("Error: No CTF found. Please use the /search to make sure you send a valid CTF name.", ephemeral=True)
            return None
        elif len(CTF_EVENT) > 1:
            await ctx.response.send_message("Error: More than one CTF was found. Please use the /search to make sure you only send 1 CTF.", ephemeral=True)
            return None

        event_id = generate_unique_id(str(CTF_EVENT[0]['title']))  # To avoid duplicates with different roles
        for event in current_events:
            if event_id in event:
                await ctx.response.send_message("Event seems to already be registered to this server. If this is an error, please contact admins.", ephemeral=True)
                return None

        CTF_EVENT = CTF_EVENT[0]  # Select the data of the event

        if role:
            await ctx.response.send_message("The role already exists. If this is an error, please contact an admin.")
            return None

        if ctfChannel:
            await ctx.response.send_message(f"A channel by that name has already been created here {ctfChannel.mention}", ephemeral=True)
            return None
    except ValueError:
        await ctx.response.send_message('Error checking data from the server. If this persists, please contact an admin.')
        return 1


    """ALL THE CHECKS PASSED: CREATING ALL THE ROLES AND CHANNELS"""


    try:
        role = await ctx.guild.create_role(name=role_name)
        private_channel = await create_private_channel(ctx.guild, category, role)
    except ValueError:
        await ctx.response.send_message("Error during the data creation. Please contact an admin if this persists.", ephemeral=True)
        return 1


    """CREATE THE INTERACTION TO JOIN THE EVENT (click for role)"""


    class RoleButton(Button):
        def __init__(self, role):
            super().__init__(label="🚩 Get to get the role & join The CTF!", style=discord.ButtonStyle.primary)
            self.role = role

        async def callback(self, interaction: discord.Interaction):
            user = interaction.user
            if self.role not in user.roles:
                await user.add_roles(self.role)
                await interaction.response.send_message(f"You have been added to the {self.role.name} role!", ephemeral=True)

    # Create the button and view after the role is created
    button = RoleButton(role)
    view = View()
    view.add_item(button)

    # Send the message with the button
    try:
        join_message = await ctx.channel.send(f"{CTF_EVENT['title']} has been added to the current events here {private_channel.mention}", view=view)
    except ValueError:
        await ctx.response.send_message("Error creating the join message. Please contact an admin if this persists.", ephemeral=True)
        return 1


    """SAVING ALL THE DATA"""


    try:
        # Save the event data to a file
        event_info = {
            "title": CTF_EVENT['title'],
            "weight": CTF_EVENT['weight'],
            "url": CTF_EVENT['url'],
            "ctftime_url": CTF_EVENT['ctftime_url'],
            "start": CTF_EVENT['start'],
            "finish": CTF_EVENT['finish'],
            "duration": CTF_EVENT['duration'],
            "format": CTF_EVENT['format'],
            "location": CTF_EVENT['location'],
            "logo": CTF_EVENT['logo'],
            "description": CTF_EVENT['description'],
            "onsite": CTF_EVENT['onsite'],
            "role_name": role.name,
            "event_id": event_id,
            "users_vote": {},
            "channelID": private_channel.id,
            "join_message_id": join_message.id
        }
        event_file_name = f"{role.name}-{event_id}-{private_channel.id}"
        complete_event_file_path = f"{CURRENT_CTF_DIR}{ctx.guild.id}/{event_file_name}"
        with open(complete_event_file_path, 'x') as file:
            json.dump(event_info, file, indent=4)
    except ValueError:
        await ctx.response.send_message("Error saving data from the server. If this persists, please contact an admin.", ephemeral=True)
        return 1


    """OTHER: SEND THE EVENT DATA TO THE NEW CHANNEL"""


    await private_channel.send(embed=(await send_event_info(event_info=event_info, id=0)))
    await ctx.response.send_message("Event added successfully!", ephemeral=True)
    return None

# refresh the list of upcoming CTFs (using CTFtime API's, reload up to 100 events)
@bot.tree.command(name="refresh", description="A command to refresh the upcoming CTFs list.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def refresh_data(ctx: discord.Interaction):

    try:
        data = api_call("https://ctftime.org/api/v1/events/?limit=100", UPCOMING_CTFTIME_FILE)
        last = str(data[-1]['finish'])[:10:]
        if not data:
            await ctx.response.send_message(f"Error updating.", ephemeral=True)
        await ctx.response.send_message(f"events have been updated up to {last}", ephemeral=True)
        return None
    except ValueError:
        ctx.response.send_message("Error during the updating of the event data.", ephemeral=True)
        return 1


"""SEARCHING COMMANDS (GENERAL): NO FILE MODIFICATION"""


# List all the upcoming CTFs based on the UPCOMING file
@bot.tree.command(name="upcoming", description="List the N upcoming CTFs events.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def upcoming_ctf(ctx: discord.Interaction, max_events: int = MAX_EVENT_LIMIT):
  
    """Retrieve data from UPCOMING file"""

    if max_events and max_events > 25:
        max_events = 25 # set a limit to 25, above the response will crash.

    try:
        with open(UPCOMING_CTFTIME_FILE) as data_file:
            events = json.load(data_file)
    except ValueError:
        await ctx.response.send_message("Error reading upcoming event list's file.", ephemeral=True)
        return 1

    embeded_message = discord.Embed(
            title="Upcoming CTF Events",  # Title of the embed
            description="Here are the lists of the upcoming CTFs on CTFTIME",  # Description of the embed
            color=discord.Color.blue()  # Color of the side bar (you can change the color)
        )

    try: 
        count = 0 # variable to limit the amount of output per message (discord limits)
        for event in events: 
            if (event['location'] == ''):

                event_info = f"Weight: {event['weight']} | {event['format']} | starts : {str(event['start'])[:10:]}" # format for the output of the CTF upcoming lists for each event
                embeded_message.add_field(name=event['title'], value=event_info, inline=False)
                
                count += 1

            if (count >= max_events):
                break  
    except ValueError:
        ctx.response.send_message("Error listing all the events, please contact an admin if this persists.", ephemeral=True)
        return 1
    
    embeded_message.set_footer(text="For more event use /upcoming {number}, you can refresh the data using /refresh or you can learn more about a specific event using /search {name of the event}")

    await ctx.response.send_message(embed=embeded_message, ephemeral=True)
    return None

# list all the files in the current events directory and prints some info
@bot.tree.command(name="listevents", description="list all registered events on the current server.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def list_registered_events(ctx: discord.Integration):
    
    try:
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
    except ValueError:
        await ctx.response.send_message('error retrieving data.', ephemeral=True)
        return 1


    embeded_message = discord.Embed(
            title="Registered CTF Events", 
            description="Here is the lists of CTF events currently registered on this server.", 
            color=discord.Color.dark_grey()  # Color of the side bar (you can change the color)
        )
    
    try:
        for individual_event in events_data: 
            event_chan = ctx.guild.get_channel(individual_event[4])
            event_info = f"Weight: {individual_event[1]} | start: {individual_event[2]} | Event ID: {individual_event[7]} | channel: {event_chan.mention}" # format for the output of the Currently registered CTF
            embeded_message.add_field(name=individual_event[0], value=event_info, inline=False)
    except ValueError:
        await ctx.response.send_message('error using data.', ephemeral=True)
        return 1
    
    embeded_message.set_footer(text="You can learn more about a specific event by joining the event directly or by using /registered_search {eventID}")

    await ctx.response.send_message(embed=embeded_message, ephemeral=True)
    return None

# # basically the listevents command with the PAST_CTF_DIR and some different text in embedded msg
# @bot.tree.command(name="listpasts", description="List all past events on the current server (imperfect, to stay disabled).", guild=discord.Object(id=DISCORD_GUILD_ID))
# async def list_pasts_events(ctx: discord.Integration):
    
#     try:
#         pasts_events = list_directory_contents(f"{PAST_CTF_DIR}{ctx.guild.id}")
#         if not pasts_events:
#             await ctx.response.send_message('No Event could be found.', ephemeral=True)
#             return 1
        
#         events_data = []
#         for individual_event in pasts_events:
#             with open(f"{PAST_CTF_DIR}{ctx.guild.id}/{individual_event}") as individual_event_file:
#                 temp = json.load(individual_event_file)
#                 full_data = [temp['title'], temp['weight'], temp['start'][:10:], temp['url'], temp['channelID'], temp['join_message_id'], temp['role_name'], temp['event_id'], temp['logo']]
#                 events_data.append(full_data)
#     except ValueError:
#         await ctx.response.send_message('error retrieving data.', ephemeral=True)
#         return 1


#     embeded_message = discord.Embed(
#             title="Pasts CTF Events", 
#             description="Here is the lists of past CTFs events on this server.", 
#             color=discord.Color.dark_grey()  # Color of the side bar (you can change the color)
#         )
    
#     try:
#         for individual_event in events_data: 
#             event_chan = ctx.guild.get_channel(individual_event[4])
#             event_info = f"Weight: {individual_event[1]} | start: {individual_event[2]} | Event ID: {individual_event[7]} | channel: {event_chan.mention}" # format for the output of the Currently registered CTF
#             embeded_message.add_field(name=individual_event[0], value=event_info, inline=False)
#     except ValueError:
#         await ctx.response.send_message('error using data.', ephemeral=True)
#         return 1
    
#     embeded_message.set_footer(text="You can learn more about a past event by going on their respective channel and running /summary")

#     await ctx.response.send_message(embed=embeded_message, ephemeral=True)

#will search the upcoming files for matches, can use integer for weight search, for strings for name/tag search
@bot.tree.command(name="search", description="Will search the data of the upcoming CTFs, query can be either an integer or a string.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def search_json(ctx: discord.Interaction, query: str = None):

    if (query == None):
        await ctx.response.send_message(f"Please add one of 2 queries either: \n- **string** => search events by name/tag\n- **integer** => search event by Weight range (range of {WEIGHT_RANGE})", ephemeral=True)
        return None

    try:
        matches = await search_ctf_data(UPCOMING_CTFTIME_FILE, query, WEIGHT_RANGE)
        if not matches:
            await ctx.response.send_message("No event could be found, check if it is already registered using /listevents, and if it is just not found you can use /refresh to refresh the Event List and try again.", ephemeral=True) 
            return None
    except ValueError:
        await ctx.response.send_message("Error searching for matches.", ephemeral=True)
        return 1

    
    embeded_message = discord.Embed(
            title="CTF Events Found",  
            description="Here is a list of matches based on your query",  
            color=discord.Color.greyple()  # Color of the side bar (you can change the color)
        )
    try : 
        count = 0 # to limit output (avoid discord limit related crashes)
        for event in matches: 
            if count < 12:
                event_info = f"**Weight: {event['weight']} | {event['format']} | Starts: {event['start'][:10:]} => [CTFTIME]({event['url']})**\n"
                count += 1
                embeded_message.add_field(name=f"**__{event['title']}__**", value=event_info, inline=False)
            else:
                continue
    except ValueError:
        await ctx.response.send_message("Error crafting the response.", ephemeral=True)
        return 1

    embeded_message.set_footer(text="you can learn more about a specific event using /search {name of the event}")

    await ctx.response.send_message(embed=embeded_message, ephemeral=True)
    return None


# search the directory for current events using its ID 
@bot.tree.command(name="registered_search", description="Search data on a currently registered event using its ID.", guild=discord.Object(id=DISCORD_GUILD_ID))
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
    
    try:
        channel_id = ctx.channel.id # used for search
        event_data = {}
        event_list = list_directory_contents(f"{CURRENT_CTF_DIR}{ctx.guild.id}")
        for event_file in event_list:
            if str(channel_id) in event_file:
                with open(f"{CURRENT_CTF_DIR}{ctx.guild.id}/{event_file}", 'r') as data:
                    event_data = json.load(data)
            
        if not event_data:
            await ctx.response.send_message(f"No event could be found for this channel. please make sure you use this command in a CTF channel. (/listevents)", ephemeral=True)
            return 1


        embeded_message = await send_event_info(event_info=event_data, id=1)
    except ValueError:
        await ctx.response.send_message("Retrieving the info.", ephemeral=True)
        return 1
    
    await ctx.response.send_message(embed=embeded_message, ephemeral=True)
    return None



"""ONGOING / TESTING / DEV"""

# TO BE ADDED

# displays more info on current channel's CTF
@bot.tree.command(name="more", description="displays all info on current channel's CTF", guild=discord.Object(id=DISCORD_GUILD_ID))
async def get_more_info(ctx: discord.integrations):
    print(1)

# displays info on current channel's CTF
@bot.tree.command(name="summary", description="displays info and grade on current channel's CTF", guild=discord.Object(id=DISCORD_GUILD_ID))
async def event_summary(ctx: discord.integrations):
    print(1)

# mark an event as over, cannot be done when event isnt over
@bot.tree.command(name="end", description="End the CTF", guild=discord.Object(id=DISCORD_GUILD_ID))
async def end_event(ctx: discord.integrations):
    print(1)

# allows to give a grade to an event between 4 levels (to set in conf.json)
@bot.tree.command(name="vote", description="start the vote for the CTF (only if over)", guild=discord.Object(id=DISCORD_GUILD_ID))
async def event_democracy(ctx: discord.integrations):
    print(1)



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





"""DISCORD SETUP"""


# sync commands with the given DISCORD_GUILD_ID
@bot.tree.command(name="sync", description="commande pour sync les commandes (dev only)")
async def sync(ctx: discord.Interaction):
    await ctx.response.defer(ephemeral=True) 
    await bot.tree.sync(guild=discord.Object(id=DISCORD_GUILD_ID))
    await ctx.edit_original_response(content="Commands synced successfully!")

#   DO NOT REMOVE

# minimum necessary to start the bot
async def basic_setup():
    try:
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
        
        print('SETUP HAS BEEN CHECKED')
        return None
    except ValueError:
        print("Error during SETUP CHECKING")
        return 1

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


    if (p.isdir(f"{CURRENT_CTF_DIR}{ctx.guild.id}") and p.isdir(f"{PAST_CTF_DIR}{ctx.guild.id}") and p.isfile(UPCOMING_CTFTIME_FILE)):
        return 0
    else:
        print("something is not right")
        return 1

@bot.event
async def on_ready():
    await basic_setup()
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')


if CTFREI == '__GOATS__':
    bot.run(TOKEN)
