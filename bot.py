import asyncio
import os
import datetime
import threading

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
    players.append(Player(int(result[0]), result[1], result[2], result[3], result[4], result[5]))

# initialise game list
games = []


def check_games(timer_event):
    # Game has no active players, remove it from list
    print('Checking activity in games...')
    n = 0
    for game in games:
        if len(game.active) == 0:
            n += 1
            games.remove(game)
    print('Removed {0} games, {1} active games left.'.format(n, len(games)))

    # When timer_event is false, start thread timer for 5 minutes
    if not timer_event.is_set():
        threading.Timer(300, check_games, [timer_event]).start()


timer_event = threading.Event()
check_games(timer_event)


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
    players.append(Player(ctx.author.id, ctx.author.name, ctx.guild.get_member(ctx.author.id).display_name, 0, 0))
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
            last_reward = datetime.datetime.strptime(str(sql.read_query(sql.sql_connection, query)[0][0]), '%Y-%m-%d %H:%M:%S')
            if last_reward is not None:
                now = datetime.datetime.now()
                if now - datetime.timedelta(minutes=30) >= last_reward:
                    await ctx.send('You\'ve redeemed your $200 reward, 30 minutes until next reward!')
                    player.change_balance(200)
                    update = '''
                    UPDATE players
                    SET last_reward = NOW()
                    WHERE user_id = {0}
                    '''.format(ctx.author.id)
                    sql.execute_query(sql.sql_connection, update)
                else:
                    seconds = (last_reward + datetime.timedelta(minutes=30) - now).total_seconds()
                    hours = seconds // 3600
                    seconds -= hours * 3600
                    minutes = seconds // 60
                    seconds -= minutes * 60
                    await ctx.send('Please wait {:02}:{:02}:{:02} until reward can be granted!'.format(int(hours), int(minutes), int(seconds)))
                return
    # Otherwise, create new Player and record, adding them to game
    players.append(Player(ctx.author.id, ctx.author.name, ctx.guild.get_member(ctx.author.id).display_name, 0, 0))
    players[len(players) - 1].create_record()
    await ctx.send('You\'ve redeemed your $200 reward, 30 minutes until next reward!')


@bot.command()
async def blackjack(ctx):
    for game in games:
        if len(game.active) == 0:
            games.remove(game)
    # Check if user is currently playing blackjack
    for game in games:
        for player in game.active:
            if player.id == ctx.author.id:
                await ctx.send('You are currently playing blackjack!\nLeave previous game to continue.')
                return

    for game in games:
        # Else check if channel is already hosting blackjack
        if game.channel == ctx.channel:
            await ctx.send('{0} has joined the table and queued for next round.'.format(
                ctx.guild.get_member(ctx.author.id).display_name))
            for player in players:
                if player.id == ctx.author.id:
                    game.queue.append(player)
                    return
            # User doesn't exist in player database, create new Player and record
            players.append(Player(ctx.author.id, ctx.author.name, ctx.guild.get_member(ctx.author.id).display_name, 0, 0))
            players[len(players) - 1].create_record()
            game.queue.append(players[len(players) - 1])
            return

    # Otherwise start new game of blackjack
    await ctx.send('@here, first round of **BLACKJACK** begins in 10 seconds, quickly join for first round!')
    games.append(Blackjack(ctx.channel))

    # Check if user exists in player database, adding them to game
    for player in players:
        if player.id == ctx.author.id:
            games[len(games) - 1].queue.append(player)
            await asyncio.sleep(7)
            await games[len(games) - 1].start()
            return

    # Otherwise, create new Player and record, adding them to game
    players.append(Player(ctx.author.id, ctx.author.name, ctx.guild.get_member(ctx.author.id).display_name, 0, 0))
    players[len(players) - 1].create_record()
    games[len(games) - 1].queue.append(players[len(players) - 1])
    await asyncio.sleep(7)
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
                        if player.hands[0].bet > amount:
                            await ctx.send('You have already bet ${0}.'.format(amount))
                        else:
                            player.hands[0].bet = amount
                            await ctx.send('{0} is betting ${1}.'.format(player.display_name, amount))
                            await game.all_bets()
                    else:
                        await ctx.send('Betting period has already ended!')
                    return


def check_game(ctx, game) -> bool:
    # Check if player message in correct channel, in correct game status and is current action player
    if game.channel == ctx.channel and game.status == Status.ACTION:
        if game.active[game.current_player].id == ctx.author.id:
            return True
    return False


@bot.command()
async def hit(ctx):
    for game in games:
        if check_game(ctx, game):
            await game.hit(game.active[game.current_player])


@bot.command()
async def split(ctx):
    for game in games:
        if check_game(ctx, game):
            await game.split(game.active[game.current_player])


@bot.command()
async def double(ctx):
    for game in games:
        if check_game(ctx, game):
            await game.double(game.active[game.current_player])


@bot.command()
async def even(ctx):
    for game in games:
        if check_game(ctx, game):
            await game.even(game.active[game.current_player])


@bot.command()
async def insurance(ctx, amount: int):
    for game in games:
        if check_game(ctx, game):
            await game.insurance(game.active[game.current_player], amount)


@bot.command()
async def stay(ctx):
    for game in games:
        if check_game(ctx, game):
            await game.stand()


@bot.command()
async def surrender(ctx):
    for game in games:
        if check_game(ctx, game):
            await game.surrender(game.active[game.current_player])


@bot.command()
async def leave(ctx):
    for game in games:
        # Check active players
        for player in game.active:
            if player.id == ctx.author.id:
                # If player already bet, player will lose bet
                hand_sum = 0
                if len(player.hands) > 0:
                    for hand in player.hands:
                        hand_sum += hand.bet
                player.change_balance(-1 * hand_sum)

                # remove player from active list
                game.active.remove(player)

                if ctx.channel != game.channel:
                    await ctx.send('You have left the table in {0}, forfeiting ${1}!'.format(game.channel.user_name, hand_sum))
                await game.channel.send(
                    '{0} has left the table.'.format(ctx.guild.get_member(ctx.author.id).display_name))
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
