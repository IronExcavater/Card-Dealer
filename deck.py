from enum import Enum
import random


class Number(Enum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 'J'
    QUEEN = 'Q'
    KING = 'K'
    ACE = 'A'

    def __str__(self):
        return self.value


class Suit(Enum):
    SPADES = 'Spades'
    CLUBS = 'Clubs'
    HEARTS = 'Hearts'
    DIAMONDS = 'Diamonds'

    def __str__(self):
        return self.value


class Card:
    def __init__(self, number, suit):
        self.number = number
        self.suit = suit

    def __str__(self):
        return '{} {}'.format(self.suit, self.number)


class Deck:
    def __init__(self):
        self.cards = []

    def __str__(self):
        return str(self.cards)

    def reset(self):
        self.cards = [Card(number, suit) for number in Number for suit in Suit]
        random.shuffle(self.cards)
