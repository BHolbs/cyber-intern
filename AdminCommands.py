import os
import discord
from discord.ext import commands
from datetime import datetime, timedelta
import logging
from pymongo import MongoClient

# use for scheduled job to unban
from apscheduler.schedulers.asyncio import AsyncIOScheduler


# returns how many seconds long the ban is, or -1 if the duration is formatted improperly
def durationGood(duration):
    # initialize to -1, so we can skip it rather than require both flags even if a value is 0
    flags = {'d': -1, 'h': -1, 'm': -1}
    allowed = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'd', 'h', 'm'}

    duration = duration.lower()
    for i in range(len(duration)):
        if duration[i] not in allowed:
            return -1

        # days
        if duration[i] == 'd':
            if flags['d'] != -1:
                return -1
            else:
                flags['d'] = i

        # hours
        if duration[i] == 'h':
            if flags['h'] != -1:
                return -1
            else:
                flags['h'] = i

        if duration[i] == 'm':
            if flags['m'] != -1:
                return -1
            else:
                flags['m'] = i

    flags_in_order = {key: value for key, value in sorted(flags.items(), key=lambda item: item[1])}
    seconds = 0
    start = 0
    for key in flags_in_order:
        if key == 'd' and flags_in_order[key] != -1:
            end = flags_in_order[key]
            seconds += (int(duration[start:end]) * 24 * 60 * 60)
            start = end + 1
        if key == 'h' and flags_in_order[key] != -1:
            end = flags_in_order[key]
            seconds += (int(duration[start:end]) * 60 * 60)
            start = end + 1
        if key == 'm' and flags_in_order[key] != -1:
            end = flags_in_order[key]
            seconds += (int(duration[start:end]) * 60)
            start = end + 1

    return seconds


async def hasGoodTarget(ctx, member: discord.Member = None):
    trying_to_ban_mod = False
    for role in member.roles:
        if role.name == 'Cyber Intern':
            continue

        if role.permissions.kick_members or role.permissions.ban_members:
            trying_to_ban_mod = True
            break

    if trying_to_ban_mod:
        await ctx.message.delete()
        await ctx.guild.owner.send("Hello!\n\n"
                                   "{0.message.author}"
                                   " in The OPMeatery attempted to ban/kick"
                                   " {1}."
                                   " I am not programmed to allow moderators to ban/kick each other, or gods, but I"
                                   " am programmed to notify you if someone tries.".format(ctx, member))
        return False
    return True


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # only timed bans go into the DB, permanent bans have to be manually unbanned
        # DB, as a free mongodb cluster, only has 512MB of storage, but this should be plenty
        self.bans = MongoClient(os.environ['CONNECTION_STRING'])['cyber-intern'].bans

        # scheduling
        self.scheduler = AsyncIOScheduler()

        # Scheduled task to automatically check for expired bans
        @self.scheduler.scheduled_job('interval', minutes=15)
        async def unban():
            channel = self.bot.get_channel(int(os.environ['INTERN_LOG_CHANNEL_ID']))

            now = datetime.utcnow()
            for ban in self.bans.find({'expiry': {"$lte": now}}):
                await self.bot_unban(ban['member'])

            self.bans.delete_many({'expiry': {"$lte": now}})
            self.nextUnbanAt = self.nextUnbanAt + timedelta(minutes=15)

        self.nextUnbanAt = datetime.utcnow() + timedelta(minutes=15)
        self.scheduler.start()

    # Helper function to validate that admin command was used in a correct channel
    async def sentInPrivateChannel(self, ctx, member: discord.User = None):
        if ctx.channel.id != int(os.environ['MOD_CHANNEL_ID']):
            await ctx.message.delete()
            channel = self.bot.get_channel(int(os.environ['MOD_CHANNEL_ID']))
            await channel.send('{0.message.author.mention}: You can only use administrator commands here.'.format(ctx))
            return False
        if member == ctx.message.author:
            await ctx.message.delete()
            await ctx.channel.send("{0.message.author.mention}: You can't ban/unban/kick yourself, dummy.".format(ctx))
            return False
        # if someone tries to remove the bot with its own commands
        if member.id == 675203071609012247:
            await ctx.channel.send("I can't let you do that, {0.message.author.mention}.")
            return False
        if member is None:
            await ctx.message.delete()
            await ctx.channel.send(
                '{0.message.author.mention}: You have to use the user\'s ID to ban/unban/kick them.'.format(ctx))
            return False

        return True

    # Manual ban command for moderators
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member = None, duration=None, *, reason=None):
        good_target = await hasGoodTarget(ctx, member)
        if not good_target:
            return

        channel_good = await self.sentInPrivateChannel(ctx, member)
        if not channel_good:
            return

        # Account for if no reason given
        if reason is None:
            reason = "Not specified."

        # check if args make sense
        # channel_good already determined if the member being banned is good, so just check duration and reason
        ban_duration_in_seconds = int()
        if duration != '-1':
            ban_duration_in_seconds = durationGood(duration)
            if ban_duration_in_seconds == -1:
                await ctx.channel.send('{0.message.author.mention}: Ban duration poorly formatted.'.format(ctx))
                return

            # calculate ban expiration
            now = datetime.utcnow()
            expiry = datetime(year=now.year, month=now.month, day=now.day, hour=now.hour, minute=now.minute)
            expiry = expiry + timedelta(seconds=ban_duration_in_seconds)

            # ban should be added to the DB AFTER ban goes through
            ban = {'member': member.id, 'expiry': expiry, 'reason': reason}
            timestamp = expiry.strftime('%B %d %Y at %I:%M %p UTC')

            try:
                await member.send("Hello, unfortunately you have been banned from The OPMeatery by the moderation "
                                  "team. \n "
                                  "\t\tReason: {0} \n"
                                  "\n"
                                  "Your ban will automatically expire on: {1}.\n"
                                  "Please allow up to half an hour after this time before contacting the moderation "
                                  "team if your ban appears to have not yet been lifted."
                                  .format(ban['reason'], timestamp))
                # add ban to DB, i only want temp bans in there
                self.bans.insert_one(ban)

            except discord.ext.commands.CommandInvokeError:
                ctx.channel.send("Banned {0.name}#{0.discriminator}, but was unable to message user. "
                                 "Their ban will expire on approximately {1}."
                                 .format(member, timestamp))
        else:
            try:
                await member.send("Hello, unfortunately you have been permanently banned from The OPMeatery by the "
                                  "moderation team. \n"
                                  "\t\tReason: {0} \n"
                                  "\n"
                                  "Your ban will not expire automatically, you must contact the moderation team to "
                                  "appeal. ".format(reason))

            except discord.ext.commands.CommandInvokeError:
                ctx.channel.send("Banned {0.name}#{0.discriminator}, but was unable to message user. "
                                 "Their ban is permanent, and will not expire unless you manually unban them.")

        await ctx.guild.ban(user=member, delete_message_days=1, reason=reason)
        await ctx.message.delete()
        logging.info('{0.message.author} banned user with id: {1.id} with reason: {2}.'
                     .format(ctx, member, reason))

    # Manual kick command for moderators
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def kick(self, ctx, member: discord.Member = None, reason=None):
        good_target = await hasGoodTarget(ctx, member)
        if not good_target:
            return

        channel_good = await self.sentInPrivateChannel(ctx, member)
        if not channel_good:
            return

        if reason is None:
            reason = "Not specified."

        await member.send("Hello, unfortunately you have been kicked from The OPMeatery by the moderation team.\n"
                          "\t\tReason: {0.reason}\n"
                          "\n"
                          "You may rejoin the server immediately, but be aware that a kick is a warning. If you "
                          "continue the behavior that resulted in your kick, you may be banned.".format(reason))
        await ctx.guild.kick(user=member, reason=reason)
        await ctx.message.delete()
        logging.info('{0.message.author} kicked user with id: {1.id} with reason: {2}.'
                     .format(ctx, member, reason))

    # This one is actually fine to be sent in any channel, there's no significant information being forfeited here
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unbancheckwhen(self, ctx):
        out = self.nextUnbanAt.strftime('%B %d %Y at %I:%M %p UTC')
        await ctx.channel.send("The ban list will be checked on {0}.".format(out))
        logging.info('{0.message.author} checked the time for the unban scheduler in channel {1}'
                     .format(ctx, ctx.channel.name))

    # Manual unban command for moderators
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, memberId=None):
        banned_users = await ctx.guild.bans()
        member = None
        for banned in banned_users:
            if banned.user.id == int(memberId):
                member = banned.user
                break

        if member is None:
            ctx.channel.send('{0.message.author.mention}: User is not banned.'.format(ctx))
            return

        channel_good = await self.sentInPrivateChannel(ctx, member)
        if not channel_good:
            return

        result = self.bans.delete_one({'member': member.id})

        await ctx.guild.unban(user=member, reason='Prompted to by {0.message.author}'.format(ctx))
        await ctx.channel.send('{0.message.author.mention}: User has been unbanned. Please reach out to them manually'
                               ' to notify them.'.format(ctx))
        logging.info('{0.message.author} unbanned user with id: {1.id}.'
                     .format(ctx, member))

    # Handler for the bot automatically unbanning members
    async def bot_unban(self, memberId=None):
        channel = self.bot.get_channel(int(os.environ['INTERN_LOG_CHANNEL_ID']))
        guild = channel.guild
        banned_users = await guild.bans()
        member = None
        for banned in banned_users:
            if banned.user.id == int(memberId):
                member = banned.user
                break

        # this is very unlikely to happen, but i want to know if there's a DB mismatch w/ banlist
        if member is None:
            now = datetime.utcnow()
            timestamp = now.strftime('%B %d %Y at %I:%M %p UTC')
            logging.error("Auto unban mismatch. Auto unbanner tried to unban someone not on the ban list."
                          " Member Id provided: {0}".format(memberId))
            await guild.owner.send("Hello. I managed to try to unban someone automatically that wasn't banned. "
                                   "Please notify my developer as soon as possible, he'll know what I mean.\n"
                                   "Please provide the following information:\n"
                                   "\t Error occurred at: {0}.\n"
                                   "\t Error occurred when unbanning user with id: {1} ".format(timestamp, memberId))
            return False

        await channel.send("Unbanned {0.name}#{0.discriminator} automatically.".format(member))
        await guild.unban(user=member, reason='Ban expired.')
        logging.info('I unbanned user with id: {0.id} because ban expired.'.format(member))
        return True


def setup(bot):
    bot.add_cog(AdminCommands(bot))
