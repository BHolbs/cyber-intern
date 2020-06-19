import discord
from discord.ext import commands
from datetime import datetime, timedelta

# use for emplacing bans in a sorted fashion, and for customizing sorts
#   - bisect for
#   - operator for list.sort(key=operator.attrgetter('expiry'))
import bisect
import operator


class Ban:
    def __init__(self, user, expiration, reason):
        self.member = user
        self.expiry = expiration
        self.reason = reason

    def __lt__(self, other):
        return self.expiry < other.expiry

    def hasExpired(self, now):
        if now > self.expiry:
            return True

        return False


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


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # only timed bans go in this list, permanent bans have to be manually unbanned
        self.bans = list()

        # TODO: change this ID when releasing to the official server
        self.internChannelId = 723323448075485237

    async def sentInPrivateChannel(self, ctx, member: discord.User = None):
        if ctx.channel.name != 'interns-assemble':
            await ctx.message.delete()
            channel = self.bot.get_channel(self.internChannelId)
            await channel.send('{0.message.author.mention}: You can only use administrator commands here.'.format(ctx))
            return False
        if member == ctx.message.author:
            await ctx.message.delete()
            await ctx.channel.send("{0.message.author.mention}: You can't ban yourself, dummy.".format(ctx))
            return False
        if member is None:
            await ctx.message.delete()
            await ctx.channel.send(
                '{0.message.author.mention}: You have to mention the user to ban with @.'.format(ctx))

        return True

    @commands.command()
    @commands.has_any_role('gods', 'interns')
    async def ban(self, ctx, member: discord.Member = None, duration=None, *, reason=None):
        member_roles = list()
        for i in member.roles:
            member_roles.append(i.name)
        trying_to_ban_mod = any(item in ['interns', 'gods'] for item in member_roles)
        if trying_to_ban_mod:
            await ctx.message.delete()
            await ctx.guild.owner.send("Hello!\n\n"
                                       "{0.message.author}"
                                       " in The OPMeatery attempted to ban"
                                       " {1}."
                                       " I am not programmed to allow moderators to ban each other, or gods, but I"
                                       " am programmed to notify you if someone tries.".format(ctx, member))
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

            try:
                f = open("bans", mode='a')
                f.write(str(ban.member.id))
                f.write(',')
                f.write(ban.expiry.strftime('%m %d %Y %H:%M'))
                f.write(',')
                f.write(ban.reason)
            finally:
                f.close()

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

        # await ctx.guild.ban(user=member, delete_message_days=1, reason=ban.reason)
        await ctx.message.delete()


def setup(bot):
    bot.add_cog(AdminCommands(bot))
