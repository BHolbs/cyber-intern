# CYBER INTERN

Hello! This is a Discord Bot using [Discord.py](https://github.com/Rapptz/discord.py) and MongoDB for [Operation Meatier's](https://www.youtube.com/channel/UCaOPFwje0plSZpef1RyzNWg) official discord server.

This bot was built specifically for the server, and will not be available to join other servers. However, I have built this bot in such a way that you can fork or clone this repository and build your own!

# Using The Repo

This bot is licensed under the MIT License. For more details, check out the [LICENSE](https://github.com/BHolbs/cyber-intern/blob/develop/LICENSE) file in this repository.

## Setting Up

As of right now, there are still a handful of hard-coded values in the bot (but don't worry, there are issues open to fix that!), so if you want to fork this repository, consider that there might be a lot of work involved to replace those. If you're willing to deal with that, read on!

This bot expects a bot token in a file called `key`. You can retrieve that key by creating an Application in the Discord Developer Portal, then attaching a Bot User to that app. The key is the token on the bot page.

This bot expects a MongoDB connection string in a file called `connection_string`. There are a number of ways to produce a MongoDB connection string, so I'm going to refer you to their official doccumentation [here](https://docs.mongodb.com/guides/server/install/).

If no `key` or `connection_string` file exists, the bot will fail to start up properly.
