
# coding: utf-8

# In[1]:


import discord
from discord.ext import commands
import random
import asyncio
from pymongo import MongoClient


# In[47]:


import datetime
def get_time_now() :
    date = datetime.datetime.now()
    date = date.isoformat().split('T')
    date , time = date[0], date[1].split('.')[0]
    return date, time


# In[2]:


CLIENT_ID = "375302183245185034"
CLIENT_SECRET ="q6VV9pfmaApEH43Fn1LI6X1s7i7Vmo7w"
CLIENT_TOKEN = "Mzc1MzAyMTgzMjQ1MTg1MDM0.DOGcMQ.kk-Z4tH85kJ5bnFYV6wjcIsEOio"


# In[3]:


db_client = MongoClient()
db = db_client.test # db named test


# In[4]:


from pymongo.errors import ConnectionFailure
try:
   # The ismaster command is cheap and does not require auth.
    db_client.admin.command('ismaster')
    print("Connected to database")
except ConnectionFailure:
    print("Server not available")


# In[5]:


db.collection_names()


# In[6]:


prefix= "??"
bot = commands.Bot(command_prefix=prefix)


# In[7]:


def get_channel_id(channel_name) :
    for channel in bot.get_all_channels() :
        if channel.name == channel_name :
            return channel.id


# In[8]:


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


# In[54]:


@bot.event
async def on_voice_state_update(before,after) :
    if (before.voice.voice_channel is None and     after.voice.voice_channel is not None )or     (before.voice.voice_channel != after.voice.voice_channel):
        cont = (before.name + ' connected to '+after.voice.voice_channel.name+ '.')
    if before.voice.voice_channel is not None and    after.voice.voice_channel is None :
        cont = (after.name +' disconnected from '+ before.voice.voice_channel.name+'.')
    date, time = get_time_now()
    cont = '`'+date + '\t'+time+'\t'+cont+'`'
    await bot.send_message(destination=bot.get_channel(get_channel_id('lug')), content=cont)
    


# In[10]:


@bot.command()
async def add(left : int, right : int):
    """Adds two numbers together."""
    await bot.say(left + right)


# In[11]:


@bot.command()
async def roll(dice : str):
    """Rolls a dice in NdN format."""
    try:
        rolls, limit = map(int, dice.split('d'))
    except Exception:
        await bot.say('Format has to be in NdN!')
        return

    result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
    await bot.say(result)


# In[12]:


@bot.command(description='For when you wanna settle the score some other way')
async def choose(*choices : str):
    """Chooses between multiple choices."""
    await bot.say(random.choice(choices))


# In[13]:


@bot.command()
async def repeat(times : int, content='repeating...'):
    """Repeats a message multiple times."""
    for i in range(times):
        await bot.say(content)


# In[14]:


@bot.command()
async def joined(member : discord.Member):
    """Says when a member joined."""
    await bot.say('{0.name} joined in {0.joined_at}'.format(member))


# In[15]:


@bot.group(pass_context=True)
async def cool(ctx):
    """Says if a user is cool.
    In reality this just checks if a subcommand is being invoked.
    """
    if ctx.invoked_subcommand is None:
        await bot.say('No, {0.subcommand_passed} is not cool'.format(ctx))


# In[16]:


@cool.command(name='bot')
async def _bot():
    """Is the bot cool?"""
    await bot.say('Yes, the bot is cool.')


# In[17]:


@bot.command(pass_context=True, no_pm=True)
async def members(ctx):
    """show a list of all members"""
    server = ctx.message.server
    members = server.members
    out = ''
    for m in members :
        print(m.name)
        out += (m.name + "\n")
    await bot.say(out)


# In[18]:


x =  db.playlist.find({'_id': '123'})
x.count()


# In[19]:


test_playlist = {'_id' : 'wad' ,  
                 'queue':['when you say nothing at all']}


# In[20]:


for x in db.playlist.find():
    print(x['_id'])


# music

# In[21]:


if not discord.opus.is_loaded():
    print('no opus')


# In[22]:


class VoiceEntry:
    def __init__(self, message, player):
        self.requester = message.author
        self.channel = message.channel
        self.player = player

    def __str__(self):
        fmt = '*{0.title}* uploaded by {0.uploader} and requested by {1.display_name}'
        duration = self.player.duration
        if duration:
            fmt = fmt + ' [length: {0[0]}m {0[1]}s]'.format(divmod(duration, 60))
        return fmt.format(self.player, self.requester)
    


# In[23]:


class VoiceState:
    def __init__(self, bot):
        self.current = None
        self.voice = None
        self.bot = bot
        self.play_next_song = asyncio.Event()
        self.songs = asyncio.Queue()
        self.skip_votes = set() # a set of user_ids that voted
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())

    def is_playing(self):
        if self.voice is None or self.current is None:
            return False

        player = self.current.player
        return not player.is_done()

    @property
    def player(self):
        return self.current.player

    def skip(self):
        self.skip_votes.clear()
        if self.is_playing():
            self.player.stop()

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        while True:
            self.play_next_song.clear()
            self.current = await self.songs.get()
            await self.bot.send_message(self.current.channel, 'Now playing ' + str(self.current))
            self.current.player.start()
            await self.play_next_song.wait()
            


# In[24]:


class Music:
    """Voice related commands.
    Works in multiple servers at once.
    """
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)
        if state is None:
            state = VoiceState(self.bot)
            self.voice_states[server.id] = state

        return state

    async def create_voice_client(self, channel):
        voice = await self.bot.join_voice_channel(channel)
        state = self.get_voice_state(channel.server)
        state.voice = voice

    def __unload(self):
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                if state.voice:
                    self.bot.loop.create_task(state.voice.disconnect())
            except:
                pass

    @commands.command(pass_context=True, no_pm=True)
    async def join(self, ctx, channel : discord.Channel = None):
        """Joins a voice channel."""
        if channel is None :
            channel = ctx.message.author.voice.voice_channel
        try:
            await self.create_voice_client(channel)
        except discord.ClientException:
            await self.bot.say('Already in a voice channel...')
        except discord.InvalidArgument:
            await self.bot.say('This is not a voice channel...')
        else:
            await self.bot.say('Ready to play audio in ' + channel.name)

    @commands.command(pass_context=True, no_pm=True)
    async def summon(self, ctx):
        """Summons the bot to join your voice channel."""
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.bot.say('You are not in a voice channel.')
            return False

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            state.voice = await self.bot.join_voice_channel(summoned_channel)
        else:
            await state.voice.move_to(summoned_channel)

        return True

    @commands.command(pass_context=True, no_pm=True)
    async def play(self, ctx, *, song : str):
        print('play command')
        """Plays a song.
        If there is a song currently in the queue, then it is
        queued until the next song is done playing.
        This command automatically searches as well from YouTube.
        The list of supported sites can be found here:
        https://rg3.github.io/youtube-dl/supportedsites.html
        """
        state = self.get_voice_state(ctx.message.server)
        print('state = ', state)
        opts = {
            'default_search': 'auto',
            'quiet': True,
        }

        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        try:
            player = await state.voice.create_ytdl_player(song,
                                                          ytdl_options=opts, 
                                                          after=state.toggle_next)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, 
                                        fmt.format(type(e).__name__, e))
        else:
            player.volume = 0.05
            entry = VoiceEntry(ctx.message, player)
            await self.bot.say('Enqueued ' + str(entry))
            await state.songs.put(entry)

    @commands.command(pass_context=True, no_pm=True)
    async def volume(self, ctx, *args):
        """Sets the volume of the currently playing song (%)."""

        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            
            if len(args) == 0 :
                await self.bot.say('Current volume : '+str(100*player.volume)+'%')
            else :
                try : 
                    value = int(args[0])
                    player.volume = value / 100
                    await self.bot.say('Set the volume to {:.0%}'.format(player.volume))
                except ValueError:              
                    await self.bot.say('invalid volume value')
                    return
                
    @commands.command(pass_context=True, no_pm=True)
    async def pause(self, ctx):
        """Pauses the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.pause()

    @commands.command(pass_context=True, no_pm=True)
    async def resume(self, ctx):
        """Resumes the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.resume()

    @commands.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        """Stops playing audio and leaves the voice channel.
        This also clears the queue.
        """
        server = ctx.message.server
        state = self.get_voice_state(server)

        if state.is_playing():
            player = state.player
            player.stop()

        try:
            state.audio_player.cancel()
            del self.voice_states[server.id]
            await state.voice.disconnect()
        except:
            pass

    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        """Vote to skip a song. The song requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        voter = ctx.message.author
        if voter == state.current.requester:
            await self.bot.say('Requester requested skipping song...')
            state.skip()
        elif voter.id not in state.skip_votes:
            state.skip_votes.add(voter.id)
            total_votes = len(state.skip_votes)
            if total_votes >= 3:
                await self.bot.say('Skip vote passed, skipping song...')
                state.skip()
            else:
                await self.bot.say('Skip vote added, currently at [{}/3]'.format(total_votes))
        else:
            await self.bot.say('You have already voted to skip this song.')

    @commands.command(pass_context=True, no_pm=True)
    async def playing(self, ctx):
        """Shows info about the currently played song."""

        state = self.get_voice_state(ctx.message.server)
        if state.current is None:
            await self.bot.say('Not playing anything.')
        else:
            skip_count = len(state.skip_votes)
            await self.bot.say('Now playing {} [skips: {}/3]'.format(state.current, skip_count))
            

    @commands.command(pass_context=True, no_pm=True)
    async def playlist(self , ctx, action:str, *args):
        """manage your playlist
             use 'playlist show' to show your playlist
             use 'playlist play' to play all songs on your playlist (add to queue)
             use 'playlist clear' to clear all songs on your playlist
             use 'playlist remove [song numbers]'
             use 'playlist add <song>' to add song to playlist
        """
        author = ctx.message.author.name
        result =  db.playlist.find_one({'_id': author})
        if result is None :
            # insert into collection
            test_playlist = {'_id' : author, 'queue':[]}
            db.playlist.insert_one(test_playlist)
        if action == 'show' :
            # never have a playlist before
            if len(result['queue'])== 0:
                await bot.say("Your playlist is empty.")
            else : # already have playlist
                # fetch playlist                
                pl = result['queue']
                out = 'This is ' + author + "'s playlist : \n"
                for song in pl :
                    out += str(song['_id']) + "\t" + song['name'] + '\n'
                await bot.say(out)
        
        elif action   == 'add' :
            song_name =  ''
            for tok in args:
                song_name += tok + " "
            print(song_name)
            song = {'_id': 1+len(result['queue']) ,'name':song_name}
            db.playlist.update_one({'_id':author},
                                    {'$push':{'queue':song}})   
            await bot.say(song['name']+' added to playlist.')
            if state.voice is None:
                    print('state.voice is None')
                    success = await ctx.invoke(self.summon)
                    if not success:
                        return

            try:

                player = await state.voice.create_ytdl_player(song_name,
                                                              ytdl_options=opts, 
                                                             after=state.toggle_next)
            except Exception as e:
                fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
                await self.bot.send_message(ctx.message.channel, 
                                            fmt.format(type(e).__name__, e))
            else:
                player.volume = 0.05
                entry = VoiceEntry(ctx.message, player)
                await self.bot.say('Enqueued ' + str(entry))
                await state.songs.put(entry)
                    
        
        elif action == 'remove' :
            rm_success = "successfully removed song number : "
            for song_num in args :
                try :
                    db.playlist.update_one(
                        { '_id': author }, 
                        { '$pull': { 'queue': { '_id': int(song_num) }}})
                    rm_success += song_num + ' '
                except ValueError:
                    pass
            await bot.say(rm_success+".")    
                
        elif action == 'clear' :
            db.playlist.update_one({'_id':author},
                              {'$set': {'queue': [] } })
            
        
        elif action == 'play' :
            for song in result['queue'] :
                song_name = song['name']
                
                state = self.get_voice_state(ctx.message.server)
                print('state = ', state)
                opts = {
                    'default_search': 'auto',
                    'quiet': True,
                }

                if state.voice is None:
                    print('state.voice is None')
                    success = await ctx.invoke(self.summon)
                    if not success:
                        return

                try:
                    
                    player = await state.voice.create_ytdl_player(song_name,
                                                                  ytdl_options=opts, 
                                                                 after=state.toggle_next)
                except Exception as e:
                    fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
                    await self.bot.send_message(ctx.message.channel, 
                                                fmt.format(type(e).__name__, e))
                else:
                    player.volume = 0.05
                    entry = VoiceEntry(ctx.message, player)
                    await self.bot.say('Enqueued ' + str(entry))
                    await state.songs.put(entry)


# In[25]:


bot.add_cog(Music(bot))


# In[26]:


bot.run(CLIENT_TOKEN)


# In[ ]:


for chan in bot.get_all_channels() :
    print (type(chan))

