import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ---------- LOAD ENV ----------
load_dotenv()
TOKEN = os.getenv("TOKEN")

# ---------- CONFIG ----------
PREFIX = "."

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None  # باش نديرو help ديالنا بلا conflict
)

# ---------- EVENTS ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{PREFIX}help"
        )
    )

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    channel = guild.system_channel

    if channel is None:
        me = guild.get_member(bot.user.id)
        for ch in guild.text_channels:
            if me and ch.permissions_for(me).send_messages:
                channel = ch
                break

    if channel:
        await channel.send(f"👋 Marhba bik f **{guild.name}**, {member.mention}!")

# ---------- ERROR HANDLER ----------
@bot.event
async def on_command_error(ctx: commands.Context, error):
    error = getattr(error, "original", error)

    if isinstance(error, commands.MissingPermissions):
        return await ctx.send("❌ sir thwa Ma 3endkch permission bach tdir had lcommand azbi wa sir ola bani zaml bok <@1096040800325992450> <@1183246467096391683>  bani had zbi.")
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send("❌ Khassk t3ti arguments kamlin. Chof  `!help`mkilakh .")
    if isinstance(error, commands.BadArgument):
        return await ctx.send("❌ Argument ma si7i7ch. Chof format dyal command.")
    if isinstance(error, commands.CommandNotFound):
        return

    print(f"❌ Error: {error}")

# ---------- FUN / BASIC ----------
@bot.command()
async def ping(ctx: commands.Context):
    msg = await ctx.send("Pinging...")
    latency = (msg.created_at - ctx.message.created_at).total_seconds() * 1000
    api_ping = bot.latency * 1000
    await msg.edit(content=f"🏓 Pong! Bot: `{latency:.0f}ms` | API: `{api_ping:.0f}ms`")

@bot.command()
async def say(ctx: commands.Context, *, text: str):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass
    await ctx.send(text)

# ---------- MODERATION ----------
@bot.command(aliases=["purge"])
@commands.has_permissions(manage_messages=True)
async def clear(ctx: commands.Context, amount: int):
    if amount < 1 or amount > 100:
        return await ctx.send("🧹 Ist3ml: `!clear <1-100>`")

    deleted = await ctx.channel.purge(limit=amount + 1, bulk=True)
    msg = await ctx.send(f"✅ Tmsa7o {len(deleted) - 1} message.")
    await msg.delete(delay=3)

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    if not member.kickable:
        return await ctx.send("❌ Ma n9drch nkick had user (role a3la mn bot wela 3ndo admin).")
    await member.kick(reason=reason)
    await ctx.send(f"✅ {member} tkick. Reason: **{reason}**")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    if not member.bannable:
        return await ctx.send("❌ Ma n9drch nban had user (role a3la mn bot wela 3ndo admin).")
    await member.ban(reason=reason)
    await ctx.send(f"⛔ {member} tban. Reason: **{reason}**")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx: commands.Context, user_id: int, *, reason: str = "Unbanned"):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=reason)
        await ctx.send(f"✅ {user} tft7 lih lban.")
    except discord.NotFound:
        await ctx.send("❌ Ma l9it hta chi ban b had ID.")
    except discord.Forbidden:
        await ctx.send("❌ Ma 3endich permission (Ban Members) باش ndir unban.")

# ---------- INFO ----------
@bot.command()
async def userinfo(ctx: commands.Context, member: discord.Member = None):
    member = member or ctx.author
    roles = [r.mention for r in member.roles if r != ctx.guild.default_role]
    roles_text = ", ".join(roles) if roles else "No roles"

    embed = discord.Embed(title=f"Info dyal {member}", color=discord.Color.green())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="🆔 ID", value=str(member.id), inline=True)
    embed.add_field(name="📛 Username", value=str(member), inline=True)
    embed.add_field(
        name="📅 Joined server",
        value=discord.utils.format_dt(member.joined_at, style="R") if member.joined_at else "N/A",
        inline=True
    )
    embed.add_field(
        name="📅 Account created",
        value=discord.utils.format_dt(member.created_at, style="R"),
        inline=True
    )
    embed.add_field(name="🎭 Roles", value=roles_text, inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def s(ctx: commands.Context):
    guild = ctx.guild
    embed = discord.Embed(title=f"Info dyal server: {guild.name}", color=discord.Color.orange())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name="🆔 ID", value=str(guild.id), inline=True)
    embed.add_field(name="👑 Owner", value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name="👥 Members", value=str(guild.member_count), inline=True)
    embed.add_field(name="📅 Created", value=discord.utils.format_dt(guild.created_at, style="R"), inline=True)
    embed.add_field(name="💬 Text channels", value=str(len(guild.text_channels)), inline=True)
    embed.add_field(name="🔊 Voice channels", value=str(len(guild.voice_channels)), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def a(ctx: commands.Context, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"Avatar dyal {member}", color=discord.Color.blue())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

# ---------- CUSTOM HELP ----------
@bot.command(name="help")
async def help_cmd(ctx: commands.Context):
    embed = discord.Embed(
        title="📜 Commands",
        description=f"Prefix: `{PREFIX}`",
        color=discord.Color.blurple()
    )
    embed.add_field(name="🎉 Fun", value="`!ping`\n`!say <message>`", inline=False)
    embed.add_field(
        name="🔧 Moderation",
        value="`!clear <1-100>`\n`!kick @user [reason]`\n`!ban @user [reason]`\n`!unban <userId> [reason]`",
        inline=False
    )
    embed.add_field(
        name="ℹ️ Info",
        value="`!s`\n`!userinfo [@user]`\n`!a [@user]`",
        inline=False
    )
    await ctx.send(embed=embed)

# ---------- RUN ----------
if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("❌ TOKEN ma kaynach. 7et TOKEN f .env wla f Secrets dyal lhost.")
    bot.run(TOKEN)
