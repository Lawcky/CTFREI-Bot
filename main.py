import discord
import json
import time
from bot_functions import *
from discord.ext import commands, tasks
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
CTF_ANNOUNCE_CHANNEL = conf['CTF_ANNOUNCE_CHANNEL'] # channel to send the announce

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

author_icon = "https://www.efrei.fr/wp-content/uploads/2024/07/ctefrei.png" # this is hardcoded once in bot_functions
footer_icon = "https://play-lh.googleusercontent.com/WOWsciDNUp-ilSYTtZ_MtkhZrhXBFp_y5KNGK0x7h2OnaqSe6JdRgQgbvBEUbNhuKxrW"

optional_thumbnail="https://cdn.discordapp.com/attachments/1167256768087343256/1202189272707502080/CFTREI_Story.png?ex=67517782&is=67502602&hm=308d0f9c1577dfad2a898dd262ad1e526127c115cf165a193d02ea5585ada2a3&"


"""INTERACTIONS' RELATED"""

INTERACTION_SAVE_FILE = conf['INTERACTION_SAVE_FILE']


def load_persistent_data():
    try:
        with open(INTERACTION_SAVE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_persistent_data(data):
    with open(INTERACTION_SAVE_FILE, "w") as f:
        json.dump(data, f)

persistent_data = load_persistent_data()

class PersistentView(View):
    def __init__(self, role):
        super().__init__(timeout=None)
        self.add_item(RoleButton(role))

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

@bot.tree.command(name="test", description="dev testing command", guild=discord.Object(id=DISCORD_GUILD_ID))
async def bordel(ctx):
    """ICI LES TRUCS A RAJOUTER"""


    event_info = {
        "title": "NOM_DU_CTF",
        "weight": 25.0,
        "url": "https://ctf.hackthebox.com/event/details/university-ctf-2024-binary-badlands-1822",
        "ctftime_url": "https://ctftime.org/event/2539/",
        "start": "2024-12-13T13:00:00+00:00",
        "finish": "2024-12-15T21:00:00+00:00",
        "duration": {
            "hours": 8,
            "days": 2
        },
        "format": "Jeopardy",
        "location": "",
        "logo": "https://ctftime.org//media/events/htbctf-logo_1.png",
        "onsite": False,
        "role_name": "htb_uni_2024",
        "event_id": "3fce356f",
        "users_vote": {},
        "channelID": 1313948527554199575,
        "join_message_id": 1313948528623751271
    }


    """SEND THE ANNOUNCEMENT"""
    announce_data = CTF_ANNOUNCE_CHANNEL[ctx.guild.name]
    announce_channel = await ctx.guild.fetch_channel(announce_data['channel_id'])
    announce_role = discord.utils.get(ctx.guild.roles, id=announce_data["role_id"])
    duration = (int(event_info['duration']['days'])*24) + (event_info['duration']['hours'])

    # Set up the embedded message
    color = discord.Color.red()
    embeded_message = discord.Embed(
        title=f"__{event_info['title']}__",
        # description=f"Hello {announce_role.mention} ! <:xxxxxxd:1312187847217909770>\nRegistrations are open for **{event_info['title']}** !",
        description="Salut {announce_role.mention} ! <:xxxxxxd:1312187847217909770>\n **{event_info['title']}** été ajouté sur le serveur ! \n\nRécupérez le rôle {role.mention} pour avoir accès au salon dédié.", # french version (cocorico)
        color=color
    )

    embeded_message.set_author(name="CTFEI BOT",icon_url="https://www.efrei.fr/wp-content/uploads/2024/07/ctefrei.png")

    embeded_message.add_field(name="**Informations:**", value=f":date: Du <t:{int((datetime.fromisoformat(event_info['start'])).timestamp())}> au <t:{int((datetime.fromisoformat(event_info['finish'])).timestamp())}>\n:alarm_clock: dure {duration} heures au total\n:man_lifting_weights: Weight estimé {event_info['weight'] if int(event_info['weight']) != 0 else 'inconnu'}", inline=True)

    embeded_message.add_field(name="**URI links:**", value=f"<:ctftime:1320354001287647264> [CTFTIME]({event_info['ctftime_url']})\n<:site:1320352422056693821> [CTFd]({event_info['url']})\n", inline=False)

    embeded_message.add_field(name="**Channel & role:**", value="<:logo_ctfrei:1167954970889441300> {message_link}", inline=False)

    embeded_message.set_image(url="https://cdn.discordapp.com/attachments/1167256768087343256/1202189774836731934/CTFREI_Banniere_920_x_240_px_1.png?ex=67162479&is=6714d2f9&hm=c649d21b2152c0200b9466a29c09a04865387410258c1c228c8df58db111c539&")

    if event_info['logo']:
        embeded_message.set_thumbnail(url=event_info['logo'])

    await ctx.response.send_message(embed=embeded_message, ephemeral=True)




@bot.tree.command(name="quickadd", description="Automatically registers a new event for the server (CTFTIME only).", guild=discord.Object(id=DISCORD_GUILD_ID))
async def add_reaction_and_channel(ctx: discord.Interaction, role_name: str, ctf_name: str):
    """add an event to the current events on a server, needs a role name (str) and a ctf name (that can be checked using /search)"""

    """RETRIEVE ALL THE DATA HERE"""

    # tries to find the ctf, if not found it'll stop the program
    CTF_EVENT = await search_ctf_data(filename=UPCOMING_CTFTIME_FILE, query=ctf_name, WEIGHT_RANGE=WEIGHT_RANGE)
    if not CTF_EVENT:
        await ctx.response.send_message("Error: No CTF found. Please use the /search to make sure you send a valid CTF name.", ephemeral=True)
        return None
    elif len(CTF_EVENT) > 1:
        await ctx.response.send_message("Error: More than one CTF was found. Please use the /search to make sure you only send 1 CTF.", ephemeral=True)
        return None

    try:
        category = get_category_by_id(guild=ctx.guild, category_id=CTF_CHANNEL_CATEGORY_ID[ctx.guild.name])
        join_channel = await ctx.guild.fetch_channel(CTF_JOIN_CHANNEL[ctx.guild.name])
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


    """Check if event is over (for interaction mostly)"""

    if timeout_timer < 0:
        await ctx.response.send_message(f"Event seems to be already over ({CTF_EVENT['finish'][:10:]})\nif this is an error please contact admin.", ephemeral=True)
        return None

    """ALL THE CHECKS PASSED: CREATING ALL THE ROLES AND CHANNELS"""

    try:
        role = await ctx.guild.create_role(name=role_name)
        private_channel = await create_private_channel(ctx.guild, category, role)
        # Create the button and view after the role is created
        button = RoleButton(role)
        view = View(timeout=timeout_timer)
        view.add_item(button)
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
            "role_id": role.id,
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


    """SEND THE ANNOUNCEMENT"""
    announce_data = CTF_ANNOUNCE_CHANNEL[ctx.guild.name]
    announce_channel = await ctx.guild.fetch_channel(announce_data['channel_id'])
    announce_role = discord.utils.get(ctx.guild.roles, id=announce_data["role_id"])
    duration = (int(event_info['duration']['days'])*24) + (event_info['duration']['hours'])

    # Set up the embedded message
    color = discord.Color.red()
    embeded_message = discord.Embed(
        title=f"__{event_info['title']}__",
        # description=f"Hello {announce_role.mention} ! <:xxxxxxd:1312187847217909770>\nRegistrations are open for **{event_info['title']}** !",
        description=f"Salut {announce_role.mention} ! <:xxxxxxd:1312187847217909770>\n **{event_info['title']}** à été ajouté sur le serveur ! \n\nRécupérez le rôle {role.mention} pour avoir accès au salon dédié.", # french version (cocorico)
        color=color
    )

    embeded_message.set_author(name="CTFREI BOT",icon_url="https://www.efrei.fr/wp-content/uploads/2024/07/ctefrei.png")

    embeded_message.add_field(name="**Informations:**", value=f":date: Du <t:{int((datetime.fromisoformat(event_info['start'])).timestamp())}> au <t:{int((datetime.fromisoformat(event_info['finish'])).timestamp())}>\n:alarm_clock: dure {duration} heures au total\n:man_lifting_weights: Weight estimé {event_info['weight'] if int(event_info['weight']) != 0 else 'inconnu'}", inline=True)

    embeded_message.add_field(name="**URI links:**", value=f"<:ctftime:1320354001287647264> [CTFTIME]({event_info['ctftime_url']})\n<:site:1320352422056693821> [CTFd]({event_info['url']})\n", inline=False)

    embeded_message.add_field(name="**Channel & role:**", value=f"<:logo_ctfrei:1167954970889441300> {message_link}", inline=False)

    embeded_message.set_image(url="https://cdn.discordapp.com/attachments/1167256768087343256/1202189774836731934/CTFREI_Banniere_920_x_240_px_1.png?ex=67162479&is=6714d2f9&hm=c649d21b2152c0200b9466a29c09a04865387410258c1c228c8df58db111c539&")

    if event_info['logo']:
        embeded_message.set_thumbnail(url=event_info['logo'])

    await announce_channel.send(embed=embeded_message)

    """OTHER: SEND THE EVENT DATA TO THE NEW CHANNEL"""

    await log(ctx, f"EDIT: added a new CTF ({CTF_EVENT['title']}) as {role.name}\n")
    await private_channel.send(embed=(await send_event_info(event_info=event_info, id=0)))
    await ctx.response.send_message(f"Event added successfully! join message is here : {message_link}", ephemeral=True)
    return None

@bot.tree.command(name="refresh", description="A command to refresh the upcoming CTFs list.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def refresh_data(ctx: discord.Interaction):
    """refresh the list of upcoming CTFs (using CTFtime API's, reload up to 100 events)"""
    try:
        data = api_call("https://ctftime.org/api/v1/events/?limit=100", UPCOMING_CTFTIME_FILE)
        last = str(data[-1]['finish'])[:10:]
        if not data:
            await ctx.response.send_message(f"Error updating.", ephemeral=True)
        await log(ctx, f"REQ: Refreshed the event file\n")
        await ctx.response.send_message(f"events have been updated up to {last}", ephemeral=True)
        return None
    except ValueError:
        ctx.response.send_message("Error during the updating of the event data.", ephemeral=True)
        return 1


"""SEARCHING COMMANDS (GENERAL): NO FILE MODIFICATION"""


@bot.tree.command(name="upcoming", description="List the N upcoming CTFs events.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def upcoming_ctf(ctx: discord.Interaction, max_events: int = MAX_EVENT_LIMIT):
    """List X number of the upcoming CTFs based on the UPCOMING file's content"""

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

                event_info = f"Weight: {event['weight']} | {event['format']} | starts : <t:{int((datetime.fromisoformat(event['start'])).timestamp())}:R>" # format for the output of the CTF upcoming lists for each event
                embeded_message.add_field(name=event['title'], value=event_info, inline=False)

                count += 1

            if (count >= max_events):
                break
    except ValueError:
        ctx.response.send_message("Error listing all the events, please contact an admin if this persists.", ephemeral=True)
        return 1
    embeded_message.set_author(name="CTFTIME API DATA", url="https://ctftime.org/event/list/upcoming", icon_url=author_icon)
    embeded_message.set_footer(text="For more event use /upcoming {number}\nYou can also learn more about a specific event using /search {name of the event}", icon_url=footer_icon)

    embeded_message.set_thumbnail(url=optional_thumbnail)

    await ctx.response.send_message(embed=embeded_message, ephemeral=True)
    return None

@bot.tree.command(name="listevents", description="list all registered events on the current server.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def list_registered_events(ctx: discord.Integration):
    """list all the files in the current events directory and prints some info"""
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
            message_link = f"https://discord.com/channels/{ctx.guild.id}/{CTF_JOIN_CHANNEL[ctx.guild.name]}/{individual_event[5]}"
            event_info = f"Weight: {individual_event[1]} | starts: <t:{int((datetime.fromisoformat(individual_event[2])).timestamp())}> | Event ID: `{individual_event[7]}` | channel: {event_chan.mention} | {message_link}" # format for the output of the Currently registered CTF
            embeded_message.add_field(name=individual_event[0], value=event_info, inline=False)
    except ValueError:
        await ctx.response.send_message('error using data.', ephemeral=True)
        return 1

    embeded_message.set_footer(text="You can learn more about a specific event by joining the event directly or by using /registered_search {eventID}", icon_url=footer_icon)

    await ctx.response.send_message(embed=embeded_message, ephemeral=True)
    return None

# @bot.tree.command(name="listpasts", description="List all past events on the current server (imperfect, to stay disabled).", guild=discord.Object(id=DISCORD_GUILD_ID))
# async def list_pasts_events(ctx: discord.Integration):
#     """basically the listevents command with the PAST_CTF_DIR and some different text in embedded msg"""
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

@bot.tree.command(name="search", description="Will search the data of the upcoming CTFs, query can be either an integer or a string.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def search_json(ctx: discord.Interaction, query: str = None):
    """search the upcoming file for matches, can use integer for weight search, for strings for name/tag search"""

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
                event_info = f"Weight: {event['weight']} | {event['format']} | Starts: <t:{int((datetime.fromisoformat(event['start'])).timestamp())}> => [CTFTIME]({event['ctftime_url']})\n"
                count += 1
                embeded_message.add_field(name=f"**__{event['title']}__**", value=event_info, inline=False)
            else:
                continue
    except ValueError:
        await ctx.response.send_message("Error crafting the response.", ephemeral=True)
        return 1

    embeded_message.set_author(name="CTFTIME API DATA", url="https://ctftime.org/event/list/upcoming", icon_url=author_icon)
    embeded_message.set_footer(text="you can learn more about a specific event using /search {name of the event}", icon_url=footer_icon)
    await log(ctx, f"GET: searched for {query}\n")
    await ctx.response.send_message(embed=embeded_message, ephemeral=True)
    return None

@bot.tree.command(name="registered_search", description="Search data on a currently registered event using its ID.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def search_registered_events(ctx: discord.Integration, event_id: str):
    """search the directory for current events using its ID or associated role name"""

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

    embeded_message.set_author(name="CTF INFORMATION", url=full_data['url'], icon_url=author_icon)
    embeded_message.add_field(name="Weight", value=f"**{full_data['weight']}**", inline=True)
    embeded_message.add_field(name="Get the role here:", value=f"{message_link}", inline=True)
    embeded_message.add_field(name="Starts:", value=f"<t:{int((datetime.fromisoformat(full_data['start'])).timestamp())}>", inline=False)
    embeded_message.add_field(name="Ends:", value=f"<t:{int((datetime.fromisoformat(full_data['start'])).timestamp())}>", inline=True)
    embeded_message.add_field(name="CTF links:", value=f"[CTFd]({full_data['url']})\n[CTFTIME]({full_data['ctftime_url']})", inline=False)


    ctfrei_logo = "https://cdn.discordapp.com/attachments/1167256768087343256/1202189774836731934/CTFREI_Banniere_920_x_240_px_1.png?ex=67162479&is=6714d2f9&hm=c649d21b2152c0200b9466a29c09a04865387410258c1c228c8df58db111c539&"

    embeded_message.set_thumbnail(url=full_data['logo']) if full_data['logo'] else embeded_message.set_thumbnail(url=ctfrei_logo)

    embeded_message.set_image(url=ctfrei_logo)

    await ctx.response.send_message(embed=embeded_message, ephemeral=True)

    return None


"""SEARCHING COMMANDS (CTFs channel): NO FILE MODIFICATION"""


@bot.tree.command(name="info", description="displays info on current channel's CTF.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def get_info(ctx: discord.Interaction):
    """displays info on current channel's CTF"""
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

        print(event_data)
        embeded_message = await send_event_info(event_info=event_data, id=1)
    except ValueError:
        await ctx.response.send_message("Error retrieving the info.", ephemeral=True)
        return 1
    await log(ctx, f"GET: Event info for {event_data['title']}\n")
    await ctx.response.send_message(embed=embeded_message, ephemeral=True)
    return None

@bot.tree.command(name="description", description="displays the description on current channel's CTF.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def get_description(ctx: discord.integrations):
    """displays the description of the current channel's CTF"""
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
    await log(ctx, f"GET: Event description for {event_data['title']}\n")
    await ctx.response.send_message(f"Here is the description of **{event_data['title']}**:\n{event_data['description']}", ephemeral=True)
    return None

@bot.tree.command(name="vote", description="start the vote on current channel's CTF. (only if over)", guild=discord.Object(id=DISCORD_GUILD_ID))
async def event_democracy(ctx: discord.integrations, grade: Literal["Absolute Trash", "Not Worth", "OK tier", "Banger"]):
    """Allow users to give a grade to an event between 4 different possibilities"""


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

@bot.tree.command(name="end", description="End the CTF on current channel's CTF.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def end_event(ctx: discord.integrations):
    """Moves the CTF file and channel to the archive, effectively stopping it from beeing seen as currently running"""

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
        await ctx.channel.edit(category=archive_category, sync_permissions=True)
        role = ctx.guild.get_role(data['role_id'])
        if role:
            await role.delete()
        await log(ctx, f"EDIT: Ended event for {data['title']}\n")
        await ctx.response.send_message("CTF was ended successfully.")
        return None
    except ValueError:
        await ctx.response.send_message("Error retrieving the info.", ephemeral=True)
        return 1

# add here summary when done

"""ONGOING / TESTING / DEV"""

# # TO BE ADDED
# # Make a summary of a past event, (mostly /info with the amount of ppl that have the role in question, and the average grade given + number of vote)
# @bot.tree.command(name="summary", description="displays info and grade on current channel's CTF", guild=discord.Object(id=DISCORD_GUILD_ID))
# async def event_summary(ctx: discord.integrations):
#     print(1)


"""HELP"""


@bot.tree.command(name="help", description="Help command.", guild=discord.Object(id=DISCORD_GUILD_ID))
async def event_summary(ctx: discord.Interaction, commands: Literal["listevents", "upcoming", "refresh", "search", "registered_search", "quickadd", "info, description, vote, end"]):


    error_server="if the command is not responding it is most likely to be a server side error.\nPlease contact an admin to look into it."

    if commands == "listevents":
        com="Listevents"
        embeded_message = discord.Embed(
            title=f"__{com}__",
            description=f"{com} is a command made to list currently registered events on the server.\nIt'll list all the events that are still running on the server, and give the user :\n- Event weight\n- Start date\n- Event ID\n- Event channel and link the message to get the related role.",
            color=discord.Color.pink()  # Color of the side bar (you can change the color)
        )
        embeded_message.set_author(name="CTFREI HELP", url="https://github.com/Lawcky/CTFREI-Bot/", icon_url=author_icon)

        format = f"`/{com} [no arguments]`"
        usage_exemple = f"`/{com}`"
        embeded_message.set_footer(text=error_server, icon_url=footer_icon)
        embeded_message.add_field(name=f"**{com}** Command Format", value=format, inline=False)
        embeded_message.add_field(name=f"**{com}** Command Example", value=usage_exemple, inline=False)

        await ctx.response.send_message(embed=embeded_message, ephemeral=True)

    elif commands == "upcoming":
        com="Upcoming"
        embeded_message = discord.Embed(
            title=f"__{com}__",
            description=f"{com} is a command made to list upcoming events on CTFTIME.\nIt'll list all the events that are coming based on a cache file, and give the user :\n- Name of the event\n- Event weight\n- Event format\n- Start date.",
            color=discord.Color.pink()  # Color of the side bar (you can change the color)
        )
        embeded_message.set_author(name="CTFREI HELP", url="https://github.com/Lawcky/CTFREI-Bot/", icon_url=author_icon)

        format = f"`/{com} [OPTIONAL number->INT]`"
        usage_exemple = f"`/{com}`\n`/{com} 15`"
        embeded_message.set_footer(text=error_server, icon_url=footer_icon)
        embeded_message.add_field(name=f"**{com}** Command Format", value=format, inline=False)
        embeded_message.add_field(name=f"**{com}** Command Example", value=usage_exemple, inline=False)
        embeded_message.add_field(name=f"**{com}** Options Description", value="This value determines the total amount of event to show in one output.\nthe default value is 10 and the maximum is 25.", inline=False)

        await ctx.response.send_message(embed=embeded_message, ephemeral=True)

    elif commands == "refresh":
        com="Refresh"
        embeded_message = discord.Embed(
            title=f"__{com}__",
            description=f"{com} is a very basic command, its only usage is to refresh the upcoming event file.\nThis command is automatically ran every 24h, but can still be used if you need to refresh the event file.",
            color=discord.Color.pink()  # Color of the side bar (you can change the color)
        )
        embeded_message.set_author(name="CTFREI HELP", url="https://github.com/Lawcky/CTFREI-Bot/", icon_url=author_icon)

        format = f"`/{com} [no arguments]`"
        usage_exemple = f"`/{com}`"
        embeded_message.set_footer(text=error_server, icon_url=footer_icon)
        embeded_message.add_field(name=f"**{com}** Command Format", value=format, inline=False)
        embeded_message.add_field(name=f"**{com}** Command Example", value=usage_exemple, inline=False)

        await ctx.response.send_message(embed=embeded_message, ephemeral=True)

    elif commands == "search":
        com="Search"
        embeded_message = discord.Embed(
            title=f"__{com}__",
            description=f"{com} is a command used to retrieve more information about __upcoming__ CTF events.\nIt can take 2 type of queries, it can search by CTF names, or use a weight range, the result of the command is a list.",
            color=discord.Color.pink()  # Color of the side bar (you can change the color)
        )
        embeded_message.set_author(name="CTFREI HELP", url="https://github.com/Lawcky/CTFREI-Bot/", icon_url=author_icon)

        format = f"`/{com} [query: INT or query: STR]`"
        usage_exemple = f"`/{com} HTB`\n`/{com} 20`\n`/{com} LakeCTF Quals 24-25`"
        embeded_message.set_footer(text=error_server, icon_url=footer_icon)
        embeded_message.add_field(name=f"**{com}** Command Format", value=format, inline=False)
        embeded_message.add_field(name=f"**{com}** Command Example", value=usage_exemple, inline=False)
        embeded_message.add_field(name=f"**{com}** Options Description", value="The **search by name** is a simple string search (not case sensitive).\n\nThe **weight search** is using a range (default is 4) allowing to list the upcoming event between a certain difficulty, for exemple if you search for 20 you'll get a list of events between 16 and 24, which is usally pretty beginner friendly for CTFs.", inline=False)
        embeded_message.add_field(name=f"**{com}** Options info", value="For the name search, the str must be at least 3 char long.\nFor the weight range search, the int must be maximum 2 units (0-99).", inline=False)

        await ctx.response.send_message(embed=embeded_message, ephemeral=True)

    elif commands == "registered_search":
        com="Registered_search"
        embeded_message = discord.Embed(
            title=f"__{com}__",
            description=f"Registered\\_search is a command use to retrieve more information about __ongoing__ CTF events on the server.\nIt takes the event ID as an input to retrieve the CTF's data (get them with /listevents), you can also give the role of associated to the event.",
            color=discord.Color.pink()  # Color of the side bar (you can change the color)
        )
        embeded_message.set_author(name="CTFREI HELP", url="https://github.com/Lawcky/CTFREI-Bot/", icon_url=author_icon)

        format = f"`/{com} [id: STR or role: STR]`"
        usage_exemple = f"`/{com} d62cd16c`\n`/{com} exemple_quals_2024`"
        embeded_message.set_footer(text=error_server, icon_url=footer_icon)
        embeded_message.add_field(name=f"**{com}** Command Format", value=format, inline=False)
        embeded_message.add_field(name=f"**{com}** Command Example", value=usage_exemple, inline=False)

        await ctx.response.send_message(embed=embeded_message, ephemeral=True)

    elif commands == "quickadd":
        com="Quickadd"
        embeded_message = discord.Embed(
            title=f"__{com}__",
            description=f"{com} is the command to automatically add a CTF to a server.\nTo register a new event for the server you need :\n- the name of the CTF as it is written in CTFTIME or `/upcoming` output.\n- to create a name for the role (more information later about naming format).",
            color=discord.Color.pink()  # Color of the side bar (you can change the color)
        )
        embeded_message.set_author(name="CTFREI HELP", url="https://github.com/Lawcky/CTFREI-Bot/", icon_url=author_icon)

        format = f"`/{com} [rolename: STR] [ctfname: STR]`"
        usage_exemple = f"`/{com} htb_uni_2024 HTB University CTF 2024`\n`/{com} saarCTF_2024 saarCTF 2024`"
        restrictions = "There are a set of restrictions for this command to work.\nThose restrictions are:\n- The event was not found using your query, or more than 1 event were found.\n- The CTF is already registered on the server (`/listevents`).\n- The given role already exists on the server.\n- A channel with that name already exists on the server.\n- The event is already over."
        search_info = "**Note**: The searching mecanism is the exact same as the `/search` command\nFor the `/quickadd` command to work you need to make sure `/search` with your query returns only 1 CTFs using a string as input."
        role_format = "The role name for each CTF has to be created for every new event, to avoid any problem make sure to use a format that'll last in time, for exemple:\n- For each year's HackTheBox's Uni CTF a good format would be htb_university_YEAR\n- For a CTF with quals and a final a good format would be ctfname_quals_YEAR or ctfname_final_YEAR\nand so on..."
        role_warning = "**Warning:** Since the Rolename's creation is up to the user and will be used to create a 'persistent' role on the server and a channel as well, it is obvious that no abuse will be tolerated, we hope that we wont have to take meaningless actions."
        embeded_message.set_footer(text=error_server, icon_url=footer_icon)
        embeded_message.add_field(name=f"**{com}** Command Format", value=format, inline=False)
        embeded_message.add_field(name=f"**{com}** Command Example", value=usage_exemple, inline=False)
        embeded_message.add_field(name=f"**{com}** Command Restrictions", value=restrictions, inline=False)
        embeded_message.add_field(name=f"**{com}** Search Mecanism", value=search_info, inline=False)
        embeded_message.add_field(name=f"**{com}** RoleName Format", value=role_format, inline=False)
        embeded_message.add_field(name=f"**{com}** RoleName Warning", value=role_warning, inline=False)

        await ctx.response.send_message(embed=embeded_message, ephemeral=True)

    elif commands == "info, description, vote, end":
        com='"info", "description", "vote" and "end" commands'
        embeded_message = discord.Embed(
            title=f"__{com}__",
            description=f"{com} are used to manage currently registered CTF events on the server, these commands can **only** be ran inside a CTF's channel, these channels are listed in /listevents.",
            color=discord.Color.pink()  # Color of the side bar (you can change the color)
        )
        embeded_message.set_author(name="CTFREI HELP", url="https://github.com/Lawcky/CTFREI-Bot/", icon_url=author_icon)

        format = f"`/info [no arguments]`\n`/description [no arguments]`\n`/vote [value: Litteral]`\n`/end [no arguments]`"
        usage_exemple = f"`/info`\n`/description`\n`/vote Banger`\n`/end`"
        embeded_message.set_footer(text=error_server, icon_url=footer_icon)
        embeded_message.add_field(name=f"**{com}** Command Format", value=format, inline=False)
        embeded_message.add_field(name=f"**{com}** Command Example", value=usage_exemple, inline=False)
        embeded_message.add_field(name=f"**{com}** Important Information", value="These commands only work when ran in currently running event, (events that were started using this bot, and were not ended using /end)", inline=False)

        await ctx.response.send_message(embed=embeded_message, ephemeral=True)
    else:
        await ctx.response.send_message("Use this command to learn about specific command uses.", ephemeral=True)


"""DISCORD SETUP"""


@bot.command(name="setup-ctfrei")
async def setup_dir(ctx: discord.integrations):
    """setup command for each server to setup the file system (does not appear as an actual command on servers)"""
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

async def refresh_interactions(DISCORD_GUILD_ID, Channel_id):
    """function to refresh the interactions that are not expired post restart"""
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

@bot.tree.command(name="sync", description="commande pour sync les commandes (dev only)")
async def sync(ctx: discord.Interaction):
    """sync commands with the given DISCORD_GUILD_ID"""
    await ctx.response.defer(ephemeral=True)
    await log(ctx, f"REQ: Synced the Bot\n")
    await bot.tree.sync(guild=discord.Object(id=DISCORD_GUILD_ID))
    await refresh_interactions(ctx.guild.id, CTF_JOIN_CHANNEL[ctx.guild.name])
    await ctx.edit_original_response(content="Commands & interactions synced successfully!")

"""refresh every 24h of event cache"""
@tasks.loop(hours=24)
async def automatic_refresh( ):
    try:
        api_call("https://ctftime.org/api/v1/events/?limit=100", UPCOMING_CTFTIME_FILE)
    except Exception as e:
        print(f"Refresh now: {e}")

"""BOT STARTING AND CHECKING"""


async def basic_setup():
    """minimum necessary to start the bot, is checked as startup"""
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

        if (not p.isfile("log/commands.log")):
            with open("log/commands.log", 'x') as filecreation:
                filecreation.write("Here starts the log file for the CTFREI bot.\n")

        print('SETUP HAS BEEN CHECKED')
        return None
    except ValueError:
        print("Error during SETUP CHECKING")
        return 1

@bot.event
async def on_ready():
    """bot startup routine"""
    await basic_setup()
    await bot.tree.sync()
    await refresh_interactions(DISCORD_GUILD_ID, CTF_JOIN_CHANNEL['Test-Bot-CTFREI']) # refresh all current interactions, and delete old join message
    automatic_refresh.start()

    print(f'Logged in as {bot.user}')

if CTFREI == '__GOATS__': # FACT
    bot.run(TOKEN)
