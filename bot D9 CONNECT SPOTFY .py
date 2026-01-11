import discord
from discord.ext import commands
import os
import wavelink
import json
import random
import asyncio

intents = discord.Intents.default()
intents.message_content = True
# intents.members = True
# intents.presences = True

bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

# Economy Helper Functions
def load_economy():
    try:
        with open("economy.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_economy(data):
    with open("economy.json", "w") as f:
        json.dump(data, f, indent=4)

def update_balance(user_id, amount):
    data = load_economy()
    user_id_str = str(user_id)
    if user_id_str not in data:
        data[user_id_str] = {"balance": 0}
    data[user_id_str]["balance"] += amount
    save_economy(data)
    return data[user_id_str]["balance"]

@bot.command()
@commands.cooldown(1, 3600, commands.BucketType.user)
async def work(ctx):
    """Work to earn some money."""
    gain = random.randint(50, 200)
    new_bal = update_balance(ctx.author.id, gain)
    await ctx.send(f"💰 You worked and earned **{gain}**! Your new balance is **{new_bal}**.")

@bot.command(name="bal")
async def balance(ctx, member: discord.Member = None):
    """Check your or another member's balance."""
    member = member or ctx.author
    data = load_economy()
    bal = data.get(str(member.id), {}).get("balance", 0)
    await ctx.send(f"💳 **{member.display_name}** has a balance of **{bal}**.")

@bot.command(name="leaderboard")
async def leaderboard(ctx):
    """Show the server's economy leaderboard."""
    data = load_economy()
    if not data:
        return await ctx.send("The leaderboard is currently empty.")

    # Sort by balance descending
    sorted_data = sorted(data.items(), key=lambda x: x[1].get("balance", 0), reverse=True)

    embed = discord.Embed(title="🏆 Economy Leaderboard", color=discord.Color.gold())

    description = ""
    for i, (user_id, stats) in enumerate(sorted_data[:10], 1):
        member = ctx.guild.get_member(int(user_id))
        name = member.display_name if member else f"User {user_id}"
        description += f"**{i}. {name}** — {stats.get('balance', 0)}\n"

    embed.description = description
    await ctx.send(embed=embed)

async def setup_nodes():
    """Setup our Lavalink nodes."""
    await bot.wait_until_ready()
    # Using a known public lavalink node for testing
    # Note: Public nodes can be unstable. Consider hosting your own for production.
    nodes = [wavelink.Node(
        uri='https://lavalink.serenetia.com:443', 
        password='https://dsc.gg/ajidevserver'
    )]
    try:
        # Spotify integration is handled automatically if secrets are present
        await wavelink.Pool.connect(nodes=nodes, client=bot)
        print("Lavalink connected successfully")
    except Exception as e:
        print(f"Failed to connect to Lavalink: {e}")

# Temporary Voice Channel Configuration
# Replace these with your actual IDs after setup
TEMP_CATEGORY_ID = None  # ID of the category where temp channels will be created
CREATE_CHANNEL_ID = None # ID of the "Join to Create" channel
WELCOME_CHANNEL_ID = None # ID of the channel for welcome messages
JAIL_ROLE_ID = None # ID of the jail role
JAIL_CHANNEL_ID = None # ID of the jail channel
VERIFY_ROLE_ID = None # ID of the member role for verification
voice_owners = {} # {channel_id: owner_id}

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.success, emoji="✅", custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not VERIFY_ROLE_ID:
            return await interaction.response.send_message("Verification system is not setup.", ephemeral=True)

        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if not role:
            return await interaction.response.send_message("Verification role not found.", ephemeral=True)

        if role in interaction.user.roles:
            return await interaction.response.send_message("You are already verified!", ephemeral=True)

        await interaction.user.add_roles(role)
        await interaction.response.send_message("You have been successfully verified!", ephemeral=True)

class SelfRoleView(discord.ui.View):
    def __init__(self, roles_data):
        super().__init__(timeout=None)
        for role_id, label, emoji in roles_data:
            self.add_item(SelfRoleButton(role_id, label, emoji))

class SelfRoleButton(discord.ui.Button):
    def __init__(self, role_id, label, emoji):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, emoji=emoji, custom_id=f"role_{role_id}")
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        if not role:
            return await interaction.response.send_message("❌ Role not found.", ephemeral=True)

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"Removed role: {role.name}", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Added role: {role.name}", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def selfrole(ctx, *, args):
    """Setup self-roles. Format: !selfrole Title | Role1ID,Label1,Emoji1 | Role2ID,Label2,Emoji2"""
    parts = [p.strip() for p in args.split("|")]
    title = parts[0]
    roles_data = []
    for role_part in parts[1:]:
        role_id, label, emoji = [r.strip() for r in role_part.split(",")]
        roles_data.append((int(role_id), label, emoji))

    embed = discord.Embed(title=title, description="Click the buttons below to get your roles!", color=discord.Color.blue())
    await ctx.send(embed=embed, view=SelfRoleView(roles_data))
    await ctx.message.delete()

@bot.command()
@commands.has_permissions(administrator=True)
async def setverify(ctx, role: discord.Role, *, message="Click the button below to verify and access the server!"):
    """Setup the verification system."""
    global VERIFY_ROLE_ID
    VERIFY_ROLE_ID = role.id

    embed = discord.Embed(
        title="Server Verification",
        description=message,
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=VerifyView())
    await ctx.message.delete()

@bot.event
async def on_member_join(member):
    """Handle new members joining the server."""
    if WELCOME_CHANNEL_ID:
        channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="Welcome to the server!",
                description=f"Welcome {member.mention}! We're glad to have you here.",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Member #{len(member.guild.members)}")
            await channel.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setjail(ctx, role: discord.Role, channel: discord.TextChannel):
    """Setup the jail system."""
    global JAIL_ROLE_ID, JAIL_CHANNEL_ID
    JAIL_ROLE_ID = role.id
    JAIL_CHANNEL_ID = channel.id
    await ctx.send(f"✅ Jail system setup! Role: {role.mention}, Channel: {channel.mention}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def jail(ctx, member: discord.Member, *, reason="No reason provided"):
    """Jail a member."""
    if not JAIL_ROLE_ID or not JAIL_CHANNEL_ID:
        return await ctx.send("❌ Jail system is not setup. Use `!setjail` first.")

    jail_role = ctx.guild.get_role(JAIL_ROLE_ID)
    if not jail_role:
        return await ctx.send("❌ Jail role not found.")

    # Remove all roles and add jail role
    await member.edit(roles=[jail_role], reason=f"Jailed by {ctx.author}: {reason}")

    jail_channel = bot.get_channel(JAIL_CHANNEL_ID)
    if jail_channel:
        await jail_channel.send(f"⚖️ {member.mention}, you have been jailed.\n**Reason:** {reason}")

    await ctx.send(f"✅ **{member.name}** has been jailed.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def unjail(ctx, member: discord.Member):
    """Unjail a member."""
    if not JAIL_ROLE_ID:
        return await ctx.send("❌ Jail system is not setup.")

    jail_role = ctx.guild.get_role(JAIL_ROLE_ID)
    if jail_role in member.roles:
        await member.remove_roles(jail_role)
        await ctx.send(f"✅ **{member.name}** has been unjailed. Remember to re-add their roles manually.")
    else:
        await ctx.send(f"❌ **{member.name}** is not in jail.")

@bot.command()
@commands.has_permissions(administrator=True)
async def setwelcome(ctx, channel: discord.TextChannel):
    """Setup the welcome channel."""
    global WELCOME_CHANNEL_ID
    WELCOME_CHANNEL_ID = channel.id
    await ctx.send(f"✅ Welcome channel set to {channel.mention}!")

class VoiceInterface(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.secondary, emoji="🔒", custom_id="v_lock")
    async def lock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.voice and interaction.user.voice.channel.id in voice_owners:
            if voice_owners[interaction.user.voice.channel.id] == interaction.user.id:
                await interaction.user.voice.channel.set_permissions(interaction.guild.default_role, connect=False)
                await interaction.response.send_message("🔒 Channel locked.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ You are not the owner of this room.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ You are not in your voice room.", ephemeral=True)

    @discord.ui.button(label="Unlock", style=discord.ButtonStyle.secondary, emoji="🔓", custom_id="v_unlock")
    async def unlock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.voice and interaction.user.voice.channel.id in voice_owners:
            if voice_owners[interaction.user.voice.channel.id] == interaction.user.id:
                await interaction.user.voice.channel.set_permissions(interaction.guild.default_role, connect=True)
                await interaction.response.send_message("🔓 Channel unlocked.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ You are not the owner of this room.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ You are not in your voice room.", ephemeral=True)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, emoji="👑", custom_id="v_claim")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.voice and interaction.user.voice.channel.id in voice_owners:
            channel = interaction.user.voice.channel
            owner_id = voice_owners[channel.id]
            owner = interaction.guild.get_member(owner_id)

            if not owner or owner not in channel.members:
                voice_owners[channel.id] = interaction.user.id
                await interaction.response.send_message(f"👑 **{interaction.user.name}** is now the room owner.", ephemeral=False)
            else:
                await interaction.response.send_message("❌ The owner is still in the room.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ You are not in a temporary voice room.", ephemeral=True)

@bot.event
async def on_voice_state_update(member, before, after):
    """Handle temporary voice channel creation and deletion."""
    # 1. Handle Creation
    if after.channel and after.channel.id == CREATE_CHANNEL_ID:
        guild = member.guild
        category = discord.utils.get(guild.categories, id=TEMP_CATEGORY_ID)

        # Create a new temporary channel
        temp_channel = await guild.create_voice_channel(
            name=f"☁️ {member.name}'s Room",
            category=category,
            reason="Temporary voice channel creation"
        )

        # Track owner
        voice_owners[temp_channel.id] = member.id

        # Move the member to the new channel
        await member.move_to(temp_channel)

        # Send a log/welcome message tagging the user with interface in the NEW channel
        embed = discord.Embed(
            title="Voice Room Control",
            description=f"✨ **Welcome {member.mention}!**\nThis is your private room.\n\nUse the buttons below to manage your channel.",
            color=discord.Color.blue()
        )
        await temp_channel.send(content=member.mention, embed=embed, view=VoiceInterface())

    # 2. Handle Deletion
    if before.channel:
        # Check if the channel is a temporary one (starts with our prefix)
        if before.channel.name.startswith("☁️"):
            # If the channel is empty, delete it
            if len(before.channel.members) == 0:
                channel_id = before.channel.id
                await before.channel.delete(reason="Temporary voice channel empty")
                if channel_id in voice_owners:
                    del voice_owners[channel_id]

@bot.group(name="v", invoke_without_command=True)
async def voice_cmd(ctx):
    """Voice channel management commands."""
    await ctx.send("**Voice Commands:**\n`.v lock` | `.v unlock` | `.v reject @user` | `.v perm @user` | `.v claim` | `.v name <new name>`")

@voice_cmd.command()
async def lock(ctx):
    """Lock the voice channel."""
    if ctx.author.voice and ctx.author.voice.channel.id in voice_owners:
        if voice_owners[ctx.author.voice.channel.id] == ctx.author.id:
            await ctx.author.voice.channel.set_permissions(ctx.guild.default_role, connect=False)
            await ctx.send("🔒 Channel locked.")

@voice_cmd.command()
async def unlock(ctx):
    """Unlock the voice channel."""
    if ctx.author.voice and ctx.author.voice.channel.id in voice_owners:
        if voice_owners[ctx.author.voice.channel.id] == ctx.author.id:
            await ctx.author.voice.channel.set_permissions(ctx.guild.default_role, connect=True)
            await ctx.send("🔓 Channel unlocked.")

@voice_cmd.command()
async def reject(ctx, member: discord.Member):
    """Kick a user from your voice channel."""
    if ctx.author.voice and ctx.author.voice.channel.id in voice_owners:
        if voice_owners[ctx.author.voice.channel.id] == ctx.author.id:
            if member in ctx.author.voice.channel.members:
                await member.move_to(None)
                await ctx.author.voice.channel.set_permissions(member, connect=False)
                await ctx.send(f"🚫 Rejected **{member.name}**.")

@voice_cmd.command()
async def perm(ctx, member: discord.Member):
    """Give a user permission to join your locked channel."""
    if ctx.author.voice and ctx.author.voice.channel.id in voice_owners:
        if voice_owners[ctx.author.voice.channel.id] == ctx.author.id:
            await ctx.author.voice.channel.set_permissions(member, connect=True)
            await ctx.send(f"✅ Gave permission to **{member.name}**.")

@voice_cmd.command()
async def claim(ctx):
    """Claim ownership of the channel if the owner left."""
    if ctx.author.voice and ctx.author.voice.channel.id in voice_owners:
        channel = ctx.author.voice.channel
        owner_id = voice_owners[channel.id]
        owner = ctx.guild.get_member(owner_id)

        if not owner or owner not in channel.members:
            voice_owners[channel.id] = ctx.author.id
            await ctx.send(f"👑 **{ctx.author.name}** is now the room owner.")
        else:
            await ctx.send("❌ The owner is still in the room.")

@voice_cmd.command()
async def name(ctx, *, new_name: str):
    """Rename your voice channel."""
    if ctx.author.voice and ctx.author.voice.channel.id in voice_owners:
        if voice_owners[ctx.author.voice.channel.id] == ctx.author.id:
            await ctx.author.voice.channel.edit(name=f"☁️ {new_name}")
            await ctx.send(f"📝 Room renamed to: **{new_name}**")

@bot.command()
@commands.has_permissions(administrator=True)
async def setvoice(ctx, channel: discord.VoiceChannel, category: discord.CategoryChannel = None):
    """Setup the temporary voice channel system."""
    global CREATE_CHANNEL_ID, TEMP_CATEGORY_ID
    CREATE_CHANNEL_ID = channel.id
    TEMP_CATEGORY_ID = category.id if category else channel.category_id
    await ctx.send(f"✅ Temporary voice system setup! Join **{channel.name}** to create a room.")

@bot.event
async def on_ready():
    print("BOT ONLINE")
    bot.loop.create_task(setup_nodes())

@bot.command()
async def join(ctx):
    """Join the voice channel and stay 24/7."""
    if not ctx.author.voice:
        return await ctx.send("❌ You must be in a voice channel!")

    channel = ctx.author.voice.channel
    if ctx.voice_client:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect(cls=wavelink.Player, self_deaf=True)

    await ctx.send(f"✅ Joined **{channel.name}** and will stay 24/7.")

@bot.command(name="cr")
async def check_role(ctx, member: discord.Member = None):
    """Check a user's roles."""
    member = member or ctx.author
    roles = [role.mention for role in member.roles[1:]] # Exclude @everyone

    embed = discord.Embed(
        title=f"Roles for {member.display_name}",
        description=" ".join(roles) if roles else "No roles",
        color=member.color
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx, *, message):
    """Send a message that tags @everyone."""
    await ctx.send(f"@everyone {message}")
    await ctx.message.delete()

@bot.command()
@commands.has_permissions(administrator=True)
async def embed(ctx, title, *, description):
    """Send a customized embed. Usage: .embed Title | Description"""
    if "|" in description:
        title, description = [p.strip() for p in description.split("|", 1)]

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)
    await ctx.message.delete()

@bot.command(name="ms7")
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int):
    """Clear a specified amount of messages."""
    await ctx.channel.purge(limit=amount + 1)
    # The +1 is to include the command message itself
    # Optional: send a temporary confirmation message
    # await ctx.send(f"✅ Cleared {amount} messages.", delete_after=5)

@bot.command(name="topma")
async def top_maroc(ctx):
    """Show the top Moroccan servers (placeholder for Konan bot command)."""
    embed = discord.Embed(
        title="🇲🇦 Top Moroccan Servers",
        description="Here are the top ranked Moroccan servers:",
        color=discord.Color.red()
    )
    # This is a placeholder as actual rankings would require a database or API integration
    # For now, we provide a clean interface matching the request
    embed.add_field(name="1. Server Name", value="Score: 9999", inline=False)
    embed.add_field(name="2. Server Name", value="Score: 8888", inline=False)
    embed.add_field(name="3. Server Name", value="Score: 7777", inline=False)
    embed.set_footer(text="Rankings updated daily")
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command()
async def help(ctx):
    """A professionally designed help menu."""
    embed = discord.Embed(
        title="🤖 Bot Command Center",
        description="Select a category from the buttons below to see available commands.",
        color=discord.Color.blue()
    )
    embed.add_field(name="👑 Admin", value="Moderation & Setup", inline=True)
    embed.add_field(name="🎵 Music", value="Voice & Playback", inline=True)
    embed.add_field(name="💰 Economy", value="Work & Leaderboards", inline=True)
    embed.set_footer(text="Use .command to run a command")

    view = HelpView()
    await ctx.send(embed=embed, view=view)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Admin", style=discord.ButtonStyle.primary, emoji="👑")
    async def admin_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="👑 Admin & Moderation", color=discord.Color.red())
        commands_list = (
            "`.kick @user` - Kick a member\n"
            "`.ban @user` - Ban a member\n"
            "`.mute @user` - Mute a member\n"
            "`.jail @user` - Jail a member\n"
            "`.setwelcome #chan` - Setup welcome\n"
            "`.setverify @role` - Setup verification\n"
            "`.setvoice #chan` - Setup temp voice\n"
            "`.setup_tickets` - Setup ticket system"
        )
        embed.description = commands_list
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Music", style=discord.ButtonStyle.success, emoji="🎵")
    async def music_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎵 Music & Voice", color=discord.Color.green())
        commands_list = (
            "`.play <song>` - Play music\n"
            "`.skip` - Skip song\n"
            "`.stop` - Stop & Disconnect\n"
            "`.join` - Join voice 24/7\n"
            "`.v lock/unlock` - Temp room control"
        )
        embed.description = commands_list
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Economy", style=discord.ButtonStyle.secondary, emoji="💰")
    async def economy_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="💰 Economy & Fun", color=discord.Color.gold())
        commands_list = (
            "`.work` - Earn money\n"
            "`.bal` - Check balance\n"
            "`.rank` - Check your level\n"
            "`.leaderboard` - Server rich list\n"
            "`.topma` - Top Moroccan servers\n"
            "`.a @user` - Show avatar\n"
            "`.b @user` - Show banner"
        )
        embed.description = commands_list
        await interaction.response.edit_message(embed=embed)

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.name}!")

@bot.command()
async def play(ctx: commands.Context, *, search: str):
    """Play a song."""
    if not ctx.author.voice:
        return await ctx.send("You must be in a voice channel to use this command.")

    if not ctx.voice_client:
        try:
            vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
        except Exception as e:
            return await ctx.send(f"Could not connect to voice channel: {e}")
    else:
        vc: wavelink.Player = ctx.voice_client

    try:
        # Check if search is a Spotify URL
        if "open.spotify.com" in search:
            from wavelink.ext import spotify
            decoded = spotify.decode_url(search)
            if decoded and decoded['type'] in (spotify.SpotifySearchType.track, spotify.SpotifySearchType.album, spotify.SpotifySearchType.playlist):
                tracks = await spotify.SpotifyTrack.search(query=search)
                if not tracks:
                    return await ctx.send("No results found on Spotify.")
                
                if isinstance(tracks, spotify.SpotifyPlaylist):
                    for track in tracks.tracks:
                        await vc.queue.put_wait(track)
                    await ctx.send(f"Added playlist **{tracks.name}** to queue.")
                else:
                    track = tracks[0]
                    await vc.play(track)
                    await ctx.send(f"Playing Spotify track: **{track.title}**")
                
                if not vc.playing:
                    await vc.play(vc.queue.get())
                return

        # Default YouTube search
        tracks = await wavelink.Playable.search(search)
        if not tracks:
            return await ctx.send("No results found.")

        track = tracks[0]
        await vc.play(track)
        await ctx.send(f"Playing: **{track.title}**")
    except Exception as e:
        await ctx.send(f"An error occurred while playing: {e}")
        # Note: Lavalink server must be running and connected for this to work
        if not wavelink.Pool.nodes:
             return await ctx.send("The music server (Lavalink) is not connected. Please check the bot's setup.")

        # Search for the track using YoutubeMusic source explicitly
        tracks: wavelink.Search = await wavelink.Playable.search(search, source=wavelink.TrackSource.YouTube)
        if not tracks:
            # Fallback to standard search if YouTube source fails
            tracks = await wavelink.Playable.search(search)

        if not tracks:
            return await ctx.send(f"No tracks found for: **{search}**")

        track = tracks[0]
        await vc.play(track)
        await ctx.send(f"Playing **{track.title}**")
    except Exception as e:
        await ctx.send(f"An error occurred while trying to play: {e}")

@bot.command()
async def skip(ctx: commands.Context):
    """Skip the current song."""
    vc: wavelink.Player = ctx.voice_client
    if vc:
        await vc.skip()
        await ctx.send("Skipped!")

@bot.command()
async def stop(ctx: commands.Context):
    """Stop the player."""
    vc: wavelink.Player = ctx.voice_client
    if vc:
        await vc.disconnect()
        await ctx.send("Stopped and disconnected.")

@bot.command(name="a")
async def avatar(ctx, member: discord.Member = None):
    """Show a user's avatar."""
    member = member or ctx.author
    await ctx.send(member.display_avatar.url)

@bot.command(name="b")
async def banner(ctx, member: discord.Member = None):
    """Show a user's banner."""
    member = member or ctx.author
    user = await bot.fetch_user(member.id)
    if user.banner:
        await ctx.send(user.banner.url)
    else:
        await ctx.send(f"**{user.name}** does not have a banner.")

# Moderation Commands
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    """Kick a member."""
    await member.kick(reason=reason)
    await ctx.send(f"Kicked **{member.name}** | Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    """Ban a member."""
    await member.ban(reason=reason)
    await ctx.send(f"Banned **{member.name}** | Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member):
    """Unban a member."""
    banned_users = [entry async for entry in ctx.guild.bans()]
    member_name, member_discriminator = member.split('#') if '#' in member else (member, None)

    for ban_entry in banned_users:
        user = ban_entry.user
        if (user.name, user.discriminator) == (member_name, member_discriminator) or user.name == member_name:
            await ctx.guild.unban(user)
            await ctx.send(f"Unbanned **{user.name}**")
            return
    await ctx.send(f"Could not find **{member}** in ban list.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    """Mute a member by removing their permission to speak."""
    await member.edit(mute=True, reason=reason)
    await ctx.send(f"Muted **{member.name}** | Reason: {reason}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def unmute(ctx, member: discord.Member):
    """Unmute a member."""
    await member.edit(mute=False)
    await ctx.send(f"Unmuted **{member.name}**")

@bot.command()
@commands.has_permissions(move_members=True)
async def move(ctx, member: discord.Member, channel: discord.VoiceChannel):
    """Move a member to a different voice channel."""
    await member.move_to(channel)
    await ctx.send(f"Moved **{member.name}** to **{channel.name}**")

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # Create a new ticket channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=interaction.channel.category,
            overwrites=overwrites,
            reason=f"Ticket created by {user.name}"
        )

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=f"Welcome {user.mention}!\nPlease describe your issue and our staff will be with you shortly.",
            color=discord.Color.green()
        )
        embed.set_timestamp()

        view = discord.ui.View(timeout=None)
        close_button = discord.ui.Button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")

        async def close_callback(close_interaction: discord.Interaction):
            await close_interaction.response.send_message("🔒 Closing ticket in 5 seconds...")
            await asyncio.sleep(5)
            await close_interaction.channel.delete()

        close_button.callback = close_callback
        view.add_item(close_button)

        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Ticket created! {channel.mention}", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx):
    """Setup the ticket system."""
    embed = discord.Embed(
        title="🎫 Support Tickets",
        description="Need help? Click the button below to create a support ticket.\n\nOur staff team will assist you shortly.",
        color=discord.Color.blurple()
    )
    embed.add_field(name="📋 General Support", value="For general questions and help")
    embed.add_field(name="⚠️ Report Issue", value="Report bugs or issues")

    await ctx.send(embed=embed, view=TicketView())
    await ctx.message.delete()

# Leveling System Helper Functions
def load_xp():
    try:
        with open("xp_data.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_xp(data):
    with open("xp_data.json", "w") as f:
        json.dump(data, f, indent=4)

def get_xp_needed(level):
    return level * 100

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Process XP
    xp_data = load_xp()
    user_id = str(message.author.id)
    user_stats = xp_data.get(user_id, {"xp": 0, "level": 1})

    # Gain XP (15-25)
    xp_gain = random.randint(15, 25)
    user_stats["xp"] += xp_gain

    xp_needed = get_xp_needed(user_stats["level"])

    if user_stats["xp"] >= xp_needed:
        user_stats["level"] += 1
        user_stats["xp"] = 0

        embed = discord.Embed(
            title="🎉 Level Up!",
            description=f"Congratulations {message.author.mention}! You reached level **{user_stats['level']}**!",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        await message.channel.send(embed=embed)

        # Role rewards
        role_rewards = {
            5: "Active Member",
            10: "Veteran",
            20: "Elite"
        }

        if user_stats["level"] in role_rewards:
            role_name = role_rewards[user_stats["level"]]
            role = discord.utils.get(message.guild.roles, name=role_name)
            if role:
                await message.author.add_roles(role)

    xp_data[user_id] = user_stats
    save_xp(xp_data)

    # Crucial: Allow bot commands to work
    await bot.process_commands(message)

@bot.command()
async def rank(ctx, member: discord.Member = None):
    """Check your or another member's level rank."""
    member = member or ctx.author
    xp_data = load_xp()
    user_stats = xp_data.get(str(member.id), {"xp": 0, "level": 1})

    next_level_xp = get_xp_needed(user_stats["level"])
    progress = (user_stats["xp"] / next_level_xp) * 100

    embed = discord.Embed(
        title=f"📊 {member.display_name}'s Rank",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Level", value=user_stats["level"], inline=True)
    embed.add_field(name="XP", value=f"{user_stats['xp']}/{next_level_xp}", inline=True)
    embed.add_field(name="Progress", value=f"{progress:.1f}%", inline=True)
    await ctx.send(embed=embed)
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive", 200

def run():
    app.run(host="0.0.0.0", port=5000)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

bot.run(os.getenv("TOKEN"))
