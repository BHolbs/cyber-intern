import discord
from discord.ext import commands
import logging
import os

# spin up the bot
logging.basicConfig(filename='log', level=logging.INFO)
logging.info("Starting.")
file = open('key', mode='r')
key = file.read()
file.close()
logging.info("Key retrieved.")

file = open('connection_string', mode='r')
connection_string = file.read()
os.environ['CONNECTION_STRING'] = connection_string
connection_string = str()
file.close()
logging.info("Connection string set, booting up.")

# set up extensions, assign command prefix
startup_extensions = ['UserCommands', 'AdminCommands']
bot = commands.Bot(command_prefix='!')

# load extensions
for extension in startup_extensions:
    try:
        bot.load_extension(extension)
    except Exception as e:
        exc = '{}: {}'.format(type(e).__name__, e)
        logging.error('Failed to load extension {0}\n{1}'.format(extension, exc))
        quit()


# async methods
@bot.event
async def on_ready():
    logging.info('Logged in as ' + str(bot.user.name) + ' with id: ' + str(bot.user.id))
    logging.info('--------------------------------------------------------------------------')
    logging.info('Performing startup checks.')
    guilds = bot.guilds
    if len(guilds) > 1:
        logging.error('I\'m in multiple servers. I can only be in one right now.')
        quit()

    # the interns-assemble channel already exists, so i can just grab that id once i get there, but
    # the intern-log channel might not when i deploy this, so let's have it create that channel and category
    need_to_create = True
    for channel in guilds[0].channels:
        if 'INTERN_LOG_CHANNEL_ID' in os.environ:
            need_to_create = False
            break

        if channel.name == 'interns-assemble':
            os.environ['MOD_CHANNEL_ID'] = str(channel.id)

        if channel.name == 'intern-log':
            for subchannel in channel.channels:
                if subchannel.name == 'intern-log-messages':
                    os.environ['INTERN_LOG_CHANNEL_ID'] = str(subchannel.id)

    if need_to_create:
        intern = None
        god = None
        for role in guilds[0].roles:
            if role.name == 'interns':
                intern = role
            elif role.name == 'gods':
                god = role

        overwrites = {
            guilds[0].default_role: discord.PermissionOverwrite(read_messages=False),
            guilds[0].me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            intern: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            god: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        category = await guilds[0].create_category('intern-log', overwrites=overwrites)
        channel = await guilds[0].create_text_channel('intern-log', overwrites=overwrites, category=category)
        await channel.send('Hello! This is the start of my logging channel!')

    await guilds[0].get_channel(int(os.environ['INTERN_LOG_CHANNEL_ID'])).send('Cyber intern online!')


bot.run(key)
