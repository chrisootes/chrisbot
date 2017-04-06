import asyncio
import io
import os
import time
import struct
import threading
import subprocess
import random
import re
import math

import urllib.request

from pathlib import Path

#rss api
import feedparser

#youtube api
import youtube_dl

#discord api
import discord
from discord.ext import commands

class ChrisPlayer(threading.Thread):
	def __init__(self, voice):
		threading.Thread.__init__(self)
		self.daemon = True

		self.voice = voice

		self.event_end = threading.Event()
		self.event_next = threading.Event()

		self.list_song = []
		self.list_requester = []
		self.list_skippers = []

		self.time_delay = 0.02
		self.time_loops = 0
		self.time_start = 0

		self.header = 0

	def run(self):
		while not self.event_end.is_set():
			#print(self.time_loops)
			if not self.event_next.is_set():
				if len(self.list_song) == 0:
					print('Waiting')
					self.event_next.wait()
				else:
					print('Next Song')
					self.event_next.set()

				song_file = self.list_song.pop()
				print(song_file)

				song_requester = self.list_requester.pop()
				print(song_requester)

				f = open(song_file, 'rb')
				stream = io.BytesIO(f.read())
				f.close
				print('Playing ' + str(song_file) + str(song_requester))

				self.time_start = time.time()
				self.time_loops = 0
				self.header = 0

			header1 = stream.read(5)
			#print(header1)

			if header1 != b'OggS\x00':
				#no new song or error
				print('Wrong header1' + str(header1))
				self.time_loops = 0
				self.event_next.clear()
				continue

			self.header += 1
			header2 = stream.read(1)
			if header2 == b'\x00':
				#print('Next page')
				stream.read(20) #skip crc etc

			elif header2 == b'\x02':
				#new song
				print('Song tag')
				self.time_loops = 0
				stream.read(20)#skip crc etc

			elif header2 == b'\x04':
				#end song
				print('Song end')
				stream.read(20) #skip crc etc
				self.event_next.clear()

			else:
				print('Wrong header2: ' + str(header2))
				self.event_next.clear()
				continue

			page_segments_byte = stream.read(1)
			page_segments = struct.unpack('B', page_segments_byte)[0]

			lacing_values_bytes = stream.read(page_segments)
			lacing_values = struct.unpack('B'*page_segments, lacing_values_bytes)

			packet_size = 0

			for lacing in lacing_values:
				if lacing == 255:
					packet_size += 255

				else:
					self.time_loops += 1
					packet_size += lacing
					packet = stream.read(packet_size)
					if self.header > 2:
						self.voice.play_audio(packet, encode=False)

					else:
						print('Header ' + str(self.header))

					packet_size = 0
					time_next = self.time_start + self.time_delay * self.time_loops
					delay = max(0, self.time_delay + (time_next - time.time()))
					#print(delay)
					time.sleep(delay)

	def stop(self):
		self.event_end.set()
		self.event_next.clear()
		self.voice.disconnect()

	def skip(self, skipper):
		for already in self.list_skippers:
			if already == skipper:
				return 'Cant skip twice'

		self.list_skippers.append(skipper)

		skipper_channel = self.voice.channel
		print(skipper_channel)

		skipper_members = self.voice.server.members
		skipper_max = 0

		for member in skipper_members:
			skipper_legit = member.voice.voice_channel
			#print(skipper_legit)
			if skipper_legit == skipper_channel:
				skipper_max += 1

		print('People in voice ' + str(skipper_max))

		skipper_needed = math.floor(0.50*skipper_max)
		print('People needed ' + str(skipper_needed))

		skipper_amount = len(self.list_skippers)
		print('People voted ' + str(skipper_amount))

		if skipper_amount >= skipper_needed:
			self.event_next.clear()
			return 'Skipped'

		return str(skipper_amount) + ' skippers out of ' + str(skipper_needed)

	def add(self, song, requester):
		self.list_song.append(song)
		self.list_requester.append(requester)
		self.event_next.set()

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
		reddit_old = self.reddit_time+36000

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
		self.player = None
		self.reddit = {}

	@commands.command(pass_context=True)
	async def echo(self, ctx, msg : str):
		"""Repeats message."""
		await self.bot.say(msg)

	@commands.command(pass_context=True)
	async def reet(self, ctx, reeten : int):
		"""Rates with buts."""
		await self.bot.say(str('<:reet:240860984086888449> ') * reeten)

	@commands.command(pass_context=True)
	async def meme(self, ctx, subreddit : str):
		"""Reddit rss."""
		#whitelist?
		reddit_obj = self.reddit.get(subreddit, None)

		if reddit_obj is None:
			try:
				reddit_obj = ChrisReddit(subreddit)
			except:
				await self.bot.say('Invalid subreddit')
				return
			self.reddit[subreddit] = reddit_obj

		print('Subredit: {}'.format(subreddit))
		reddit_link = reddit_obj.reddit()
		print(reddit_link)
		await self.bot.say(reddit_link)

	@commands.command(pass_context=True, no_pm=True)
	async def summon(self, ctx):
		"""Summons youtube player."""
		summoned_channel = ctx.message.author.voice_channel
		if summoned_channel is None:
			await self.bot.say('You are not in a voice channel.')
			return

		if self.player is None:
			self.player = ChrisPlayer(await self.bot.join_voice_channel(summoned_channel))
			self.player.setName('MusicPlayer 1')
			self.player.start()

	@commands.command(pass_context=True)
	async def add(self, ctx, song : str):
		"""Plays youtube song, give youtube id only."""
		if self.player is None:
			await ctx.invoke(self.summon)
			#success =
			#if not success:
				#return

		if len(song) > 20:
			await self.bot.say('Wrong song link')
			return

		file_youtube = song + '.webm'
		print('Checking ' + file_youtube)
		path_youtube = Path(file_youtube)

		if not path_youtube.is_file():
			ydl_opts = {'format': '251/250/249', 'output': file_youtube}

			try:
				song_info = youtube_dl.YoutubeDL(ydl_opts).extract_info(song, download=False)

			except Exception as e:
				print(e)
				await self.bot.say('Youtube part fucked up mate')
				return

			song_url = song_info.get('url', None)
			song_title = song_info.get('title', None)
			song_id = song_info.get('id', None)
			song_duration = song_info.get('duration', None)

			if song_duration < 600:
				try:
					urllib.request.urlretrieve(song_url, file_youtube)

				except Exception as e:
					print(e)
					await self.bot.say('Youtube part fucked up mate')
					return

			else:
				await self.bot.say('Song {}, by: {} is too long'.format(song_title, str(ctx.message.author)))
				return

		else:
			song_title = 'Dunno'

		file_opus = file_youtube + '.opus'
		print('Checking ' + file_opus)
		path_opus = Path(file_opus)

		if not path_opus.is_file():
			command = ['mkvextract', 'tracks', file_youtube, '0:' + file_opus]
			succes = subprocess.run(command)
			print(succes)

		self.player.add(path_opus, ctx.message.author)

		await self.bot.say('Added song {}, by: {}'.format(song_title, str(ctx.message.author)))

	@commands.command(pass_context=True)
	async def stop(self, ctx):
		"""Stop youtbube player."""
		if self.player is None:
			print(ctx.message.author.id)
		elif ctx.message.author.id == '100280813244936192':
			self.player.stop()
			#self.player.join()
		else:
			await self.bot.say('Mute and/or vote to skip')

	@commands.command(pass_context=True)
	async def skip(self, ctx):
		"""Vote to skip song."""
		if self.player is not None:
			succes = self.player.skip(ctx.message.author.id)
			await self.bot.say(succes)

bot = commands.Bot(command_prefix='$', description='Kinky bot')
bot.add_cog(ChrisCommands(bot))

@bot.event
async def on_ready():
	print('Logged in as: {0} \nUser ID: {0.id}'.format(bot.user))

bot.run('MTkxMzMxODY1MjUxMTUxODcy.Cv5KNw.FF8ar2Ik21ou_GFyeyTXO7OeBx4')
