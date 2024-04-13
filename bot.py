import os
import datetime

from dotenv import load_dotenv

import discord
from discord.ext import commands

import sql

from blackjack import Blackjack, Status
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
            await ctx.send('@{0.display_name}\'s current balance is ${0.balance}.'.format(player))
            return
    # Otherwise create a new Player with default balance
    players.append(Player(ctx.author.id, ctx.author.name, ctx.guild.get_member(ctx.author.id).display_name))
    players[len(players) - 1].create_record()
    await ctx.send('@{0.display_name}\'s current balance is ${0.balance}.'.format(players[len(players) - 1]))


@bot.command()
async def reward(ctx):
    for player in players:
        if player.id == ctx.author.id:
            query = '''
            SELECT last_reward FROM players
            WHERE user_id = '{0}'
            '''.format(ctx.author.id)
            last_reward = sql.read_query(sql.sql_connection, query)[0][0]
            if last_reward is not None:
                now = datetime.datetime.now()
                if now - datetime.timedelta(minutes=30) >= last_reward:
                    await ctx.send('You\'ve redeemed your $200 reward, 30 minutes until next reward!')
                    player.deposit(200)
                    update = '''
                    UPDATE players
                    SET last_reward = NOW()
                    WHERE user_id = {0}
                    '''.format(ctx.author.id)
                    sql.execute_query(sql.sql_connection, update)
                else:
                    await ctx.send('Please wait, {0} until reward can be granted!'.format(datetime.datetime.strftime(now - last_reward, '%H:%M:%S')))


@bot.command()
async def blackjack(ctx):
    # Check if user is currently playing blackjack
    for game in games:
        for player in game.active:
            if player.id == ctx.author.id:
                await ctx.send('You are currently playing blackjack!\nLeave previous game to continue.')
                return

    # Check if channel is already hosting blackjack
    for game in games:
        if game.channel == ctx.channel:
            await ctx.send('{0} has joined the table and queued for next round.'.format(ctx.guild.get_member(ctx.author.id).display_name))
            for player in players:
                if player.id == ctx.author.id:
                    game.queue.append(player)
                    return
            # User doesn't exist in player database, create new Player and record
            players.append(Player(ctx.author.id, ctx.author.name, ctx.guild.get_member(ctx.author.id).display_name))
            players[len(players) - 1].create_record()
            game.queue.append(players[len(players) - 1])
            return

    # Otherwise start new game of blackjack
    await ctx.send('@here, first round of **BLACKJACK** begins in 10 seconds, quickly join for first round!')
    games.append(Blackjack(ctx.channel))
    for player in players:
        if player.id == ctx.author.id:
            games[len(games) - 1].queue.append(player)
    await games[len(games) - 1].start()


@bot.command()
async def bet(ctx, amount: int):
    # Check if user is currently playing and is messaging in correct channel
    for game in games:
        if game.channel == ctx.channel:
            for player in game.active:
                if player.id == ctx.author.id:
                    if game.status == Status.BET:
                        if amount < 10:
                            await ctx.send('Bet must be more than $10')
                            return
                        if player.bet > amount:
                            await ctx.send('You have already bet ${1}.'.format(player.user_name, amount))
                        else:
                            player.bet = amount
                            await ctx.send('{0} is betting ${1}.'.format(player.user_name, amount))
                    else:
                        await ctx.send('Betting period has already ended!')
                    return


@bot.command()
async def hit(ctx):
    # Check if player message in correct channel and is current action player
    for game in games:
        if game.channel == ctx.channel and game.status == Status.ACTION:
            if game.active[game.current_player].id == ctx.author.id:
                game.hit(game.active[game.current_player])


@bot.command()
async def split(ctx):
    # Check if player message in correct channel and is current action player
    for game in games:
        if game.channel == ctx.channel and game.status == Status.ACTION:
            if game.active[game.current_player].id == ctx.author.id:
                game.split(game.active[game.current_player])


@bot.command()
async def stay(ctx):
    # Check if player message in correct channel and is current action player
    for game in games:
        if game.channel == ctx.channel and game.status == Status.ACTION:
            if game.active[game.current_player].id == ctx.author.id:
                game.stand(game.active[game.current_player])


@bot.command()
async def leave(ctx):
    for game in games:
        # Check active players
        for player in game.active:
            if player.id == ctx.author.id:
                # If player already bet, player will lose bet
                if player.bet > 0:
                    player.withdraw(player.bet)
                # remove player from active list
                game.active.remove(player)

                if ctx.channel != game.channel:
                    await ctx.send('You have left the table in {0}'.format(game.channel.user_name))
                await game.channel.send('{0} has left the table'.format(ctx.guild.get_member(ctx.author.id).display_name))
                # Check if there are still active players else remove game
                if len(game.active) == 0:
                    await game.channel.send('No active players in blackjack, closing game!')
                    games.remove(game)
                return
        # Check queued players
        for player in game.queue:
            if player.id == ctx.author.id:
                game.queue.remove(player)
                return


bot.run(discord_token)
