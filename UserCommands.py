from discord.ext import commands
import logging
import random
import requests


class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.responses = ['It is certain.', 'It is decidedly so.', 'Without a doubt.', 'Yes - definitely.',
                          'You can count on it.', 'As I see it, yes.', 'Most likely.', 'Outlook is good.', 'Yes.',
                          'Signs point to yes.', 'Not sure, try again.',
                          'Ask me again later, I don\'t feel like answering.',
                          'Better not tell you now and spoil the surprise.', 'Can\'t predict now.',
                          'Concentrate and ask again.',
                          'Don\'t count on it.', 'Nope.', 'My sources say no.', 'Outlook ain\'t good.', 'Hell, no.']

    @commands.command(name='8ball')
    async def eight_ball(self, ctx, *, arg):
        if len(arg) == 0:
            logging.info(str(ctx.message.author) + ' prompted 8ball without a question.')
            await ctx.send('{0.message.author.mention}, please provide a question! It doesn\'t make sense for me to '
                           'respond without a question.'.format(ctx))

        val = random.randint(0, len(self.responses))
        shuff_responses = random.sample(self.responses, len(self.responses))
        response = shuff_responses[val]

        msg = '{0.message.author.mention}: '.format(ctx) + ' ' + response
        logging.info(str(ctx.message.author) + ' prompted 8 ball with a question and got a response.')
        await ctx.send(msg)

    @commands.command()
    async def gwiki(self, ctx, *, arg):
        r = requests.get('https://gundam.fandom.com/api/v1/Search/List?query='+arg)
        response = r.json()
        if r.status_code == 400 or r.status_code == 404:
            logging.info(str(ctx.message.author) + ' prompted gwiki with a bad query.')
            await ctx.send('{0.message.author.mention}, it looks like your search wasn\'t allowed by the wiki.'
                           'Try with a different query.'.format(ctx))
            return
        else:
            if len(response["items"]) == 0:
                logging.info(str(ctx.message.author) + ' prompted gwiki with a query that returned nothing.')
                await ctx.send('{0.message.author.mention}, I can\'t find anything with that search.'
                               ' Try again?'.format(ctx))
                return
            url = response["items"][0]["url"]
            logging.info('{0} prompted gwiki with a good query and was served a page.'.format(str(ctx.message.author)))
            await ctx.send('{0.message.author.mention}, looking for this?: '.format(ctx) + url)


def setup(bot):
    bot.add_cog(UserCommands(bot))
