import asyncio
import io
import os
import time
import struct
import subprocess
import math
import json

import urllib.request

from pathlib import Path

import youtube_dl #youtube api

import discord #discord api
from discord.ext import commands

class ChrisPlayer:
	"""
	Chris commands for a bot.
	https://github.com/chrisootes/chrisbot
	"""
	def __init__(self, bot):
		self.bot = bot
		self.voice = voice

		self.list_skippers = []
		self.list_songs = []
		self.list_names = []

        self.song_playing = False
        
	async def background_song(self):
		song_old = False
		time_delay = 0.02
		time_loops = 0
		time_start = 0
		header = 0

		while not self.bot.is_closed:
			#print(self.time_loops)
			if self.song_playing == False:
				if len(self.list_songs) == 0:
					if song_old == False:
						song_old = True
						song_status = discord.Status.dnd
						song_game = discord.Game(name='Nothing')
						self.bot.change_presence(game=song_game, status=song_status)
					await asyncio.sleep(1)
				else:
					print('Next Song')
					self.song_playing = True
					song_old = True

					song_file = self.list_songs.pop(0)
					print(song_file)

					song_name = self.list_names.pop(0)
					print(song_name)

					song_status = discord.Status.online
					song_game = discord.Game(name=song_name)
					self.bot.change_presence(game=song_game, status=song_status)

					f = open(song_file, 'rb')
					stream = io.BytesIO(f.read())
					f.close
					print('Playing ' + str(song_name) + ' with ' + str(song_file))

					time_start = time.time()
					time_loops = 0
					header = 0

			else:
				header1 = stream.read(5)
				#print(header1)

				if header1 != b'OggS\x00':
					print('Wrong header1' + str(header1))
					time_loops = 0
					song_playing = False
					continue

				header += 1
				header2 = stream.read(1)
				if header2 == b'\x00':
					#print('Next page')
					stream.read(20) #skip crc etc

				elif header2 == b'\x02':
					print('Song tag')
					stream.read(20)#skip crc etc

				elif header2 == b'\x04':
					print('Song end')
					stream.read(20) #skip crc etc
					song_playing = False

				else:
					print('Wrong header2: ' + str(header2))
					song_playing = False
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
						time_loops += 1
						packet_size += lacing
						packet = stream.read(packet_size)

						if header > 2:
							voice.play_audio(packet, encode=False)

						else:
							print('Header ' + str(header))

						packet_size = 0
						time_next = time_start + time_delay * time_loops
						delay = max(0, time_delay + (time_next - time.time()))
						#print(delay)
						await asyncio.sleep(delay)

	@commands.command(pass_context=True, no_pm=True)
	async def summon(self, ctx):
		"""Summons youtube player."""
		print(ctx.message)
		#await self.bot.delete_message(ctx.message) #cant delete twice after invoke
		summoned_channel = ctx.message.author.voice_channel
		if summoned_channel is None:
			await self.bot.say('You are not in a voice channel.')
			return False

		if self.song_playing == False:
			self.voice = await self.bot.join_voice_channel(summoned_channel)
			print('Creating background task')
			self.bot.loop.create_task(ChrisCommands.background_song(self)) #create task to check the current song and change status

		else:
			print('moving to: ' + str(summoned_channel))
			await self.voice.move_to(summoned_channel)

		return True

	@commands.command(pass_context=True)
	async def add(self, ctx, song : str):
		"""Plays youtube song."""
		await self.bot.delete_message(ctx.message)
		if self.song_playing == False:
			success = await ctx.invoke(self.summon)
			print(success)
			if not success:
				await self.bot.say('Failed to summon bot.')
				return

		ydl_opts = {
		'playlist_items': '1',
		'format': '251/250/249'}

		try:
			song_info = youtube_dl.YoutubeDL(ydl_opts).extract_info(song, download=False) #create async threads to paralise
		except Exception as e:
			print(e)
			await self.bot.say('Youtube failed')
			return

		if song_info.get('_type', None) == 'playlist':
			song_url = song_info.get('entries[0].url', None)
			song_title = song_info.get('entries[0].title', None)
			song_id = song_info.get('entries[0].id', None)
			song_duration = song_info.get('entries[0].duration', None)

		else:
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
					urllib.request.urlretrieve(song_url, file_youtube) #create async threads to paralise
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
			print('Returncode: ' + str(succes.returncode))
			if succes.returncode != 0:
				await self.bot.say('Youtube mkv container extraction failed')
				return

		self.list_songs.append(path_opus)
		self.list_names.append(song_title)
		await self.bot.say('Added song: ' + str(song_title) + ' by ' + str(ctx.message.author))

	@commands.command(pass_context=True)
	async def stop(self, ctx):
		"""Stop youtbube player."""
		await self.bot.delete_message(ctx.message)
		if self.player is None:
			print(ctx.message.author.id)
			await self.bot.say('Nothin to stop')

		elif ctx.message.author.id == '100280813244936192':
			print('Stopping')
			#stop self.bot.loop.create_task(ChrisCommands.background_song(self))
            self.voice.disconnect()

		else:
			await self.bot.say('Mute and/or vote to skip')

	@commands.command(pass_context=True)
	async def skip(self, ctx):
		"""Vote to skip song."""
		await self.bot.delete_message(ctx.message)
		if self.song_playing == False:
			await self.bot.say('Nothing is playing')

		else:
            skipper = ctx.message.author.id
			for already in self.list_skippers: #check if de voter hasnt voted already
				if already == skipper: #
					await self.bot.say('Cant skip twice')
					return

			self.list_skippers.append(skipper)  #add the id of de voter to the list

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
			skipper_needed = math.floor(0.5*skipper_max)
			print('People needed ' + str(skipper_needed))
			skipper_amount = len(self.list_skippers)
			print('People voted ' + str(skipper_amount))
			if skipper_amount >= skipper_needed:
				self.list_skippers = []
				self.player.skip()
				await self.bot.say('Skipped')
			else:
				await self.bot.say(str(skipper_amount) + ' skippers out of ' + str(skipper_needed))
