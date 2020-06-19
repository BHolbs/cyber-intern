from discord.ext import commands
import logging

logging.basicConfig(filename='log', level=logging.INFO)
logging.info("Starting.")
file = open('key', mode='r')
key = file.read()
file.close()
logging.info("Key retrieved, booting bot.")

startup_extensions = ['UserCommands', 'AdminCommands']

bot = commands.Bot(command_prefix='!')

for extension in startup_extensions:
    try:
        bot.load_extension(extension)
    except Exception as e:
        exc = '{}: {}'.format(type(e).__name__, e)
        print('Failed to load extension {}\n{}'.format(extension, exc))
        quit()

bot.run(key)


# async methods
@bot.event
async def on_ready():
    logging.info('Logged in as ' + str(bot.user.name) + ' with id: ' + str(bot.user.id))
    logging.info('--------------------------------------------------------------------------')
