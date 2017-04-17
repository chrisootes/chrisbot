import asyncio
import discord
from discord.ext import commands

import ChrisCommands
#import ChrisPlayer

bot = commands.Bot(command_prefix='$', description='Kinky bot')
bot.add_cog(ChrisCommands.ChrisCommands(bot)) #add all commands from this class
#bot.add_cog(ChrisPlayer(bot)) #add all commands from this class

@bot.event
async def on_ready():
	print('Logged in as: ' + str(bot.user))
	print('User ID: ' + str(bot.user.id))

tokenfile = open('token.txt', 'rt')
token = tokenfile.readline().splitlines()
tokenfile.close
print('Token: ' + token[0])
bot.run(token[0])
