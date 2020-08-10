import os
import discord
from discord.ext import commands
from datetime import datetime, timedelta
import logging

# use for emplacing bans in a sorted fashion, and for customizing sorts
#   - bisect for inserting in order
import bisect

# use for scheduled job to unban
from apscheduler.schedulers.asyncio import AsyncIOScheduler


class Ban:
    def __init__(self, user: int(), expiration: datetime, reason):
        self.member = user
        self.expiry = expiration
        self.reason = reason

    def __lt__(self, other):
        return self.expiry < other.expiry

    def __eq__(self, other):
        return self.member == other

    def hasExpired(self, now):
        return now > self.expiry:

    def writeBanToFile(self):
        try:
            f = open("bans", mode='a')
            f.write(str(self.member))
            f.write(',')
            f.write(self.expiry.strftime('%m %d %Y %H:%M'))
            f.write(',')
            f.write(self.reason)
            f.write('\n')
        finally:
            f.close()


# returns how many seconds long the ban is, or -1 if the duration is formatted improperly
def durationGood(duration):
    # initialize to -1, so we can skip it rather than require both flags even if a value is 0
    flags = {'d': -1, 'h': -1}
    allowed = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'd', 'h'}

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

    return seconds


async def hasGoodTarget(ctx, member: discord.Member = None):
    member_roles = list()
    for i in member.roles:
        member_roles.append(i.name)
    trying_to_ban_mod = any(item in ['interns', 'gods'] for item in member_roles)
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
        # only timed bans go in this list, permanent bans have to be manually unbanned
        self.bans = list()

        try:
            f = open('bans', mode='r')
            raw_bans = f.read().splitlines()

            for line in raw_bans:
                chunks = line.split(',')
                self.bans.append(Ban(int(chunks[0]), datetime.strptime(chunks[1], '%m %d %Y %H:%M'), chunks[2]))
        finally:
            f.close()

        # TODO: change this ID when releasing to the official server
        # TODO: consider having a search to find if the channel, and create it if it doesn't exist instead?
        self.internChannelId = 723323448075485237
        self.cyberInternLogChannelId = 723740807433027685

        # scheduling
        self.scheduler = AsyncIOScheduler()

        # Scheduled task to automatically check for expired bans
        @self.scheduler.scheduled_job('interval', seconds=5)
        async def unban():
            channel = self.bot.get_channel(self.cyberInternLogChannelId)
            await channel.send("Hello! I'm checking the ban list to see if anyone's ban has expired.")
            to_remove = list()
            for ban in self.bans:
                if ban.hasExpired(datetime.now()):
                    await self.bot_unban(ban.member)
                    to_remove.append(ban)

            self.bans = [x for x in self.bans if x not in to_remove]
            self.rewriteBanFile()

        self.scheduler.start()

    # Helper function to validate that admin command was used in a correct channel
    async def sentInPrivateChannel(self, ctx, member: discord.User = None):
        if ctx.channel.name != 'interns-assemble':
            await ctx.message.delete()
            channel = self.bot.get_channel(self.internChannelId)
            await channel.send('{0.message.author.mention}: You can only use administrator commands here.'.format(ctx))
            return False
        if member == ctx.message.author:
            await ctx.message.delete()
            await ctx.channel.send("{0.message.author.mention}: You can't ban/unban/kick yourself, dummy.".format(ctx))
            return False
        if member is None:
            await ctx.message.delete()
            await ctx.channel.send(
                '{0.message.author.mention}: You have to use the user\'s ID to ban/unban/kick them.'.format(ctx))

        return True

    # Manual ban command for moderators
    @commands.command()
    @commands.has_any_role('gods', 'interns')
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
            now = datetime.now()
            expiry = now + timedelta(seconds=ban_duration_in_seconds)

            ban = Ban(member, expiry, reason)
            bisect.insort(self.bans, ban)
            timestamp = expiry.strftime('%B %d %Y at %I:%M %p Pacific')

            ban.writeBanToFile()

            await member.send("Hello, unfortunately you have been banned from The OPMeatery by the moderation team. \n"
                              "\t\tReason: {0.reason} \n"
                              "\n"
                              "Your ban will expire on: {1}.\nPlease allow up to an hour after the time given,"
                              " to compensate for potential daylight savings time issues.".format(ban, timestamp))
        else:
            await member.send("Hello, unfortunately you have been permanently banned from The OPMeatery by the "
                              "moderation team. \n"
                              "\t\tReason: {0} \n"
                              "\n"
                              "Your ban will not expire automatically, you must contact the moderation team to appeal."
                              .format(reason))

        await ctx.guild.ban(user=member, delete_message_days=1, reason=reason)
        await ctx.message.delete()
        logging.info('{0.message.author} banned {1.name}#{1.discriminator}, id: {1.id} with reason: {2}.'
                     .format(ctx, member, reason))

    # Manual kick command for moderators
    @commands.command()
    @commands.has_any_role('gods', 'interns')
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
                          "continue the behavior that resulted in your kick, you may be banned. ")
        await ctx.guild.kick(user=member, reason=reason)
        await ctx.message.delete()
        logging.info('{0.message.author} kicked {1.name}#{1.discriminator}, id: {1.id} with reason: {2}.'
                     .format(ctx, member, reason))

    def rewriteBanFile(self):
        # if the list is only 1 element long, just delete the file. other methods will create the file if need be.
        if len(self.bans) == 1:
            os.remove('bans')
        try:
            f = open('bans', mode='w')
            for ban in self.bans:
                f.write(str(ban.member))
                f.write(',')
                f.write(ban.expiry.strftime('%m %d %Y %H:%M'))
                f.write(',')
                f.write(ban.reason)
                f.write('\n')
        finally:
            f.close()

    # Manual unban command for moderators
    @commands.command()
    @commands.has_any_role('gods', 'interns')
    async def unban(self, ctx, memberId=None):
        banned_users = await ctx.guild.bans()
        member = None
        for banned in banned_users:
            if banned.user.id == int(memberId):
                member = banned.user

        if member is None:
            ctx.channel.send('{0.message.author.mention}: User is not banned.'.format(ctx))
            return

        channel_good = await self.sentInPrivateChannel(ctx, member)
        if not channel_good:
            return

        await ctx.guild.unban(user=member, reason='Prompted to by {0.message.author}'.format(ctx))
        await ctx.channel.send('{0.message.author.mention}: User has been unbanned. Please reach out to them manually'
                               ' to notify them.'.format(ctx))
        logging.info('{0.message.author} unbanned {1.name}#{1.discriminator}, id: {1.id}.'
                     .format(ctx, member))

    # Handler for the bot automatically unbanning members
    async def bot_unban(self, memberId=None):
        channel = self.bot.get_channel(self.cyberInternLogChannelId)
        guild = channel.guild
        banned_users = await guild.bans()
        member = None
        for banned in banned_users:
            if banned.user.id == int(memberId):
                member = banned.user

        await channel.send("Unbanned {0.name}#{0.discriminator} automatically.".format(member))
        await guild.unban(user=member, reason='Ban expired.')
        logging.info('Cyber-Intern unbanned {0.name}#{0.discriminator}, id: {0.id} because ban expired.'.format(member))
        return True


def setup(bot):
    bot.add_cog(AdminCommands(bot))
