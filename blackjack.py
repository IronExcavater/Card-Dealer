import time
from enum import Enum
from bot import bot
from deck import Deck
from player import Player


class Status(Enum):
    START = 1
    BET = 2


class Blackjack:
    def __init__(self, channel: int, player: Player):
        self.channel = channel
        self.active = [player]
        self.queue = []
        self.deck = Deck()
        self.status = Status.START
        time.sleep(7)
        bot.send_message(self.channel, '3... 2... 1...')
        time.sleep(3)
        self.start()  # TODO: make it time-based with timer of 10 seconds

    def start(self):
        bot.send_message(self.channel, 'Place initial bets!')
        self.active.extend(self.queue)
        self.queue.clear()
        self.deck.reset()
        time.sleep(7)
        bot.send_message(self.channel, '3... 2... 1...')
        time.sleep(3)
