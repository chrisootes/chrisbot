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

		self.list_songs = []
		self.list_names = []
		self.list_skippers = []

		self.song_name =  'Nothing'

		self.time_delay = 0.02
		self.time_loops = 0
		self.time_start = 0

		self.header = 0

	def run(self):
		while not self.event_end.is_set():
			#print(self.time_loops)
			if not self.event_next.is_set():
				self.song_name = 'Nothing'

				if len(self.list_song) == 0:
					print('Waiting')
					self.event_next.wait()
				else:
					print('Next Song')
					self.event_next.set()

				song_file = self.list_songs.pop()
				print(song_file)

				self.song_name = self.list_names.pop()
				print(self.song_name)

				f = open(song_file, 'rb')
				stream = io.BytesIO(f.read())
				f.close
				print('Playing ' + str(self.song_name) + ' with ' + str(song_file))

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

		print('Stopping')
		self.voice.disconnect() #no working

	def stop(self):
		print('Stopping')
		self.event_end.set()
		self.event_next.clear()

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
			self.list_skippers = []
			return 'Skipped'

		return str(skipper_amount) + ' skippers out of ' + str(skipper_needed)

	def add(self, song, requester):
		self.list_song.append(song)
		self.list_requester.append(requester)
		self.event_next.set()

	def current(self):
		return self.song_name

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
		self.reddit_object = {}

	async def background_song(self):
		await self.bot.wait_until_ready()
		while not self.bot.is_closed:
			song_game = discord.Game(name=self.player.current)
			song_status = random.choice((discord.Status.online, discord.Status.idle, discord.Status.dnd))
			await self.bot.change_presence(game=echogame, status=song_status)
			await asyncio.sleep(10) # task runs every 10 seconds

	@commands.command(pass_context=True)
	async def echo(self, ctx, msg : str):
		"""Repeats message."""
		await self.bot.delete_message(ctx.message)
		echogame = discord.Game(name=msg)
		await self.bot.change_status(game=echogame)

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

	@commands.command(pass_context=True, no_pm=True)
	async def summon(self, ctx):
		"""Summons youtube player."""
		#await self.bot.delete_message(ctx.message)
		summoned_channel = ctx.message.author.voice_channel
		if summoned_channel is None:
			await self.bot.say('You are not in a voice channel.')
			return False

		if self.player is None:
			self.player = ChrisPlayer(await self.bot.join_voice_channel(summoned_channel))
			self.player.setName('MusicPlayer 1')
			self.player.start()

		print('Creating background task')
		self.bot.loop.create_task(background_song())

		return True

	@commands.command(pass_context=True)
	async def add(self, ctx, song : str):
		"""Plays youtube song, give youtube id only."""
		await self.bot.delete_message(ctx.message)
		if self.player is None:
			success = await ctx.invoke(self.summon)
			print(success)
			if not success:
				return

		ydl_opts = {'format': '251/250/249'}

		try:
			song_info = youtube_dl.YoutubeDL(ydl_opts).extract_info(song, download=False)

		except Exception as e:
			print(e)
			await self.bot.say('Youtube failed')
			return

		song_url = song_info.get('url', None)
		song_title = song_info.get('title', None)
		song_id = song_info.get('id', None)
		song_duration = song_info.get('duration', None)

		file_youtube = song_id + '.webm'
		print('Checking ' + file_youtube)
		path_youtube = Path(file_youtube)

		if not path_youtube.is_file():
			if song_duration < 600:
				try:
					urllib.request.urlretrieve(song_url, file_youtube)

				except Exception as e:
					print(e)
					await self.bot.say('Download failed')
					return

			else:
				await self.bot.say('Song ' + str(song_title) + ' by ' + str(ctx.message.author) + ' is too long')
				return

		file_opus = file_youtube + '.opus'
		print('Checking ' + file_opus)
		path_opus = Path(file_opus)

		if not path_opus.is_file():
			command = ['mkvextract', 'tracks', file_youtube, '0:' + file_opus]
			succes = subprocess.run(command)
			print(succes.returncode)

			if succes.returncode != 0:
				await self.bot.say('Youtube mkv container extraction failed')
				return

		self.player.add(path_opus, song_title)

		await self.bot.say('Added song: ' + str(song_title) + ' by ' + str(ctx.message.author))

	@commands.command(pass_context=True)
	async def stop(self, ctx):
		"""Stop youtbube player."""
		await self.bot.delete_message(ctx.message)
		if self.player is None:
			print(ctx.message.author.id)
		elif ctx.message.author.id == '100280813244936192':
			print('Beginning')
			self.player.stop()
			print('Joining')
			self.player.join()
			print('Joined')
		else:
			await self.bot.say('Mute and/or vote to skip')

		await self.bot.say('Stopped')

	@commands.command(pass_context=True)
	async def skip(self, ctx):
		"""Vote to skip song."""
		await self.bot.delete_message(ctx.message)
		if self.player is not None:
			succes = self.player.skip(ctx.message.author.id)
			await self.bot.say(succes)

bot = commands.Bot(command_prefix='$', description='Kinky bot')
bot.add_cog(ChrisCommands(bot))

@bot.event
async def on_ready():
	print('Logged in as: ' + str(bot.user))
	print('User ID: ' + str(bot.user.id))

tokenfile = open('token.txt', 'rt')
token = tokenfile.readline().splitlines()
tokenfile.close
print('Token: ' + token[0])
bot.run(token[0])
