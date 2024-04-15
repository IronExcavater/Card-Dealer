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
        # reset game (for when looping)
        self.status = Status.START
        self.dealer = Hand(0)
        self.active.extend(self.queue)
        self.queue.clear()
        self.deck.reset_deck()
        # reset players (for when looping and when new players join)
        for player in self.active:
            player.hands.clear()
            player.hands.append(Hand(0))
            player.blackjack_extras['insurance'] = 0
            player.blackjack_extras['even'] = False
        await self.channel.send('3... 2... 1...')
        await asyncio.sleep(3)
        await self.bet()

    async def bet(self):
        self.status = Status.BET
        await self.channel.send('Place initial bets!')
        await asyncio.sleep(6)
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
        await asyncio.sleep(1)
        await self.deal()

    async def deal(self):
        self.status = Status.DEAL
        # Remove any player that didn't place a bet
        for player in self.active:
            if player.hands[0].bet == 0:
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
                    print("It got up to here")
                    hand.cards.append(self.deck.cards[0])
                    self.deck.remove_card()
            # Automatically hide dealer's cards
            self.deck.cards[0].hidden = True
            self.dealer.cards.append(self.deck.cards[0])
            self.deck.remove_card()

        for player in self.active:
            await self.channel.send(
                '@{0}\'s hand (${1}): {2}'.format(player.display_name, player.hands[self.current_hand].bet,
                                                  str(player.hands[0])))
            await asyncio.sleep(2)

        # Show dealer's second card
        self.dealer.cards[1].hidden = False
        await self.channel.send('dealer\'s hand: {0}'.format(str(self.dealer)))
        await asyncio.sleep(2)
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
            while self.current_hand < len(player.hands):
                # if hand the same then increment action otherwise reset action
                if self.current_hand == past_hand:
                    self.num_actions += 1
                else:
                    self.num_actions = 0

                await self.action_hand(player)
                await asyncio.sleep(1)

        # Check if an remaining active players
        for player in self.active:
            if len(player.hands) > 0:
                await self.action_dealer()
            else:
                await self.channel.send('No players with playable hands left! **DEALER WINS**!')
                await self.loop()

    async def action_hand(self, player):
        # reset action flag to false
        self.action_input.clear()

        # player only has one hand?
        if len(player.hands) == 1:
            await self.channel.send(
                '@{0}\'s turn (${1}), are you staying, hitting?'.format(player.display_name, player.hands[self.current_hand].bet))
            # player's first move?
            if self.num_actions == 1:
                await asyncio.sleep(0.5)
                await self.channel.send('  -  or surrendering?')
            # can this hand split?
            if player.hands[self.current_hand].can_split():
                await asyncio.sleep(0.5)
                await self.channel.send('  -  or splitting hand?')
            # can player place an insurance bet?
            if self.dealer.cards[1].number == 'A' and player.blackjack_extras['insurance'] == 0:
                await asyncio.sleep(0.5)
                await self.channel.send('  -  or placing an insurance bet?')
            # can player call even with natural hand?
            if player.hands[self.current_hand].sum() == 21 and self.dealer.cards[1].number == 'A':
                await asyncio.sleep(0.5)
                await self.channel.send('  -  or calling even?')
        else:
            await self.channel.send(
                '@{0}\'s turn for **Hand #{1}** (${2}), are you staying, hitting?'.format(player.display_name,
                                                                                          self.current_hand,
                                                                                          player.hands[
                                                                                              self.current_hand].bet))
        # can this hand bet be doubled?
        if len(player.hands[self.current_hand].cards) == 2 and not player.hands[self.current_hand].doubled:
            await asyncio.sleep(0.5)
            await self.channel.send('  -  or doubling initial bet?')

        await self.action_input.wait()

    async def hit(self, player: Player):
        # If player previously doubled or split, the max number of cards per hand is 3
        if len(player.hands[self.current_hand].cards) > 3 and (player.hands[self.current_hand].doubled or len(player.hands[self.current_hand]) > 1):
            return
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

        await asyncio.sleep(2)
        # Is this hand over 21?
        if player.hands[self.current_hand].sum() > 21:
            player.change_balance(-1 * player.hands[self.current_hand].bet)
            print('bust')
            if len(player.hands) == 1:
                await self.channel.send('@{0}\'s hand is **BUST and LOST ${1}!**'.format(player.display_name, player.hands[self.current_hand].bet))
            else:
                await self.channel.send(
                    '@{0}\'s **hand #{1}** is **BUST** and LOST ${2}!**'.format(player.display_name, self.current_hand,
                                                                                player.hands[self.current_hand].bet))
            # automatic hand loss
            player.change_games(False)
            player.hands.pop(self.current_hand)
            self.action_input.set()
            return

        if len(player.hands[self.current_hand].cards) == 5:
            # automatic hand win due to Five Card Charlie
            print('five cards')
            if len(player.hands) == 1:
                await self.channel.send(
                    '@{0}\'s hand reached **FIVE CARD CHARLIE**, automatically winning if dealer doesn\'t reach blackjack.'.format(
                        player.display_name))
            else:
                await self.channel.send(
                    '@{0}\'s **hand #{1}** reached **FIVE CARD CHARLIE**, automatically winning if dealer doesn\'t reach blackjack.'.format(
                        player.display_name, self.current_hand))
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
            # Adding an extra card for each hand
            await self.channel.send('Dealing an extra card for both hands...')
            for i in range(len(player.hands)):
                player.hands[i].cards.append(self.deck.cards[0])
                self.deck.remove_card()
                await self.channel.send(
                    '@{0}\'s **Hand #{1}** (${2}): {3}'.format(player.display_name, i, player.hands[i].bet,
                                                               str(player.hands[i])))
            self.action_input.set()

    async def double(self, player: Player):
        # can this hand bet be doubled?
        if len(player.hands[self.current_hand].cards) == 2 and not player.hands[self.current_hand].doubled:
            player.hands[self.current_hand].bet *= 2
            if len(player.hands) == 1:
                await self.channel.send('@{0}\'s bet is **DOUBLED to ${1}!**'.format(player.display_name, player.hands[
                    self.current_hand].bet))
            else:
                await self.channel.send(
                    '@{0}\'s **hand #{1}** bet is **DOUBLED to ${2}!**'.format(player.display_name, self.current_hand,
                                                                               player.hands[self.current_hand].bet))
            player.hands[self.current_hand].doubled = True
            self.action_input.set()

    async def even(self, player: Player):
        # can player call even with natural hand?
        if self.num_actions == 1 and player.hands[self.current_hand].sum() == 21 and len(player.hands) == 1 and self.dealer.cards[1].number == 'A':
            player.blackjack_extras['even'] = True
            await self.channel.send('@{0}\'s has called **EVEN**'.format(player.display_name))
            self.current_hand += 1
            self.action_input.set()

    async def insurance(self, player: Player, amount: int):
        # can player place an insurance bet?
        if self.dealer.cards[1].number == 'A' and self.current_hand == 1 and self.num_actions == 1:
            if player.blackjack_extras['insurance'] != 0:
                await self.channel.send('You have already placed an insurance bet!')
            elif amount < 0:
                await self.channel.send('The minimum insurance bet is $1!')
            elif amount > player.hands[self.current_hand].bet:
                await self.channel.send(
                    'The maximum insurance bet is **HALF** of your initial bet (${0} ÷ 2 = ${1})'.format(
                        player.hands[self.current_hand].bet, player.hands[self.current_hand].bet / 2))
            else:
                player.blackjack_extras['insurance'] = amount
                await self.channel.send('@{0} has placed an **INSURANCE BET of ${1}**!'.format(player.display_name,
                                                                                               player.blackjack_extras[
                                                                                                   'insurance']))
                self.action_input.set()

    async def stand(self):
        self.current_hand += 1
        self.action_input.set()

    async def surrender(self, player: Player):
        if self.num_actions == 1:
            player.change_balance(-0.5 * player.hands[self.current_hand].bet)
            await self.channel.send('@{0} **FORFEITED** and **LOST ${1}!**'.format(player.display_name,
                                                                                   player.hands[self.current_hand].bet))
            player.change_games(False)
            player.hands.pop(self.current_hand)
            self.action_input.set()

    async def action_dealer(self):
        self.status = Status.END
        await asyncio.sleep(0.5)
        await self.channel.send('All players have finished their turn, dealer\'s turn:')
        await asyncio.sleep(1)
        # unhide dealer's first card
        self.dealer.cards[0].hidden = False
        await self.channel.send('dealer\'s hand: {0}'.format(str(self.dealer)))
        await asyncio.sleep(2)
        # dealer will hit when card sum is less than 17
        while self.dealer.sum() < 17:
            self.dealer.cards.append(self.deck.cards[0])
            self.deck.remove_card()
            await self.channel.send('dealer\'s hand: {0}'.format(str(self.dealer)))
            await asyncio.sleep(2)

        await asyncio.sleep(5)

        if self.dealer.sum() > 21:
            await self.channel.send('dealer\'s hand is **BUST!**')
            await asyncio.sleep(3)
            for player in self.active:
                if len(player.hands) > 0:
                    hands_sum = 0
                    # All remaining (non-bust) hands win
                    for hand in player.hands:
                        if hand.sum() == 21:
                            hands_sum += hand.bet * 2.5
                        else:
                            hands_sum += hand.bet * 2
                        player.hands.remove(hand)
                    player.change_balance(hands_sum)
                    await self.channel.send('**@{0} WON ${1}!**'.format(player.display_name, hands_sum))
                    player.change_games(True)
                    await asyncio.sleep(2)
        else:
            if self.dealer.sum() == 21:
                await self.channel.send('dealer\'s hand is **BLACKJACK!**')
                await asyncio.sleep(2)

            for player in self.active:
                if len(player.hands) > 0:
                    hands_sum = 0
                    for hand in player.hands:
                        # break even with 'even' rule
                        if not player.blackjack_extras['even']:
                            # Five Card Charlie rule
                            if len(hand.cards) > 4 and self.dealer.sum() != 21:
                                hands_sum += hand.bet
                            else:
                                # Hands with higher sum will win (busted hands already removed out of hands list)
                                if hand.sum() > self.dealer.sum():
                                    if hand.sum() == 21:
                                        hands_sum += hand.bet * 1.5
                                    else:
                                        hands_sum += hand.bet
                                elif hand.sum() < self.dealer.sum():
                                    hands_sum -= hand.bet
                        player.hands.remove(hand)

                    player.change_balance(hands_sum)
                    if hands_sum > 0:
                        await self.channel.send('**@{0} WON ${1}!**'.format(player.display_name, hands_sum))
                        player.change_games(True)
                    elif hands_sum < 0:
                        await self.channel.send('**@{0} LOST ${1}!**'.format(player.display_name, hands_sum))
                        player.change_games(False)
                    else:
                        await self.channel.send('**@{0} BROKE EVEN!**'.format(player.display_name, hands_sum))
                        player.change_games(False)
                    await asyncio.sleep(1)

                # Check whether insurance bet exists and is successful or not
                if player.blackjack_extras['insurance'] > 0:
                    if self.dealer.sum() == 21:
                        player.change_balance(player.blackjack_extras['insurance'] * 3)
                        await self.channel.send(
                            'AND **WON ${1}** from the **INSURANCE BET** as the dealer has blackjack!'.format(
                                player.display_name, player.blackjack_extras['insurance'] * 3))
                    else:
                        player.change_balance(-1 * player.blackjack_extras['insurance'])
                        await self.channel.send(
                            'AND **LOST ${1}** from the **INSURANCE BET** as the dealer didn\'t reach blackjack!'.format(
                                player.display_name, player.blackjack_extras['insurance']))
                    await asyncio.sleep(2)
        await self.loop()

    async def loop(self):
        # loop blackjack
        await asyncio.sleep(2)
        await self.channel.send('@here, new round of **BLACKJACK** begins in 5 seconds!')
        await asyncio.sleep(3)
        await self.start()
