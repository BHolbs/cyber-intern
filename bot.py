import discord
import commands

print("Starting.")
file = open('key', mode='r')
key = file.read()
file.close()
print("Key retrieved, booting bot.")
client = discord.Client()

bad_words = list()


@client.event
async def on_message(message):
    # bot should not respond to itself
    if message.author == client.user:
        return

    if message.content.startswith('!eightball'):
        out = commands.eightball(message)
        await message.channel.send(out)
        return

    if message.content.startswith('!gwiki'):
        out = commands.wikihandler(message)
        await message.channel.send(out)
        return

    # only check if bad words isn't an empty list
    if len(bad_words) > 0:
        for i in range(0, len(bad_words)):
            if bad_words[i] in message.content:
                print(str(message.author) + ' said a banned word.')
                msg = 'Please don\'t use banned words, {0.author.mention}'.format(message)
                await message.delete()
                await message.channel.send(msg)
                return


@client.event
async def on_ready():
    print('Logged in as ' + str(client.user.name) + ' with id: ' + str(client.user.id))
    print('--------------------------------------------------------------------------')


client.run(key)