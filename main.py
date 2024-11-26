import discord
import json
import time
from bot_functions import *
from discord.ext import commands
from discord.ui import Button, View
from discord.utils import get
from os import path as p
from os import mkdir, rename
from typing import Literal

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


"""Interactions related functions"""

INTERACTION_SAVE_FILE = conf['INTERACTION_SAVE_FILE']

# Load data from Interaction files
def load_persistent_data():
    try:
        with open(INTERACTION_SAVE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save data to the file
def save_persistent_data(data):
    with open(INTERACTION_SAVE_FILE, "w") as f:
        json.dump(data, f)

persistent_data = load_persistent_data()

class PersistentView(View):
    def __init__(self, role):
        super().__init__(timeout=None)
        self.add_item(RoleButton(role))




"""EVENT REGISTRATION: FILE EDITING"""


class RoleButton(Button):
        def __init__(self, role):
            super().__init__(label="🚩 Get to get the role & join The CTF!", style=discord.ButtonStyle.primary)
            self.role = role

        async def callback(self, interaction: discord.Interaction):
            user = interaction.user
            if self.role not in user.roles:
                await user.add_roles(self.role)
                await interaction.response.send_message(f"You have been added to the {self.role.name} role!", ephemeral=True)
            else:
                await interaction.response.send_message(f"You already have been asigned the {self.role.name} role!", ephemeral=True)

# allow to add an event to the current events on a server, needs a role name (str) and a ctf name (that can be found using /search)
@bot.tree.command(name="quickadd", description="Automatically registers a new event for the server (CTFTIME only).", guild=discord.Object(id=DISCORD_GUILD_ID))
async def add_reaction_and_channel(ctx: discord.Interaction, role_name: str, ctf_name: str):


    """RETRIEVE ALL THE DATA HERE"""


    try:
        category = get_category_by_id(guild=ctx.guild, category_id=CTF_CHANNEL_CATEGORY_ID[ctx.guild.name])
        join_channel = await ctx.guild.fetch_channel(CTF_JOIN_CHANNEL[ctx.guild.name])
        CTF_EVENT = await search_ctf_data(filename=UPCOMING_CTFTIME_FILE, query=ctf_name, WEIGHT_RANGE=WEIGHT_RANGE)
        current_events = list_directory_contents(f"{CURRENT_CTF_DIR}{ctx.guild.id}")
        role = get(ctx.guild.roles, name=role_name)
        ctfChannel = get_channel_by_name(ctx.guild, f"🚩-{role_name}")
        
        end_time = datetime.fromisoformat(CTF_EVENT[0]["finish"]).timestamp()
        current = datetime.now().timestamp()
        timeout_timer = end_time - current  # Calculate time remaining until end for interaction
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


    """CREATE THE INTERACTION TO JOIN THE EVENT (click for role)"""

    if timeout_timer < 0:
        await ctx.response.send_message(f"Event seems to be already over ({CTF_EVENT["finish"][:10:]})\nif this is an error please contact admin.", ephemeral=True)
        return None

    # Create the button and view after the role is created
    button = RoleButton(role)
    view = View(timeout=timeout_timer)
    view.add_item(button)



    """ALL THE CHECKS PASSED: CREATING ALL THE ROLES AND CHANNELS"""


    try:
        role = await ctx.guild.create_role(name=role_name)
        private_channel = await create_private_channel(ctx.guild, category, role)
    except ValueError:
        await ctx.response.send_message("Error during the data creation. Please contact an admin if this persists.", ephemeral=True)
        return 1

    # Send the message with the button
    try:
        join_message = await join_channel.send(f"{CTF_EVENT['title']} has been added to the current events here {private_channel.mention}", view=view)
        message_link = f"https://discord.com/channels/{ctx.guild.id}/{CTF_JOIN_CHANNEL[ctx.guild.name]}/{join_message.id}" # will be linked in the response

        persistent_data[str(join_message.id)] = {"role_id": role.id, "finish": CTF_EVENT['finish']} # to keep the interaction going
        save_persistent_data(persistent_data)

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
    await ctx.response.send_message(f"Event added successfully! join message is here : {message_link}", ephemeral=True)
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
                full_data = json.load(individual_event_file)

    if not full_data:
        await ctx.response.send_message(f"Could not find any event with id {event_id}. use /listevents to see all events.", ephemeral=True)
        return None



    event_chan = ctx.guild.get_channel(CTF_JOIN_CHANNEL[ctx.guild.name])

    message_link = f"https://discord.com/channels/{ctx.guild.id}/{event_chan.id}/{full_data['join_message_id']}"

    # Set up the embedded message
    color = discord.Color.dark_teal()
    embeded_message = discord.Embed(
        title=f"__{full_data['title']}__", 
        url=full_data['url'],
        description=f"Here are the information on {full_data['title']}.",
        color=color
    )
    
    embeded_message.set_author(name="CTF INFORMATION", url=full_data['url'])
    embeded_message.add_field(name="Weight", value=f"**{full_data['weight']}**", inline=True)
    embeded_message.add_field(name="Starts:", value=f"**{full_data['start'][:10:]}**", inline=True)
    embeded_message.add_field(name="Ends:", value=f"**{full_data['finish'][:10:]}**", inline=True)
    embeded_message.add_field(name="Joining:", value=f"**{message_link}**", inline=True)
    embeded_message.add_field(name="CTF link:", value=f"**{full_data['url']}**", inline=True)

    ctfrei_logo = "https://cdn.discordapp.com/attachments/1167256768087343256/1202189774836731934/CTFREI_Banniere_920_x_240_px_1.png?ex=67162479&is=6714d2f9&hm=c649d21b2152c0200b9466a29c09a04865387410258c1c228c8df58db111c539&"

    embeded_message.set_thumbnail(url=full_data['logo']) if full_data['logo'] else embeded_message.set_thumbnail(url=ctfrei_logo)

    embeded_message.set_image(url=ctfrei_logo)

    await ctx.response.send_message(embed=embeded_message, ephemeral=True)
    
    return None



"""SEARCHING COMMANDS (CTFs channel): NO FILE MODIFICATION"""



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


# displays the description of the current channel's CTF
@bot.tree.command(name="more", description="displays all info on current channel's CTF", guild=discord.Object(id=DISCORD_GUILD_ID))
async def get_more_info(ctx: discord.integrations):
    try:
        channel_id = ctx.channel.id # used for search
        event_data = []
        event_list = list_directory_contents(f"{CURRENT_CTF_DIR}{ctx.guild.id}")
        for event_file in event_list:
            if str(channel_id) in event_file:
                with open(f"{CURRENT_CTF_DIR}{ctx.guild.id}/{event_file}", 'r') as data:
                    event_data = json.load(data)
        if not event_data:
            await ctx.response.send_message(f"No event could be found for this channel. please make sure you use this command in a CTF channel. (/listevents)", ephemeral=True)
            return 1
    except ValueError:
        await ctx.response.send_message("Error retrieving the info.", ephemeral=True)
        return 1
    
    await ctx.response.send_message(f"Here is the description of **{event_data['title']}**:\n{event_data['description']}", ephemeral=True)
    return None


# allows to give a grade to an event between different possibilities
@bot.tree.command(name="vote", description="start the vote for the CTF (only if over)", guild=discord.Object(id=DISCORD_GUILD_ID))
async def event_democracy(ctx: discord.integrations, grade: Literal["Absolute Trash", "Not Worth", "OK tier", "Banger"]):
    
    """retrieve the CTF data (and users_vote if existing)"""

    try:
        data = {} # keep or will crash if no file found
        channel_id = ctx.channel.id # used for search
        event_list = list_directory_contents(f"{CURRENT_CTF_DIR}{ctx.guild.id}")
        for event_file in event_list:
            if str(channel_id) in event_file:
                with open(f"{CURRENT_CTF_DIR}{ctx.guild.id}/{event_file}", 'r') as data:
                    data = json.load(data)
                    users_vote = data['users_vote']
                    break
        if not data:
            await ctx.response.send_message(f"No event could be found for this channel. please make sure you use this command in a CTF channel. (/listevents) (you cannot vote for a CTF that was ended)", ephemeral=True)
            return 1
    except ValueError:
        await ctx.response.send_message("Error retrieving the info.", ephemeral=True)
        return 1
    
    """Set the users vote as grade's value"""
    try:
        users_vote[ctx.user.id] = grade
        data['users_vote'] = users_vote

        with open(f"{CURRENT_CTF_DIR}{ctx.guild.id}/{event_file}", 'w') as file:
            json.dump(data, file, indent=4)
            
        await ctx.response.send_message(f"Your vote has been registered ! ({grade})")
        return None
    
    except ValueError:
        await ctx.response.send_message("Error during the voting process.", ephemeral=True)
        return 1


# mark an event as over, cannot be done when event isnt over
@bot.tree.command(name="end", description="End the CTF", guild=discord.Object(id=DISCORD_GUILD_ID))
async def end_event(ctx: discord.integrations):

    """retrieve the data"""

    try:
        full_file_path = "" # keep or will crash if no file found
        ARCHIVE_CATEGORY = conf['ARCHIVE_CATEGORY'][ctx.guild.name]
        channel_id = ctx.channel.id # used for search
        event_list = list_directory_contents(f"{CURRENT_CTF_DIR}{ctx.guild.id}")
        for event_file in event_list:
            if str(channel_id) in event_file:
                full_file_path= f"{CURRENT_CTF_DIR}{ctx.guild.id}/{event_file}"

                with open(f"{CURRENT_CTF_DIR}{ctx.guild.id}/{event_file}", 'r') as data:
                    data = json.load(data)

                break
        if not full_file_path:
            await ctx.response.send_message(f"No event could be found for this channel. please make sure you use this command in a CTF channel. (/listevents) (the event cannot be already over)", ephemeral=True)
            return 1
        
        """Check if the event is actually over"""

        end_time = datetime.fromisoformat(data['finish']).timestamp()
        current = datetime.now().timestamp()

        if end_time > current: # event is not over
            await ctx.response.send_message(f"The Event is not over yet, if this is an error please contact an admin.", ephemeral=True)
            return 1

        """Move the file to PAST and move discord channel to the (optionnal)"""

        rename(full_file_path, f"{PAST_CTF_DIR}{ctx.guild.id}/{event_file}_{int(time.time())}")

        archive_category = get(ctx.guild.categories, id=ARCHIVE_CATEGORY)
        await ctx.channel.edit(category=archive_category)
        
        await ctx.response.send_message("CTF was ended successfully.")
        return None
    except ValueError:
        await ctx.response.send_message("Error retrieving the info.", ephemeral=True)
        return 1

# add here summary when done 

"""ONGOING / TESTING / DEV"""

# TO BE ADDED
# Make a summary of a past event, (mostly /info with the amount of ppl that have the role in question, and the average grade given + number of vote)
@bot.tree.command(name="summary", description="displays info and grade on current channel's CTF", guild=discord.Object(id=DISCORD_GUILD_ID))
async def event_summary(ctx: discord.integrations):
    print(1)


"""DISCORD SETUP"""


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
@bot.command(name="setup")
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


async def refresh_interactions(DISCORD_GUILD_ID, Channel_id): # function to refresh all old interaction post restart
    """Persistence of interactions."""
    if persistent_data:
        guild = bot.get_guild(DISCORD_GUILD_ID)  # The server to refresh
        channel = guild.get_channel(Channel_id)  # The channel to refresh

        if channel:
            for message_id, data in list(persistent_data.items()):  # Iterate through a copy to allow modification
                finish_date = data["finish"]  # Retrieve finish date
                end_time = datetime.fromisoformat(finish_date).timestamp()
                current = datetime.now().timestamp()
                timeout_timer = end_time - current  # Calculate time remaining

                # Check if the timeout has expired
                if timeout_timer < 0:
                    # Delete the expired message and remove its record
                    try:
                        message = await channel.fetch_message(int(message_id))
                        await message.delete()
                        print(f"Deleted expired message with ID {message_id}")
                    except discord.NotFound:
                        print(f"Message with ID {message_id} not found, skipping deletion.")
                    
                    # Remove from persistent_data and save changes
                    del persistent_data[message_id]
                    save_persistent_data(persistent_data)
                    continue  # Skip further processing for this message
                
                # Refresh the message with the new timeout
                try:
                    message = await channel.fetch_message(int(message_id))
                    role = discord.utils.get(channel.guild.roles, id=data["role_id"])
                    if role:
                        view = PersistentView(role)
                        view.timeout = timeout_timer  # Set the remaining timeout
                        await message.edit(view=view)  # Re-attach the view
                        print(f"Refreshed view for message {message_id} with timeout {timeout_timer} seconds.")
                except discord.NotFound:
                    # Handle deleted messages gracefully
                    print(f"Message with ID {message_id} not found during refresh.")
                    del persistent_data[message_id]
                    save_persistent_data(persistent_data)
        else:
            print("Channel not found.")
    else:
        print("No interaction to persist found.")

# sync commands with the given DISCORD_GUILD_ID
@bot.tree.command(name="sync", description="commande pour sync les commandes (dev only)")
async def sync(ctx: discord.Interaction):
    await ctx.response.defer(ephemeral=True) 
    await bot.tree.sync(guild=discord.Object(id=DISCORD_GUILD_ID))
    await refresh_interactions(ctx.guild.id, CTF_JOIN_CHANNEL[ctx.guild.name])
    await ctx.edit_original_response(content="Commands & interactions synced successfully!")

@bot.event
async def on_ready():
    await basic_setup()
    await bot.tree.sync()
    await refresh_interactions(DISCORD_GUILD_ID, CTF_JOIN_CHANNEL['Test-Bot-CTFREI']) # refresh all current interactions, and delete old join message
    

    print(f'Logged in as {bot.user}')

if CTFREI == '__GOATS__':
    bot.run(TOKEN)
