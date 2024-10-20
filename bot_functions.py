import requests
from bs4 import BeautifulSoup
import discord
import json


# retrive the upcoming CTF events and data
async def extract_ctf_data(url, filename):
    try:
        headers = {
            'User-Agent': 'curl/7.68.0'  # Mimicking a curl request
        }

        response = requests.get(url, headers=headers)

        # Check request's status code
        if response.status_code != 200:
            print(f"Failed to retrieve content: {response.status_code}")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        table = soup.find('table', {'class': 'table table-striped'})
        if table is None:
            print("Table not found on the page")
            return None

        ctf_data = []
        rows = table.find_all('tr')[1:]  # Skip the first header row

        if not rows:
            print("No rows found in the table.")
            return None

        for row in rows:
            columns = row.find_all('td') # retrieve all data
            links = row.find('a') # retrieve the links to get an easy access
            # Extract data for each field
            event_name = columns[0].get_text(strip=True)
            event_date = columns[1].get_text(strip=True)
            event_format = columns[2].get_text(strip=True)
            event_location = columns[3].get_text(strip=True)
            event_weight = columns[4].get_text(strip=True)
            event_notes = columns[5].get_text(strip=True)
            event_link = links.get('href')

            # Add the extracted data to the list
            ctf_data.append({
                'name': event_name,
                'date': event_date,
                'format': event_format,
                'location': event_location,
                'weight': event_weight,
                'notes': event_notes,
                'link': 'https://ctftime.org' + event_link # recreate the link
            })

        # this is to save data so that you dont spam the website with useless requests
        # you can customize the refresh timing in conf.json

        with open(filename, 'w') as json_file:
            json.dump(ctf_data, json_file, indent=4)
        print(f"CTF data has been saved to {filename}")

        return ctf_data
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
#look inside the Json data files for match
async def search_ctf_data(filename, query, WEIGHT_RANGE):
    
    match = [] # array of match
    with open(filename) as json_file:
        events = json.load(json_file)

        if len(query) <= 2: # set as 2 or 5, if set as 2 you need to enter an integer to look for a list of CTFs, if 5 you could enter a float directlybut less easier for name searches 
            try:
                # Attempt to convert the query to a float
                weight_query = float(query)
                # range can be set in the conf file
                min_weight = weight_query - WEIGHT_RANGE
                max_weight = weight_query + WEIGHT_RANGE

                for event in events:
                    event_weight = float(event['weight'])  # Convert event weight to float
                    if min_weight <= event_weight <= max_weight:
                        match.append({
                            'name': event['name'],
                            'date': event['date'],
                            'format': event['format'],
                            'location': event['location'],
                            'weight': event['weight'],
                            'link': event['link']
                        })
            except ValueError:
                print(f"no result found: {query}") 

        else:
            for event in events:
                if (query.lower() in event['name'].lower()):
                    match.append({
                        'name': event['name'],
                        'date': event['date'],
                        'format': event['format'],
                        'location': event['location'],
                        'weight': event['weight'],
                        'link': event['link']
                    })

        return match



# Create a private text channel in the specified category for the role
async def create_private_channel(guild, category: discord.CategoryChannel, role: discord.Role):
    
    CTFREI_role = discord.utils.get(guild.roles, name="CTFREI")  # Get the CTFREI role

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),  # Deny access to everyone
        role: discord.PermissionOverwrite(read_messages=True),  # Grant access to users with the specified role
        CTFREI_role: discord.PermissionOverwrite(read_messages=True)  # Grant access to users with the CTFREI role
    }

    private_channel = await guild.create_text_channel(name=f"🚩-{role.name}", category=category, overwrites=overwrites)

    return private_channel

#retrieve a message and reply to it
async def reply_message(ctx, channel: discord.TextChannel, message_id: int, response: str):

    if channel is None:
        await ctx.send("Error finding the join channel")
        print("Channel not found.")
        return

    try:
        message = await channel.fetch_message(message_id)

        await message.reply(response)
        return 1
    except discord.NotFound:
        await ctx.send("Error finding the actual message")
        return None
    except discord.Forbidden:
        await ctx.send("I don't have permission to fetch or reply to that message.")
        return None
    except discord.HTTPException:
        await ctx.send("Something went wrong while fetching the message.")
        return None

# will retrieve a channel's category based on its ID (to make sure channels are not created everywhere)
def get_category_by_id(guild: discord.Guild, category_id: int):
    
    for category in guild.categories:
        if category.id == category_id:
            return category
    return None

# will check if the channel name already exists (to make sure channels are not created everywhere)
def get_channel_by_name(guild: discord.Guild, channelname: str):
    
    for channel in guild.channels:
        if channel.name == channelname:
            return channel
    return None

async def search_event_data(filename, role: discord.Role):
    with open(filename, 'r') as events_file:
        events_data = json.load(events_file)

    for event in events_data:
        for rolename in event:
            if rolename.lower() == role.name.lower():
                return event[role.name] #returns the information about the CTF

    return None
