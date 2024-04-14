import asyncio
from enum import Enum

from deck import Deck, Hand
from player import Player


class Status(Enum):
    START = 1
    BET = 2
    DEAL = 3
    ACTION = 4
    END = 5


class Blackjack:
    def __init__(self, channel):
        self.channel = channel
        self.active = []
        self.queue = []
        self.current_player = 0
        self.current_hand = 0
        self.num_actions = 0
        self.deck = Deck()
        self.dealer = Hand(0)
        self.status = Status.START
        self.action_input = asyncio.Event()

    async def start(self):
        self.active.extend(self.queue)
        self.queue.clear()
        self.deck.reset_deck()
        await self.channel.send('3... 2... 1...')
        await asyncio.sleep(3)
        await self.bet()

    async def bet(self):
        self.status = Status.BET
        await self.channel.send('Place initial bets!')
        await asyncio.sleep(3)
        # Check if all_bets has overrided this function
        if self.status == Status.BET:
            await self.channel.send('3... 2... 1...')
            await asyncio.sleep(3)
            # Check if all_bets has overrided this function
            if self.status == Status.BET:
                await self.deal()

    async def all_bets(self):
        for player in self.active:
            if player.hands[0].bet == 0:
                return
        await self.deal()

    async def deal(self):
        self.status = Status.DEAL
        # Remove any player that didn't place a bet
        for player in self.active:
            if player.bet == 0:
                self.active.remove(player)
                self.queue.append(player)
                await self.channel.send(
                    '@{0} didn\'t place a bet in time, forfeiting the round.'.format(player.display_name))
        # Check if there are still active players
        if len(self.active) == 0:
            await self.channel.send('No active players in blackjack, closing game!')
            return

        await self.channel.send('Dealing cards...')
        await asyncio.sleep(2)
        # Deal two rounds of cards to players and dealer
        for i in range(2):
            for player in self.active:
                for hand in player.hands:
                    hand.cards.append(self.deck.cards[0])
                    self.deck.remove_card()
            # Automatically hide dealer's cards
            self.deck.cards[0].hidden = True
            self.dealer.cards.append(self.deck.cards[0])
            self.deck.cards.remove_card()

        for player in self.active:
            await self.channel.send(
                '@{0}\'s hand (${1}): {2}'.format(player.display_name, player.hands[self.current_hand].bet,
                                                  str(player.hands[0])))
            await asyncio.sleep(1)

        # Show dealer's second card
        self.dealer.cards[1].hidden = False
        await self.channel.send('dealer\'s hand: {0}'.format(str(self.dealer)))
        await asyncio.sleep(1)
        await self.action_player()

    async def action_player(self):
        self.status = Status.ACTION
        # loop through players
        for i in range(len(self.active)):
            self.current_player = i
            # loop through player's hands (normally only 1)
            player = self.active[self.current_player]
            self.current_hand = 0
            self.num_actions = 0
            past_hand = self.current_hand
            while self.current_hand >= len(player.hands):
                # if hand the same then increment action otherwise reset action
                if self.current_hand == past_hand:
                    self.num_actions += 1
                else:
                    self.num_actions = 0

                await self.action_hand(player)
                await asyncio.sleep(1)

        await self.action_dealer()

    async def action_hand(self, player):
        # reset action flag to false
        self.action_input.clear()
        # player only has one hand?
        if len(player.hands) == 1:
            # player's first move?
            if self.num_actions == 1:
                await self.channel.send(
                    '@{0}\'s turn (${1}), are you staying, hitting or surrendering?'.format(player.display_name,
                                                                                            player.hands[
                                                                                                self.current_hand].bet))
                # can this hand split?
                if player.hands[self.current_hand].can_split():
                    await self.channel.send('**OR SPLITTING HAND**')
                # can player place an insurance bet?
                if self.dealer.cards[1].number == 'A' and player.insurance_bet == 0:
                    await self.channel.send('**OR PLACING INSURANCE BET**')
            else:
                await self.channel.send(
                    '@{0}\'s turn (${1}), are you staying, hitting?'.format(player.display_name,
                                                                            player.hands[self.current_hand].bet))
        else:
            await self.channel.send(
                '@{0}\'s turn for **Hand #{1}** (${2}), are you staying, hitting?'.format(player.display_name,
                                                                                          self.current_hand,
                                                                                          player.hands[
                                                                                              self.current_hand].bet))

        await self.action_input.wait()

    async def hit(self, player: Player):
        # Add card to current hand from deck
        player.hands[self.current_hand].cards.append(self.deck.cards[0])
        self.deck.remove_card()

        if len(player.hands) == 1:
            await self.channel.send(
                '@{0}\'s hand (${1}): {2}'.format(player.display_name, player.hands[self.current_hand].bet,
                                                  str(player.hands[self.current_hand])))
        else:
            await self.channel.send(
                '@{0}\'s **hand #{1}** (${2}): {3}'.format(player.display_name, self.current_hand,
                                                           player.hands[self.current_hand].bet,
                                                           str(player.hands[self.current_hand])))

        await asyncio.sleep(1)
        # Is this hand over 21?
        if player.hands[self.current_hand].sum() > 21:
            player.change_balance(-1 * player.hands[self.current_hand].bet)
            if len(player.hands) == 1:
                await self.channel.send('@{0}\'s hand is ***BUST*** and LOST ${1}!**'.format(player.display_name,
                                                                                             player.hands[
                                                                                                 self.current_hand].bet))
            else:
                await self.channel.send(
                    '@{0}\'s **hand #{1}** is **BUST** and LOST ${2}!**'.format(player.display_name, self.current_hand,
                                                                                player.hands[self.current_hand].bet))
            # automatic hand loss
            player.hands.pop(self.current_hand)
        self.action_input.set()

    async def split(self, player: Player):
        hand = player.hands[self.current_hand]
        # can this hand split?
        if len(player.hands) == 1 and hand.can_split() and self.num_actions == 1:
            # Add new hand with the first card and initial bet from the current hand
            split_hand = Hand(player.hands[self.current_hand].bet)
            split_hand.cards.append(player.hands.card[0])
            # Position new hand at current hand index
            player.hands.insert(self.current_hand, split_hand)
            # remove the first card from the current hand
            hand.cards.pop(0)

            await self.channel.send(
                '@{0} has **SPLIT** his hand! Initial bet doubled and split between the two hands! Your hands are now:'.format(
                    player.display_name, self.current_hand))
            for i in range(len(player.hands)):
                await self.channel.send(
                    '@{0}\'s **Hand #{1}** (${2}): {3}'.format(player.display_name, i, player.hands[i].bet,
                                                               str(player.hands[i])))
            self.action_input.set()

    async def insurance(self, player: Player, amount: int):
        if self.dealer.cards[1].number == 'A' and self.num_actions == 1 and player.insurance_bet == 0:
            player.insurance_bet = amount
            self.action_input.set()

    async def stand(self):
        self.current_hand += 1
        self.action_input.set()

    async def surrender(self, player: Player):
        if self.num_actions == 1:
            player.change_balance(-1 * player.hands[self.current_hand].bet)
            await self.channel.send('@{0} **FORFEITED** and **LOST ${1}!**'.format(player.display_name,
                                                                                   player.hands[self.current_hand].bet))
            player.hands.pop(self.current_hand)
            self.action_input.set()

    async def action_dealer(self):
        self.status = Status.END
        await asyncio.sleep(1)
        await self.channel.send('All players have finished their turn, dealer\'s turn:')
        # unhide dealer's first card
        self.dealer.cards[0].hidden = False
        await self.channel.send('dealer\'s hand: {0}'.format(str(self.dealer)))
        # dealer will hit when card sum is less than 17
        while self.dealer.sum() < 17:
            self.dealer.cards.append(self.deck.cards[0])
            self.deck.remove_card()
            await asyncio.sleep(1)
            await self.channel.send('dealer\'s hand: {0}'.format(str(self.dealer)))
        await asyncio.sleep(1)

        if self.dealer.sum() > 21:
            await self.channel.send('dealer\'s hand is **BUST!**')
            for player in self.active:
                if len(player.hands) > 0:
                    hands_sum = 0
                    # All remaining (non-bust) hands win
                    for hand in player.hands:
                        hands_sum += hand.bet * 2
                        player.hands.remove(hand)
                    player.change_balance(hands_sum)
                    await self.channel.send('**@{0} WON ${1}!**'.format(player.display_name, hands_sum))
                    await asyncio.sleep(1)
        else:
            if self.dealer.sum() == 21:
                await self.channel.send('dealer\'s hand is **BLACKJACK!**')
                await asyncio.sleep(1)

            for player in self.active:
                if len(player.hands) > 0:
                    for hand in player.hands:
                        hands_sum = 0
                        # Hands with same sum as dealer will push
                        if hand.sum() == self.dealer.sum():
                            hands_sum -= hand.bet
                        # Hands with higher sum will win (busted hands already removed out of hands list)
                        if hand.sum() > self.dealer.sum():
                            hands_sum += hand.bet * 2
                        player.change_balance(hands_sum)
                        if hands_sum > 0:
                            await self.channel.send('**@{0} WON ${1}!**'.format(player.display_name, hands_sum))
                        elif hands_sum <= 0:
                            await self.channel.send('**@{0} LOST ${1}!**'.format(player.display_name, hands_sum))
                        player.hands.remove(hand)
                        await asyncio.sleep(1)

                # Check whether insurance bet exists and is successful or not
                if player.insurance_bet > 0:
                    if self.dealer.sum() == 21:
                        player.change_balance(player.insurance_bet * 2)
                        await self.channel.send(
                            'AND **WON ${1}** from the **INSURANCE BET** as the dealer has blackjack!'.format(
                                player.display_name, player.insurance_bet * 2))
                    else:
                        player.change_balance(-1 * player.insurance_bet)
                        await self.channel.send(
                            'AND **LOST ${1}** from the **INSURANCE BET** as the dealer didn\'t reach blackjack!'.format(
                                player.display_name, player.insurance_bet))
                    player.insurance_bet = 0
                    await asyncio.sleep(1)
        # reset blackjack
        self.dealer = Hand(0)
        self.status = Status.START
        await self.channel.send('@here, new round of **BLACKJACK** begins in 5 seconds!')
        await asyncio.sleep(2)
        await self.start()
