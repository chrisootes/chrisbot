import asyncio
import random
import re
import math
import json

#rss api
import feedparser

#discord api
import discord
from discord.ext import commands

#reddit rss class
class ChrisReddit:
	def __init__(self, subredit):
		self.reddit_sub = subredit
		self.reddit_time = time.time()
		self.reddit_feed = feedparser.parse('https://www.reddit.com/r/{}/top/.rss?sort=top&t=week'.format(self.reddit_sub))

		print(self.reddit_feed.status)
		if self.reddit_feed.status != 200:
			raise Exception()

	def reddit(self):
		reddit_current = time.time()
		reddit_old = self.reddit_time + 36000

		if reddit_old < reddit_current:
			self.reddit_feed = feedparser.parse('https://www.reddit.com/r/{}/top/.rss?sort=top&t=week'.format(self.reddit_sub))
			self.reddit_time  = reddit_current

		reddit_rng = math.floor(random.random()*len(self.reddit_feed.entries))
		print(reddit_rng)
		reddit_html = self.reddit_feed.entries[reddit_rng].content[0].value
		reddit_regex = re.search('<a\s+(?:[^>]*?\s+)?href="([^"]*)">\[link\]<\/a>', reddit_html)
		reddit_link = reddit_regex.group(1).replace('amp;', '')

		return(reddit_link)

class ChrisCommands:
	"""
	Chris commands for a bot.
	https://github.com/chrisootes/chrisbot
	"""
	def __init__(self, bot):
		self.bot = bot
		self.reddit_object = {}

	@commands.command(pass_context=True)
	async def echo(self, ctx, msg : str):
		"""Repeats message."""
		await self.bot.delete_message(ctx.message)
		await asyncio.sleep(10)
		await self.bot.say('Reply: ' + msg)

	@commands.command(pass_context=True)
	async def reet(self, ctx, reeten : int):
		"""Rates with buts."""
		await self.bot.delete_message(ctx.message)
		await self.bot.say(str('<:reet:240860984086888449> ') * reeten + ' from ' + str(ctx.message.author))

	@commands.command(pass_context=True)
	async def reddit(self, ctx, subreddit : str):
		"""Reddit rss."""
		await self.bot.delete_message(ctx.message)
		#whitelist?
		subreddit_object = self.reddit_object.get(subreddit, None)
		if subreddit_object is None:
			try:
				subreddit_object = ChrisReddit(subreddit)
			except:
				await self.bot.say('Invalid subreddit')
				return

			self.reddit_object[subreddit] = subreddit_object

		print('Subredit: ' + str(subreddit))
		reddit_link = subreddit_object.reddit()
		print(reddit_link)
		await self.bot.say(reddit_link)
