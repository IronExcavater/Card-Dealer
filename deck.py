from enum import Enum
import random


class Number(Enum):
    N2 = 2
    N3 = 3
    N4 = 4
    N5 = 5
    N6 = 6
    N7 = 7
    N8 = 8
    N9 = 9
    N10 = 10
    JACK = 'J'
    QUEEN = 'Q'
    KING = 'K'
    ACE = 'A'

    def __str__(self):
        return self.value


class Suit(Enum):
    SPADES = '♠'
    HEARTS = '♥'
    DIAMONDS = '♦'
    CLUBS = '♣'

    def __str__(self):
        return self.value


class Card:
    def __init__(self, number, suit):
        self.number = number
        self.suit = suit
        if isinstance(self.number.value, int):
            self.value = self.number.value
        else:
            match self.number:
                case Number.JACK | Number.QUEEN | Number.KING:
                    self.value = 10
                case Number.ACE:
                    self.value = 11
        self.hidden = False

    def __str__(self):
        if self.hidden:
            return '░░'
        else:
            return '{0} {1}'.format(self.suit.value, self.number.value)


class Hand:
    def __init__(self, bet: int):
        self.cards = []
        self.bet = bet
        self.doubled = False

    def __str__(self):
        string = '  '
        for card in self.cards:
            string += str(card) + '     '
        return string

    def sum(self) -> int:
        hand_sum = 0
        for card in self.cards:
            hand_sum += card.value
        if hand_sum > 21:
            # Check for soft aces (value 11), changing their value to hard aces (1)
            for card in self.cards:
                if card.value == 11:
                    card.value = 1
                    hand_sum -= 10
                    if hand_sum <= 21:
                        break
        return hand_sum

    def can_split(self) -> bool:
        # A hand can be split when it only has two cards of the same number
        if len(self.cards) == 2 and self.cards[0].number == self.cards[1].number:
            return True
        return False


class Deck:
    def __init__(self):
        self.cards = []

    def __str__(self):
        return str(self.cards)

    def remove_card(self):
        self.cards.pop(0)
        # if deck has less than 14, add new deck of cards
        if len(self.cards) < 14:
            self.cards.extend([Card(number, suit) for number in Number for suit in Suit])
            random.shuffle(self.cards)

    def reset_deck(self):
        # reset the cards in the deck and shuffle
        self.cards = [Card(number, suit) for number in Number for suit in Suit]
        random.shuffle(self.cards)
