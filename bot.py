import os
from dotenv import load_dotenv

import discord
from discord.ext import commands

import sql
from blackjack import Blackjack
from player import Player

load_dotenv()
discord_token = os.environ['DISCORD_TOKEN']
bot = commands.Bot(command_prefix='$', intents=discord.Intents.all())

# read data from users table
players = []
results = sql.read_query(sql.sql_connection, 'SELECT * FROM players')
for result in results:
    result = list(result)
    players.append(Player(int(result[0]), result[1], result[2]))

# initialise game list
games = []


@bot.event
async def on_ready():
    print('Logged in as {0.user}'.format(bot))


@bot.event
async def on_command_error(ctx, error):
    await ctx.send('Unknown command: {error}'.format(error=error))


@bot.command()
async def bal(ctx):
    # Check if user is players list
    for player in players:
        if player.id == ctx.author.id:
            await ctx.send('{0.name}\'s current balance is {0.balance}.'.format(player))
            return
    # Otherwise no data
    await ctx.send('{0.name}\'s doesn\'t have a balance.'.format(ctx.author))


@bot.command()
async def blackjack(ctx):
    # Stop if user is bot
    if bot.user.id == ctx.author.id:
        return
    # Check if user is currently playing blackjack
    for game in games:
        for player in game.active:
            if player.id == ctx.author.id:
                await ctx.send('You are currently playing blackjack!\nLeave previous game to continue.')
                return

    # Check if channel is already hosting blackjack
    for game in games:
        if game.channel == ctx.channel:
            await ctx.send('{0} has joined the table and queued for next round.'.format(ctx.author.name))
            for player in players:
                if player.id == ctx.author.id:
                    game.queue.append(player)
                    return
            # User doesn't exist in player database, create new Player and record
            players.append(Player(ctx.author.id, ctx.author.name))
            players[len(players) - 1].create_record()
            game.queue.append(players[len(players) - 1])
            return

    # Otherwise start new game of blackjack
    await ctx.send('@here, first round of *BLACKJACK* begins in 10 seconds, quickly join for first round!')
    games.append(Blackjack(ctx.channel, ctx.author))


@bot.command()
async def bet(ctx, amount: int):
    # Check if user is currently playing and is messaging in correct channel
    for game in games:
        if game.channel == ctx.channel:
            for player in game.active:
                if player.id == ctx.author.id:
                    if game.status.BET:
                        if amount <= 0:
                            await ctx.send('Cannot bet a negative amount!')
                            return
                        if player.bet > amount:
                            player.bet(amount)
                            await ctx.send('{0} is betting {1}.'.format(player.name, amount))
                        else:
                            await ctx.send('You have already bet {1}.'.format(player.name, amount))
                    else:
                        await ctx.send('Betting period has already ended!')
                    return


@bot.command()
async def leave(ctx):
    for game in games:
        # Check active players
        for player in game.active:
            if player.id == ctx.author.id:
                if player.bet > 0:
                    player.lose_bet()
                game.active.remove(player)
                if ctx.channel != game.channel:
                    await ctx.send('You have left the table in {0}'.format(game.channel.name))
                await game.channel.send('{0} has left the table'.format(ctx.author.name))
                return
        # Check queued players
        for player in game.queue:
            if player.id == ctx.author.id:
                game.queue.remove(player)
                return


bot.run(discord_token)
