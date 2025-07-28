import random
import json
import argparse
from time import sleep
from pydantic import BaseModel

from display import make_screen
from blmp import *
from log import log_message, log_start, log_end

'''
Game state contains the public state of the game. 
It is used to display the game state on the screen and to provide context for the players.
It should not contain any private information about the players, such as their cards or their mind.
'''
global GAME_STATE
GAME_STATE = ""

Language = "a"  # Default language is English
LangName = "English"  # Default language name is English

def update_game_state(msg):
    global GAME_STATE
    GAME_STATE += msg + "\n"
    log_message(msg) 

Announcer_voice = "am_eric"  # Default announcer voice

BLUFF_MIND_RULES = """
Bluff Mind is a card game.
The game uses 20 playing cards, consisting of 6 Queens (Q), 6 Kings (K), 6 Aces 
(A), and 2 Jokers (J). Jokers can be used as any card, functioning as wild cards.

The game is played by 4 players and proceeds in rounds. In each round, every 
player is dealt 5 cards, and one of the three card types (Q, K, or A) is 
randomly selected as the "table card".

The players sit around a table and take turns in clockwise order, starting with 
a random person. On their turn, a player can choose to either challenge or play cards. 
If the player chooses to play cards, they can play 1 to 3 cards from their hand, 
claiming they are all the "table card" (they may bluff). 
If the player chooses to challenge, the previous 
player must reveal the cards they played. If the previous player played at least 
one card that is not the table card, the challenge succeeds, and the previous 
player loses and must play Russian Roulette. If the previous player played only 
cards that are the table card or a Joker, the challenge fails, and the challenger 
loses and must play Russian Roulette. A player must challenge if they have no 
cards left in their hand.

Russian Roulette rules are as follows:
Each player has a revolver with 3 chambers. At the start of the game, one bullet 
is randomly loaded into one of the chambers. Each time a player fires the 
revolver, the chamber advances by one position. The chamber does not advance if 
the revolver is not fired.

After a player chooses to challenge, the round ends. All surviving players 
proceed to the next round. At the start of a new round, all previous cards are 
discarded, each player is dealt a new hand of 5 cards, a new table card is 
selected, and the players are reseated in a random order. The chambers of all 
revolvers stay in their current position.

The game ends when only one player remains alive. 
"""

BLUFF_MIND_PROMPT = """
Play the game of Bluff Mind as if you are in the game. You must follow the 
system instructions and the rules of the game.
"""

AGG_LEVEL_EXPLANATION = """
The number represents how likely you are to challenge or bluff. 
0 means you should never challenge the last player nor bluff.
99 means you should always challenge the last player or bluff.
"""

class PlayerResponse(BaseModel):
    reason: str
    move: str
    played_cards: list[str]
    taunt: str

class Player:
    def __init__(self, name, model, persona, voice, aggro=50):
        self.name = name
        self.model = model
        self.persona = "You are " + name + ". " + persona + "You have an aggression level of " + str(aggro) + ". " 
        self.voice = voice
        self.model_messages = [system_message(BLUFF_MIND_RULES + self.persona + AGG_LEVEL_EXPLANATION + BLUFF_MIND_PROMPT)]
        self.aggro = aggro
        self.dead_round = 0 # The round in which the player was killed
        self.cards = []
        self.last_played_cards = []
        self.rr_position = None
        self.rr_played = 0
        self.alive = True

        self.in_play = False

        self.mind = ""
        self.taunt = ""

    def __str__(self):
        return f"{self.name}"
    
    def reset_rr(self):
        self.rr_position = random.randint(1, 3)  # position in the Russian Roulette
        self.rr_played = 0

    def shoot_rr(self):
        """
        Simulate a Russian Roulette shot.
        Returns True if the player survives, False if the player is killed.
        """
        # return False # auto force death on challenge for fast testing
        log_message(f"{self} is taking a shot in RR, position: {self.rr_position}, played: {self.rr_played}")
        self.rr_played += 1
        if self.rr_played == self.rr_position:
            log_message(f"{self} has been killed in RR!")
            return False
        else:
            log_message(f"{self} has survived the RR shot!")
            return True
        

    def play_card(self, last_player, table_card):
        '''
        Return a list of cards played or an empty list if a challenge is issued
        '''

        #Move this log to LM????
        if len(self.cards) == 0:
            log_message(f"{self} has no cards left to play, therefore must challenge.")
            self.last_played_cards = []
            return [], "I have no cards left to play, therefore must challenge."

        if self.model == "Random":
            self.last_played_cards, self.taunt = self._play_card_random(last_player, table_card)
            return self.last_played_cards, self.taunt 
        else: 
            self.last_played_cards, self.taunt = self._play_card_llm(last_player, table_card)
            return self.last_played_cards, self.taunt
        

    def _play_card_llm(self, last_player, table_card):

        self.mind = ""
        
        prompt = (
            "This is the current state of the game you are in:\n"
            + GAME_STATE + "\n"
            + "Your cards are: " + str(self.cards) + "\n"
            + "Think about your next move and give the reason for your decision."
            + "What is your move? Please challenge or play 1 to 3 cards from your hand.\n"
        )

        if last_player is not None:
            prompt += f"The last player was {last_player}. You can choose to challenge them. Do you want to challenge them? If so, do not play any cards, and provide a reason for your challenge.\n"
        else:
            prompt += "There is no last player, so you cannot challenge anyone.\n"
        
        if self.model.api_type == APIType.OPENROUTER:
            response_format = {
                "type": "json_schema",
                "json_schema":{
                    "name": "turn",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": f"The reason for playing the selected cards or challenging, in {LangName}."
                            },
                            "move": {
                                "type": "string",
                                "enum": ["CHALLENGE", "PLAY"],
                                "description": "The move to make. Either 'CHALLENGE' or 'PLAY'. If 'CHALLENGE', the player is challenging the last player. If 'PLAY', the player is playing cards."
                            },
                            "played_cards": {
                                "type": "array", 
                                "items": {"type": "string"},
                                "description": "List of cards to be played by the player. Must be a subset of the player's hand. List must be empty if the player chooses to challenge. Cards must be in format of 'Q', 'K', 'A', or 'Joker'." 
                            },
                            "taunt": {
                                "type": "string",
                                "description": f"Optional taunt or comment in {LangName} to say to the other players."
                            }
                        },
                        "required": ["move", "played_cards", "reason", "taunt"]
                    }
                }
            }
        elif self.model.api_type == APIType.OLLAMA:
            response_format = PlayerResponse.model_json_schema()

        code, llm_move = self.model.complete_chat(self.model_messages + [user_message(prompt)], response_format=response_format)

        if code == 0:
            try:
                llm_move = json.loads(llm_move)
            except Exception as e:
                print("-- ERROR --")
                print("Error parsing LLM response as JSON:", e)
                print("LLM response:")
                print(llm_move)
                buffer = input("Check LLM error. Press Enter to continue...")
                return self._play_card_llm(last_player, table_card)

            played_cards = [] if llm_move["move"] == "CHALLENGE" else llm_move["played_cards"]
            reason = llm_move["reason"]
            taunt = llm_move["taunt"]
        
            self.mind = reason
            
            msg = f"{self} has performed {llm_move['move']} and played cards: {played_cards} with hand {self.cards}\n\n Reason: \n{reason}\n"
            log_message(msg)


            counts = {card: self.cards.count(card) for card in self.cards}
            for card in played_cards:
                if counts.get(card, 0) < 1:
                    print(f"-- ERROR --")
                    print(f"{self} attempted to play {played_cards} with hand {self.cards}.")
                    buffer = input("Check LLM error. Press Enter to continue...")
                    return self._play_card_llm(last_player, table_card)
                counts[card] -= 1
                
            if llm_move["move"] == "CHALLENGE":
                if len(played_cards) != 0:
                    print(f"-- ERROR --")
                    print(f"{self} attempted to challenge with played cards: {played_cards}.")
                    buffer = input("Check LLM error. Press Enter to continue...")
                    return self._play_card_llm(last_player, table_card)
                if (last_player is None):
                    print(f"-- ERROR --")
                    print(f"{self} attempted to challenge without a last player.")
                    buffer = input("Check LLM error. Press Enter to continue...")
                    return self._play_card_llm(last_player, table_card)
                else:
                    log_message(f"{self} has chosen to challenge {last_player}.")
                    if Language == "a":
                        taunt = f"I challenge {last_player}."
                    else:
                        taunt += f"我要挑战{last_player}."
            else:
                if Language == "a":
                    taunt += f" {len(played_cards)} {table_card}!" 
                else:
                    taunt += f" {len(played_cards)} 张!" 

            if taunt != "":
                update_game_state(f"{self} says: {taunt}")

            for card in played_cards:
                self.cards.remove(card)

            log_message(f"{self} has played card: {played_cards}, remaining cards: {self.cards}")

            self.last_played_cards = played_cards
            return played_cards, taunt
        else:
            print("-- ERROR --")
            print(f"LLM Error, Code {code}:")
            print(llm_move['message'])
            if metadata := llm_move.get("metadata", None):
                print("Error Metadata:")
                print(metadata)
            print("Check LLM error. Quitting.")
            exit() 
        
    def _play_card_random(self, last_player, table_card):
        sleep(1)
        if (last_player is not None) and (random.random() < (self.aggro / 100)):
            log_message(f"{self} has chosen to challenge {last_player}.")
            self.last_played_cards = []
            return [], "I challenge the last player."
        
        number_of_cards = len(self.cards)
        # Randomly pick a few cards (1 to number_of_cards)
        npick = random.randint(1, min(3, min(3, number_of_cards)))
        picked_cards = []
        while npick > 0:
            # Randomly pick a card from the hand
            card_index = random.randint(0, len(self.cards) - 1)
            picked_cards.append(self.cards[card_index])
            del self.cards[card_index]  # remove the card from hand
            npick -= 1

        log_message(f"{self} has played card: {picked_cards}, remaining cards: {self.cards}")
        self.last_played_cards = picked_cards
        return picked_cards, f"{len(picked_cards)} {table_card}"

class BaseGame:
    def __init__(self, players, show_context=None):
        self.all_players = players
        self.state = "initial"
        self.table_card = None
        self.show_context = show_context

        self.round_number = 0
        self.players_in_round = []
        self.screen_message = "To challenge or not, that is the question."
        self.screen_message_type = "info" # info, play, challenge, survived, killed 

        self.agent_mode = False
        
        if show_context is not None:
            from tts import VoiceTTS 
            self._tts = VoiceTTS(lang=Language)
        else:
            self._tts = None

    def start_game(self):
        update_game_state(f"Game started with state: {self.state}")
        self.state = "running"
        random.seed()

        for player in self.all_players:
            if Language == "a":
                msg = f"{player.name} has joined the game."
            else:
                msg = f"{player.name} 来了"
            self.voice_say(player.voice, msg, speed=1.0)
            self.players_in_round.append(player)
            self.show_message(msg, voice=False)
            log_message(msg)

        # reset RR for all players
        for player in self.all_players:
            player.reset_rr()

    def round_order(self):
        """
        Return the order of players for the current round.
        This is a random order of all alive players.
        """
        alive_players = [p for p in self.all_players if p.alive]
        random.shuffle(alive_players)
        self.players_in_round = alive_players
        return
    
    def voice_say(self, voice, msg, speed=1.0):
        """
        Say a message using the TTS system.
        """
        if self._tts is not None:
            self._tts.voice_say(voice, msg, speed)

    def wait_say(self):
        """
        Wait for the TTS system to finish speaking.
        """
        if self._tts is not None:
            self._tts.wait()

    def update_screen(self):
        """
        Update the screen with the current game state.
        """
        if self.show_context is not None:
            self.show_context.update(make_screen(self, self.agent_mode, lang=Language), refresh=True)

    def show_message(self, msg, wait=True, msg_type="info", voice=True):
        """
        Update the screen message.
        """
        if self.show_context is None:
            return 
        self.screen_message = msg
        self.screen_message_type = msg_type
        self.wait_say()
        self.update_screen()
        if voice:
            self.voice_say(Announcer_voice, msg, speed=1.0)

    def shuffle_cards(self):
        deck = ['Joker'] * 2 + ['Q'] * 6 + ['K'] * 6 + ['A'] * 6 
        random.shuffle(deck)
        # each player gets 5 cards
        i = 0
        for player in self.all_players:
            if player.alive:
                # make a deep copy. [:] is a shallow copy
                # player.cards will be modified during play. 
                player.cards = deck[i:i + 5].copy() 
                # sort the cards for better readability
                player.cards.sort()
                player.last_played_cards = []
                i += 5
                log_message(f"{player} has been dealt cards: {player.cards}")
    
    def check_cards(self, cards):
        """
        Check if all the cards are the self.table_card, 
        If so, return True, otherwise return False.
        """
        check = all((card == self.table_card or card == 'Joker') for card in cards)
        if check:
            if Language == "a":
                msg = "Challenge failed! All cards match the table card." 
            else:
                msg = "挑战失败！所有的牌都匹配桌面牌。"
        else:
            if Language == "a":
                msg = "Challenge successful! Not all cards match the table card."
            else:
                msg = "挑战成功！不是所有的牌都匹配桌面牌。"
        update_game_state(msg)
        self.show_message(msg, msg_type="challenge")
        return check

    def russian_roulette(self, player):
        '''
        Play Russian Roulette with the given player.
        Return True if the player is killed, False if the player survives.
        '''
        if Language == "a":
            msg = f"{player} will now play Russian Roulette!"
        else:
            msg = f"{player} 朝自己开了一枪！"
        update_game_state(msg)
        self.show_message(msg, msg_type="rr")

        if player.shoot_rr() is False:
            if Language == "a":
                msg = f"{player} was killed!"
            else:
                msg = f"{player} 完蛋了!"
            update_game_state(msg)
            self.show_message(msg, msg_type="killed")
            player.alive = False
            player.dead_round = self.round_number
            return True
        else:
            if Language == "a":
                msg = f"{player} survived!"
            else:
                msg = f"{player} 逃过了!"
            update_game_state(msg)
            self.show_message(msg, msg_type="survived")
            return False 
        

    def report(self):
        log_message("Game report:")
        for player in self.all_players:
            if player.alive:
                if Language == "a":
                    msg = f"{player.name} wins the game."
                else:
                    msg = f"{player.name} 赢了游戏."
                self.show_message(msg)
                update_game_state(msg)
                self.wait_say()
            else:
                log_message(f"{player} has been killed.")

class GameProg(BaseGame):
    def __init__(self, players, show_context=None):
        super().__init__(players, show_context=show_context)

    def play(self):
        self.start_game()

        total_players = len(self.all_players)
        while total_players > 1:
            if self.play_a_round() is not None:
                total_players -= 1
        self.state = "finished"

    def play_a_round(self):
        '''
        return the killed player if any, otherwise None
        '''

        for player in self.all_players:
            player.mind = ""  # Reset mind for each player
            player.taunt = ""  # Reset taunt for each player
            
        self.round_order()  # Determine the order of players for the round
        players = self.players_in_round

        self.round_number += 1

        global GAME_STATE 
        GAME_STATE = ""  # Reset game state for the new round
        players_str = ', '.join([f"{player}({player.rr_played})" for player in players])
        update_game_state(f"Playing round {self.round_number} with {len(players)} players. Player order will be: {players_str}")
        update_game_state("The number next to each player is the number of times they have played Russian Roulette (RR) so far.")

        # Shuffle the cards
        self.shuffle_cards()
        
        # Randomly select a live player to start
        # Since the players is randomly shuffled in each round, we can just take the first one
        number_of_all_players = len(players)
        start = 0
        msg = f"{players[start]} will start the game."
        log_message(msg)

        # Determine the table card
        self.table_card = random.choice(['Q', 'K', 'A'])
        msg = f"The table card is: {self.table_card}"
        update_game_state(msg)

        if Language == "a":
            msg = f"Starting round {self.round_number} with table card {self.table_card}"
        else:
            msg = f"开始第{self.round_number}轮"
        self.show_message(msg)
        
        # Play until a challenge is issued
        last_player = None
        last_played_cards = None
        killed = None
        while True:
            player = players[start]
            player.in_play = True
            if Language == "a":
                msg = f"{player}'s turn..."
            else:
                msg = f"轮到{player}出牌了..."
            self.show_message(msg)
            log_message(msg)

            cards_played, taunt = player.play_card(last_player, self.table_card)
            self.update_screen()
            if taunt != "":
                self.voice_say(player.voice, taunt, speed=1.0)
            if len(cards_played) == 0 : # challenge issued
                assert last_player is not None, "Challenge issued without a last player."
                if Language == "a":
                    msg = f"{player} challenges {last_player}!"
                else:
                    msg = f"{player} 挑战 {last_player}!"
                update_game_state(msg)
                self.show_message(msg, msg_type="challenge")

                if self.check_cards(last_played_cards):
                    rr_shooter = player
                else:
                    rr_shooter = last_player

                self.russian_roulette(rr_shooter)
                
                player.in_play = False

                break

            if Language == "a":
                msg = f"{player} has played {len(cards_played)} card" + ("s." if len(cards_played) > 1 else ".") 
            else:
                msg = f"{player} 出了 {len(cards_played)} 张牌"
            update_game_state(msg)
            self.show_message(msg, msg_type="play", voice=False)

            player.in_play = False
            
            last_player = player
            last_played_cards = cards_played
            start = (start + 1) % number_of_all_players

        return killed

AGENT_PROMPT = """
You are a game agent for game of BluffMind with a given N number of players. 
Track players by their respective index from 0 to N-1. Start the game by first 
calling the tool 'start_game' to initialize the game state. Then, use the 'prompt_round_order'
tool to determine a player order for the round, which will not include any dead 
players. If there is only one player left alive, return only "GAME OVER: 
<winner_name> won!", which ends the game. Then, shuffle and deal the cards to
the players using the 'start_round' tool, which you should also pass in the
player order. Finally, you will help players play their turns in the order 
determined by prompting them to perform their turn using the 'prompt_player_turn' 
tool, which takes two arguments. The first is the index of the player you are 
prompting to take their turn, and the second is the index of the last player who 
just played a turn, which should be 'None' if the turn is the first player. The 
tool will then return the cards the player chooses to play. A player issues a 
challenge to the last player when they play 0 or 'None' cards. If a player 
issues a challenge, use the 'prompt_check_cards' tool, which returns either True 
or  False. If 'prompt_check_cards' returns True, then the challenge fails and 
the player who issued the challenge must play Russian Roulette (RR). If 
'prompt_check_cards' returns False, the challenge succeeds and the last player 
must play RR. You will then prompt the respective player to play RR using the 
'prompt_russian_roulette' tool. After a player is killed in RR, they are removed 
from the game. A round only ends after a challenge is issued. Otherwise, players 
keep playing cards in their respective order, which should loop if needed. Keep 
track of who is alive and who is dead. After a challenge is issued and a player 
has played RR, start a new round by again, first determining the player order 
using the 'round_order' tool. Determine if there is a winner, if not, then 
continue the game by calling  the 'start_round' tool. You will not play the game 
yourself. All prompts should be done only through the tools provided. You may 
taunt all the players in the game as an announcer to keep the game lively. The 
message must be in {lang}. When doing so, return only a message with "COMMENT: 
<your taunt message in {lang}>", which will be broadcast to all players. In the 
message, refer to play 0 as {player0}, player 1 as {player1}, player 2 as 
{player2}, and player 3 as {player3}. Continue playing the game after taunting.
"""

class GameAgent(BaseGame):
    def __init__(self, players, show_context=None, agent_model="google/gemini-2.5-flash"):
        super().__init__(players, show_context=show_context)
        self.agent_mode = True
        
        self.agent = BLMPClient(model=agent_model)
        self.agent_messages = []

        self.dead_players = []
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "start_game",
                    "description": "Starts the game. This will reset the game state and prepare for a new round."
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "prompt_round_order",
                    "description": "Determines the order of players for the current round. Returns a list of players in the order they will play. Only includes players who are alive.",
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "start_round",
                    "description": "Starts a new round. Shuffles the deck of cards and re-deals them to players.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "players": {
                                "type": "array",
                                "items": {
                                    "type": "integer"
                                },
                                "description": "List of alive players in the current round."
                            }
                        },
                        "required": ["players"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "prompt_player_turn",
                    "description": "Prompts a player with index i to take their turn, accounting also for the last player's index.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "player_index": {
                                "type": "integer",
                                "description": "The index of the player taking their turn."
                            },
                            "last_player_index": {
                                "type": ["integer", "None"],
                                "description": "The index of the last player who played, or None if no last player."
                            }
                        },
                        "required": ["player_index", "last_player_index"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "prompt_check_cards",
                    "description": "Checks if all the cards played by a player match the table card. Used to determine if a challenge is successful.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cards": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "The list of cards played by the player."
                            }
                        },
                        "required": ["cards"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "prompt_russian_roulette",
                    "description": "Prompts a player with index i to play Russian Roulette (RR) after a challenge is issued.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "player_index": {
                                "type": "integer",
                                "description": "The index of the player who will play Russian Roulette."
                            }
                        },
                        "required": ["player_index"]
                    }
                }
            }
        ]
        self.TOOL_MAPPING = {
            "start_game": self.start_game,
            "prompt_round_order": self.prompt_round_order,
            "start_round": self.start_round,
            "prompt_player_turn": self.prompt_player_turn,
            "prompt_check_cards": self.prompt_check_cards,
            "prompt_russian_roulette": self.prompt_russian_roulette
        }

    def prompt_round_order(self):
        log_message("AGENT DETERMINING ROUND ORDER")
        self.round_order()
        return [self.all_players.index(p) for p in self.players_in_round]

    def start_round(self, players):
        log_message("AGENT STARTING NEW ROUND")
        
        for player in self.all_players:
            player.mind = ""  # Reset mind for each player
            player.taunt= ""  # Reset taunt for each player

        self.round_number += 1

        players = [self.all_players[i] for i in players]

        global GAME_STATE 
        GAME_STATE = ""  # Reset game state for the new round
        players_str = ', '.join([f"{player}({player.rr_played})" for player in players])
        update_game_state(f"Playing round {self.round_number} with {len(players)} players. Player order will be: {players_str}")
        update_game_state("The number next to each player is the number of times they have played Russian Roulette (RR) so far.")
        
        log_message("AGENT SHUFFLING CARDS")
        self.shuffle_cards()

        self.table_card = random.choice(['Q', 'K', 'A'])
        msg = f"The table card is: {self.table_card}"
        update_game_state(msg)

        if Language == "a":
            msg = f"Starting round {self.round_number} with table card {self.table_card}" 
        else:
            msg = f"开始第{self.round_number}轮"
        self.show_message(msg)

    def prompt_check_cards(self, cards):
        log_message("AGENT CHECKING CARDS IN CHALLENGE")
        return self.check_cards(cards)

    def prompt_player_turn(self, player_index, last_player_index):
        player = self.all_players[player_index]
        last_player = self.all_players[last_player_index] if last_player_index is not None else None
        log_message(f"AGENT PROMPTING {player} TURN, LAST PLAYER: {last_player}")
        player.in_play = True
        if Language == "a":
            msg = f"{player}'s turn..."
        else:
            msg = f"轮到{player}出牌了..."
        self.show_message(msg)
        log_message(msg)
        cards_played, taunt = player.play_card(last_player, self.table_card)
        self.update_screen()
        if taunt != "":
            self.voice_say(player.voice, taunt, speed=1.0)
        if len(cards_played) == 0 : # challenge issued
            assert last_player is not None, "Challenge issued without a last player."
            if Language == "a":
                msg = f"{player} challenges {last_player}!"
            else:
                msg = f"{player} 挑战 {last_player}!"
            update_game_state(msg)
            self.show_message(msg, msg_type="challenge")
        else:
            if Language == "a":
                msg = f"{player} has played {len(cards_played)} card" + ("s." if len(cards_played) > 1 else ".") 
            else:
                msg = f"{player} 出了 {len(cards_played)} 张牌"
            update_game_state(msg)
            self.show_message(msg, msg_type="play", voice=False)

        player.in_play = False
        return cards_played
    
    def prompt_russian_roulette(self, player_index):
        player = self.all_players[player_index]
        if self.russian_roulette(player): 
            self.dead_players.append(player_index)
            return f"{player.name} (player {player_index}) has been killed in the RR!"
        else:
            return f"{player.name} (player {player_index}) has survived the RR!"

    def play(self):
        log_message("Playing the game...")

        agent_prompt = AGENT_PROMPT.format(
            player0=self.all_players[0].name,
            player1=self.all_players[1].name,
            player2=self.all_players[2].name,
            player3=self.all_players[3].name,
            lang = LangName
        )
        self.agent_messages = [
            system_message(agent_prompt),
            user_message(f"Play a game of BluffMind with {len(self.all_players)} players.")
        ]
        response = self.agent.f_call(self.agent_messages, tools=self.tools)

        while True:
            self.agent_messages.append(response.model_dump())

            if "GAME OVER" in response.content:
                print(f"LLM returned: {response.content}")
                break
            if "COMMENT:" in response.content:
                comment = response.content.replace("COMMENT:", "", 1).strip()
                update_game_state(f"Announcer Taunt: {comment}")
                self.wait_say()
                #self.voice_say(Announcer_voice, comment, speed=1.0)
                self.show_message(comment)
            if response.tool_calls is not None:
                tool_call = response.tool_calls[0]
                tool_name = tool_call.function.name
                if self.agent.api_type == APIType.OPENROUTER:
                    tool_args = json.loads(tool_call.function.arguments)
                elif self.agent.api_type == APIType.OLLAMA:
                    tool_args = tool_call.function.arguments

                if tool_name in self.TOOL_MAPPING:
                    tool_response = self.TOOL_MAPPING[tool_name](**tool_args)
                    if type(tool_response) is str and "killed" in tool_response:
                        self.agent_messages = [
                            system_message(agent_prompt),
                            user_message(f"Continue the game of BluffMind with {len(self.all_players)} players. Account for the fact that players {self.dead_players} have been killed. The game has already been started, do not call the 'start_game' tool again.")
                        ]
                    else:
                        self.agent_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": json.dumps(tool_response)
                        })
                else:
                    print(response)
                    raise Exception(f"Tool {tool_name} not found in TOOL_MAPPING")
            response = self.agent.f_call(self.agent_messages, tools=self.tools)
        self.state = "finished"

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="BluffMind")
    parser.add_argument('-b', '--batch', action='store_true', help='Enable batch mode (no dashboard, no voice acting)')
    parser.add_argument('-d', '--disable_agent', action='store_true', help='Disable the agent mode and run the game in normal program mode')
    parser.add_argument('-l', '--logfile', type=str, default='bluff_mind.log', help='Log file name')
    parser.add_argument('-c', '--config', type=str, default='config.json', help='Configuration file for players')
    args = parser.parse_args()

    config = args.config
    players = []

    if config:
        config_file = config
    else:
        config_file = "config.json"
    try:
        with open(config_file, 'r') as f:
            data = json.load(f)
            Language = data.get("language", "a")
            for player_data in data.get("players", []):
                name = player_data.get("name", "Unknown")
                model = player_data.get("model", "Random")
                api = player_data.get("api", "openrouter")
                if api.lower() not in [APIType.OPENROUTER.value, APIType.OLLAMA.value]:
                    raise TypeError(f"Invalid API type: {api}. Supported types are: {APIType.OPENROUTER.value}, {APIType.OLLAMA.value}.")
                if model != "Random":
                    model = BLMPClient(model=model, api_type=APIType(api.lower()))
                persona = player_data.get("persona", "")
                voice = player_data.get("voice", "am_echo")
                aggro = player_data.get("aggro", 50)
                players.append(Player(name, model, persona, voice, aggro))
    except Exception as e:
        print(f"Error loading configuration file {config_file}: {e}")
        exit(1)

    if Language == "a":
        LangName = "English"
        Announcer_voice = "am_eric"  
    else:
        LangName = "Chinese"
        Announcer_voice = "zm_yunyang"  

    log_start(args.logfile, args.batch)

    if args.batch is False:
        from display import get_show_context
        show_context = get_show_context(agent_mode=(not args.disable_agent), lang=Language)
        show_context.__enter__()
    else:
        show_context = None

    if args.disable_agent:
        log_message("Running in normal mode...")
        game = GameProg(players, show_context=show_context) 
    else:
        log_message("Running in agent mode...")
        game = GameAgent(players, show_context=show_context)
        
    # Use the __enter__, try, finally, __exit__ pattern instead of 'with' statement so that
    # the SHOW mode and BATCH mode can use the same code. 
    try:
        game.play()
        game.report()
    finally:
        if show_context is not None:
            show_context.__exit__(None, None, None)

    log_end()
