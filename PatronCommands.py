import os
import logging
from datetime import datetime, timedelta
from discord.ext import commands


def make_diff_string(delta):
    out = str()
    if delta.days != 0:
        out += "{0.days} day(s)".format(delta)
        return out
    elif delta.total_seconds() >= 3600:
        out += "{0} hour(s)".format(round(delta.total_seconds() / (60 * 60), 2))
        return out
    elif delta.total_seconds() >= 60:
        out += "{0} minute(s)".format(round(delta.total_seconds() / 60, 2))
        return out
    else:
        out += "{0} seconds".format(round(delta.total_seconds(), 2))
        return out


class PatronCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # if the file containing the last time jojo got called out exists
        if os.path.isfile('time'):
            try:
                with open('time', mode='r') as f:
                    time = f.readlines()
                    if len(time) == 0:
                        self.when_blue_last_mentioned = None
                    else:
                        self.when_blue_last_mentioned = datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f")
            except IOError:
                # something would have to be VERY wrong for this to happen, print to the console and then quit
                # since this can only happen on startup, quit out if this happens
                print("'time' file exists, but unable to open it. Quitting.")
                quit()
            finally:
                f.close()
        # if the file doesn't exist
        else:
            try:
                with open('time', mode='w') as f:
                    f.write('')
                    self.when_blue_last_mentioned = None
            except IOError:
                # something would have to be VERY wrong for this to happen, print to the console and then quit
                # since this can only happen on startup, quit out if this happens
                print("'time' file was unable to be created. Quitting.")
                quit()
            finally:
                f.close()

        self.last_time_patron_called_out_blue = timedelta()

    @commands.command(name="jojo")
    @commands.has_any_role("Cool Capers", "gods", "interns")
    async def last_time(self, ctx):
        if self.when_blue_last_mentioned is None:
            await ctx.channel.send("Blue has not ever mentioned JoJo, somehow.")
            return
        else:
            time = self.when_blue_last_mentioned
            how_long = datetime.utcnow() - time
            diff_string = make_diff_string(how_long)
            await ctx.message.delete()
            await ctx.channel.send("It has been {0} since Blue last talked about JoJo's Bizarre Adventure."
                                   .format(diff_string))

    @commands.command(name="callout")
    @commands.has_any_role("Cool Capers", "gods", "interns")
    async def call_out(self, ctx):
        last_time_called_out = self.last_time_patron_called_out_blue
        # don't really need precision down to the absolute second, don't let people use this command more than
        # once a minute, since it pings blue
        if self.when_blue_last_mentioned is not None and last_time_called_out.total_seconds() < 60:
            return
        else:
            now = datetime.utcnow()
            # write 'now' to the time file
            try:
                with open('time', mode='w') as f:
                    f.write(str(now))
                    self.when_blue_last_mentioned = now
            except IOError:
                # this should almost NEVER happen, but if it does, i definitely want to know about it
                logging.error("'time' file was unable to be rewritten when a patron used !callout.")
                await ctx.guild.owner.send("Something went wrong when a patron used !callout. Please let my dev know.")
            finally:
                f.close()

            # really don't like having to do this search here, but doing it in init would be a huge pain
            blue = ctx.guild.get_member(159145385367961600)
            await ctx.message.delete()
            await ctx.channel.send("{0.mention}, either make JoJo Abridged, or talk about something else.".format(blue))


def setup(bot):
    bot.add_cog(PatronCommands(bot))
