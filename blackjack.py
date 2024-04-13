import asyncio
from enum import Enum

from deck import Deck
from player import Player, Action


class Status(Enum):
    START = 1
    BET = 2
    DEAL = 3
    ACTION = 4
    END = 4


class Blackjack:
    def __init__(self, channel):
        self.channel = channel
        self.active = []
        self.current_player = 0
        self.current_hand = 0
        self.queue = []
        self.deck = Deck()
        self.dealer = []
        self.status = Status.START
        self.action_input = asyncio.Event()

    async def start(self):
        self.active.extend(self.queue)
        self.queue.clear()
        self.deck.shuffle()
        await asyncio.sleep(3)
        await self.channel.send('3... 2... 1...')
        await asyncio.sleep(3)
        await self.bet()

    async def bet(self):
        self.status = Status.BET
        await self.channel.send('Place initial bets!')
        await asyncio.sleep(3)
        await self.channel.send('3... 2... 1...')
        await asyncio.sleep(3)
        await self.deal()

    async def deal(self):
        self.status = Status.DEAL
        # Remove any player that didn't place a bet
        for player in self.active:
            if player.bet == 0:
                self.active.remove(player)
                self.queue.append(player)
                await self.channel.send('@{0} didn\'t place a bet in time, forfeiting the round.'.format(player.user_name))
        # Check if there are still active players
        if len(self.active) == 0:
            await self.channel.send('No active players in blackjack, closing game!')
            # TODO: how to delete reference to this game in the bot.games list
            return

        await self.channel.send('Dealing cards...')
        await asyncio.sleep(2)
        # Deal two rounds of cards to players and dealer
        for i in range(2):
            for player in self.active:
                for hand in player.hands:
                    hand.cards.append(self.deck.cards[0])
                    self.deck.cards.pop(0)
            # Automatically hide dealer's cards
            self.deck.cards[0].hidden = True
            self.dealer.append(self.deck.cards[0])
            self.deck.cards.pop(0)

        for player in self.active:
            for i in range(len(player.hands)):
                if len(player.hands) == 1:
                    await self.channel.send('@{0}\'s hand: {1}'.format(player.user_name, player.hands[i]))
                else:
                    await self.channel.send('@{0}\'s **Hand #{1}**: {2}'.format(player.user_name, i, player.hands[i]))
                await asyncio.sleep(1)

        # Show dealer's second card
        self.dealer[1].hidden = False
        await self.channel.send('dealer\'s hand: {0}\n '.format(self.dealer))
        await asyncio.sleep(1)
        await self.action_player()

    async def action_player(self):
        self.status = Status.ACTION
        # loop through players
        for i in range(len(self.active)):
            self.current_player = i
            # loop through player's hands (normally only 1)
            player = self.active[self.current_player]
            for j in range(len(player.hands)):
                self.current_hand = j
                await self.action_hand(player)

    async def action_hand(self, player):
        # reset action flag to false
        self.action_input.clear()
        # can this hand split?
        if player.hands[self.current_hand].can_split():
            if len(player.hands) == 1:
                await self.channel.send('@{0}\'s turn, are you staying or hitting?'.format(player.user_name))
            else:
                await self.channel.send('@{0}\'s turn for **Hand #{1}**, are you staying or hitting?'.format(player.user_name, self.current_hand))
        else:
            if len(player.hands) == 1:
                await self.channel.send(
                    '@{0}\'s turn, are you staying, hitting or **SPLITING**?'.format(player.user_name))
            else:
                await self.channel.send(
                    '@{0}\'s turn for **Hand #{1}**, are you staying, hitting or **SPLITING**?'.format(player.user_name, self.current_hand))
        await self.action_input.wait()
        # If action continue (when hitting or splitting) then repeat this function until action is break
        if player.action == Action.REPEAT:
            await self.action_hand(player)

    async def hit(self, player: Player):
        player.action = Action.REPEAT
        # Add card to current hand from deck
        player.hands[self.current_hand].append(self.deck.cards[0])
        self.deck.cards.pop(0)

        if len(player.hands) == 1:
            await self.channel.send('@{0}\'s hand: {1}'.format(player.user_name, player.hands[self.current_hand]))
        else:
            await self.channel.send(
                '@{0}\'s **hand #{1}**: {2}'.format(player.user_name, self.current_hand, player.hands[self.current_hand]))

        await asyncio.sleep(1)
        # Is this hand over 21?
        if player.hands[self.current_hand].sum() > 21:
            if len(player.hands) == 1:
                await self.channel.send('@{0}\'s hand is bust!'.format(player.user_name))
            else:
                await self.channel.send('@{0}\'s **hand #{1}** is bust!'.format(player.user_name, self.current_hand))
            player.hands.pop(self.current_hand)
            player.action = Action.BREAK
        self.action_input.set()

    async def split(self, player: Player):
        hand = player.hands[self.current_hand]
        # can this hand split?
        if hand.can_split():
            player.action = Action.REPEAT
            # Add new hand with the first card from the current hand and at the current hand's position in list
            player.hands.insert(self.current_hand, hand.cards[0])
            # remove the first card from the current hand
            hand.cards.pop(0)

            await self.channel.send('@{0} has split his hand! Your hands are now:'.format(player.user_name, self.current_hand))
            for i in range(len(player.hands)):
                await self.channel.send('**Hand #{1}**: {1}'.format(player.user_name, i, player.hands[i]))
            self.action_input.set()

    async def stand(self, player: Player):
        player.action = Action.BREAK
        self.action_input.set()
