# CTFREI-Bot
A discord bot made to manage CTF events on a discord Server.

This bot's main goal is to be able to offer to anyone on a server the capabilities to be able to create a dedicated channel & event for people to join the CTF.

The bots Data is fetched from CTFTIME's API.

this bot comes with 12 commands right now (i keep making changes when i have time),
there are 2 types of commands : those that be ran everywhere, and those that can only be ran inside a CTF channel (created by the bot).

# How to setup

To setup the bot its pretty simple, most of the changes must be done inside of the conf.json file (you might want to change some hardcoded strings inside main.py as well),

first download the git : 

```git clone https://github.com/Lawcky/CTFREI-Bot.git```

add a discord bot token in conf.json (you can create the token [here](https://discord.com/developers/applications)

for the bot to work he needs : 
- a specific discord bot channel (to send the messages related to joining an event)
- a discord CTF category (where he'll create all the CTF channels)
- a discord archive category (where he'll send CTF channels that are over)
- an discord announce channel (where he'll send a "cleaner" message to ping the server, default language is french 🐔 for this)

go on the bot channel (inside the CTF category  is better) and send `/setup-ctfrei`, this will create the files and directories needed for the bot to run correctly (make sure the bot is running and has the permissions on the OS he is on), and it'll also print in the console the informations you need to fill out the conf.json file (you still need to give things like the archive category or the announce channel which will not be given by the command here).

once everything is setup you can run `/sync` on the server and start using commands !

## DevPod

<a href="https://devpod.sh/open#https://github.com/Lawcky/CTFREI-Bot"><img src="https://camo.githubusercontent.com/8ba20cf8d294f8faa1859e1940f591333280802bfdc79accb6d1cfd5e54f1347/68747470733a2f2f646576706f642e73682f6173736574732f6f70656e2d696e2d646576706f642e737667" alt="Open in DevPod!" data-canonical-src="https://devpod.sh/assets/open-in-devpod.svg" style="max-width: 100%;"></a>

# Commands

`{}` represents an optionnal parameter
`[]` represent a required parameter

## Basic Commands (run anywhere on the server)

`/upcoming {int}` : This command will list the upcoming CTF events and display the relative time before the start, it not making a live request but instead uses a files data (in json) as cache.
you can also add a number after for how much upcoming events you want, default value is 10, maximum value is 25 (above discord may crash the response as too long).

<img src="https://github.com/user-attachments/assets/b5ddf244-6ef1-4bf4-b549-1b889701219c" height=250>

`/search [int or string]` : This command allows 2 things : to get more information about a specific event by searching by event name like `/search HTB Uni` (not case sensitive) or to filter upcoming events by weight range (`/search 20` will output the upcoming events with a weight between 16 and 24 since the default range is 4)

<img src="https://github.com/user-attachments/assets/459a275d-824f-4e0e-afb1-4e293e93f094" height=250><img src="https://github.com/user-attachments/assets/f2cbec05-6250-4984-b0ec-e3a4d0b54028" height=250>

`/quickadd [name of the role] [name of the event]` : This command allow any person on the server to add an event, its takes 2 parameters, the first one is a string to name the event, this string will be used during the creation of the channel & the role, the second parameter is the actual name of the event, the search is the same system as the `/search` command so if you can have only 1 result as output for the `/search` command it'll work for the quickadd command.
Many restrictions are in place here to avoid dupplicate events, role already existing, channel with same name already existing etc...

<add image later>

`/listevents` : This command will list currently registered (either running or upcoming) events on the server, with the relative time until it starts/end and additional infos like its ID on the server.

<img src="https://github.com/user-attachments/assets/1c10531a-79d1-4c49-ab21-46b71b633cce" height=250>

`/registered_search [event id]` : This command will give you informations about a registered event on the server (without needing to be participating), it uses the event id given by `/listevents`

<img src="https://github.com/user-attachments/assets/b027092d-77f6-4482-beea-45a3bc8cd8fc" height=250>

## CTF Commands (can be ran only inside channels created by the bot)

`/info` : This will print out some informations on the event. (this message is sent by default inside the channel when it is created by `/quickadd`)

<img src="https://github.com/user-attachments/assets/717bba4e-558e-4f13-8f16-eae91287419e" height=250>

`/description` : Well... pretty straightforward, will give you the description of the ctf event

<img src="https://github.com/user-attachments/assets/cc3dee34-04de-4b50-8c13-cac9dbec00a3" height=125>

`/vote` : This command allow everyone with access to the channel to give their opinion (from 1 to 4) about the event, you can only vote once since a new vote will overwrite past votes.
(side note: for now voting is pretty much useless since no commands uses the output, so for now it is only for data inside the event files for the person hosting)

<img src="" height=250>

`/end` : Once the CTF is over you can run this command, it'll archive the channel, remove the event from the currently running ones (for `/listevents`) and later will also delete the related role to avoid flooding (not implemented yet)

![image](https://github.com/user-attachments/assets/c0fa75fb-ad7b-4d00-9e28-a6b5c1c3045d)

## Other commands

`/refresh`

`/sync`

`/help [CTFREI command]`
