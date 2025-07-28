# BluffMind

BluffMind is a LLM powered program featuring the card game "Liar's Deck" from [Liar's Bar](https://store.steampowered.com/app/3097560/Liars_Bar/). The game has five actors: one dealer and four players, whom all can be controlled by their own LLM respectively. 

<p align="center" width="100%">
    <img width="614" height="530" alt="agentdealer drawio" src="https://github.com/user-attachments/assets/85c744d8-2ad9-4f5d-a83e-711bb4cb94d5"/>
</p>

The dealer is an agent who deals the cards, directs the players, and determines game processes live. The agent can see each players' cards and prompt Russian Roulette as necessary. Each player decides how to play based on cards in their hands, current game status, and their persona settings. They are also aware of other players in the game and their taunts, however of course, do not know their hands, played cards, or Russian Roulette position. The game runs autonomously and automatically, with all actors making their own decisions and taunting each other, in English or Chinese.

Each player can be configured to use online model serving provided by [OpenRouter](https://openrouter.ai/) or locally by [Ollama](https://ollama.com/). TTS functionality for each players' taunts and voicelines uses the [Kokoro](https://github.com/nazdridoy/kokoro-tts) model.

## English Demo

<video src="https://raw.githubusercontent.com/TangyKiwi/BluffMind/main/BM-Demo-English-c.mp4" controls></video>

## Chinese Demo

<video src="https://raw.githubusercontent.com/TangyKiwi/BluffMind/main/BM-Demo-Chinese-c.mp4>" controls></video>

## Installation
### 1) Python environment setup
We suggest using Python version `3.10.5`. Setup a virtual environment and install
the required libraries using:
```bash
pip install -r requirements.txt
```

### 2) TTS setup

TTS uses the [`kokoro`](https://github.com/hexgrad/kokoro) model and library. 

If you are on **MacOS**, you will also need the `PyObjC` package. Install with
```bash
pip install PyObjC
```

If you are on **Windows**, you will need to also install `espeak-ng`. 
1. Go to [espeak-ng releases](https://github.com/espeak-ng/espeak-ng/releases)  
2. Click on **Latest release**  
3. Download the appropriate `*.msi` file (e.g. **espeak-ng-20191129-b702b03-x64.msi**)  
4. Run the downloaded installer  

For advanced configuration and usage on Windows, see the [official espeak-ng Windows guide](https://github.com/espeak-ng/espeak-ng/blob/master/docs/guide.md)

Run `python tts.py` to load in the voice model and test that TTS is working. Refer back to [`kokoro`](https://github.com/hexgrad/kokoro) if you encounter any issues.

### 3) OpenRouter setup
Create an account on [OpenRouter](https://openrouter.ai) and obtain an API key. 
You can set this API key as an environment variable
```bash
export OPENROUTER_API_KEY=<your key>
```
or store it in a `.env` file your local repo.

### 4) Optional, Ollama setup
BluffMind also supports using Ollama to run models locally, for the players. Support for local dealer agent is yet to be implemented. Make sure to install the Python library as well.

```bash
pip install ollama
```

## Usage

To run a LLM powered game of BluffMind, use 

```bash
python bm.py
```

This, by default, will run a completely automated, agent-run game of BluffMind with TTS in your local terminal, visualized through a dashboard. Each player's hand, played cards, as well as LLM reasoning will be displayed, along with general game information, as illustrated in the demos above.

Additional arguments can be passed to modify the game process:
```
usage bm.py [-h] [-b] [-d] [-l LOGFILE] [-c CONFIG]

BluffMind

options:
  -h, --help            Show this help message and exit
  -b, --batch           Enable batch mode (no dashboard, no voice acting)
  -d, --disable_agent   Disable the agent and run the game in normal program mode
  -l LOGFILE, --logfile LOGFILE
                        Log file name
  -c CONFIG, --config CONFIG
                        Configuration file for players
```

- `-c/--config` allows you to customize all players using a config file in json format. The default config is:
```json
{
    "language": "a", # language for agent 'a' (English), 'z' (Chinese)
    "players": [
        {
            "name": "Snow White",
            "model": "google/gemini-2.5-flash",
            "api": "openrouter",
            "persona": "Gentle, observant, underestimated, with hidden inner strength. Appears naïve, lulls opponents into overconfidence, wins by calm consistency and timing — surprises all in the end. Catchphrase: 'Even the fairest can call your bluff.'",
            "voice": "af_heart",
            "aggro": 50
        },
        {
            "name": "Zoro",
            "model": "google/gemini-2.5-flash",
            "api": "openrouter",
            "persona": "Charming, daring, theatrical, unpredictable. Loves to bluff and mislead, wins through misdirection, occasionally throws in a flamboyant move for style. Catchphrase: 'Why play a safe hand when you can play a legendary one?'",
            "voice": "am_adam",
            "aggro": 50
        },
        {
            "name": "Sherlock",
            "model": "google/gemini-2.5-flash",
            "api": "openrouter",
            "persona": "Hyper-rational, observant, emotionally detached. Calculates odds with precision, bluffs rarely but effectively, reads other players' behavior like a book. Catchphrase: 'It's elementary. You're holding a bluff.'",
            "voice": "am_michael",
            "aggro": 50
        },
        {
            "name": "Lady Macbeth",
            "model": "google/gemini-2.5-flash",
            "api": "openrouter",
            "persona": "Ambitious, manipulative, intense under pressure. Plays aggressively, pushes others into mistakes, uses psychological pressure as a weapon. Catchphrase: 'Out, out, damned bluff! You cannot hide from me.'",
            "voice": "af_bella",
            "aggro": 50
        }
    ]
}
```

- `-b/--batch` runs the game without the dashboard and voice acting. This is useful for debugging and batch experiments. 

- `-l/--logfile` pipes output to a specified log file. By default, it is `bluff_mind.log`.

- `-d/--disable_agent` runs the dealer using pre-programed logic instead of a LLM agent. 

## Agent Functionality

On top of a standard LLM, an agent is able to interact with the "environment" it's in using externally given tools and make decisions on further actions. It's able to perform real-world tasks like fetching live data, making changes to its environment, or executing code. 

Our BluffMind dealer is a good use of an LLM agent. Given a set of rules and external functions, our dealer agent can effectively and accurately use the results from such functions to run the game with other AI players. The agent can and will: setup and start the game, determine a player round for every round, prompt players in order to play their turn, determine a challenge result and who needs to play Russian Roulette, play Russian Roulette for said player, and finally, determine who is the winner, all through the use of functions we give to it. Occasionally, the agent itself will taunt all the players in the game with a comment.
 
The agent is given the following functions:  
- `start_game()`: Starts the game. This will reset the game state and prepare for a new round.  
- `prompt_round_order()`: Determines the order of players for the current round. Returns a list of players in the order they will play. Only includes players who are alive. The agent stores by itself, the returned order of the players and will issue respective function calls following such order.  
- `start_round(int[] players)`: Starts the new round. Shuffles the deck of cards and re-deals them to players. The agent passes in the list of players, identified by index, when calling this function.
- `prompt_player_turn(player_index, last_player_index)`: Prompts a player with index i to take their turn, accounting also for the last player's index. The agent determines these indices and passes them in accordingly, using `None` if there was no last player. The agent also stores by itself, the returned played hand by the player (`None` if the player chooses to challenge)  
- `prompt_check_cards(str[] cards)`: Checks if all the cards played by a player match the table card. Used to determine if a challenge is successful. The agent only calls this function when necessary (if a challenge is issued) and passes in the stored played cards from the respective player.
- `prompt_russian_roulette(player_index)`: Prompts a player with index i to play Russian Roulette (RR) after a challenge is issued. The agent only calls this function when necessary, and determines by itself using the rules of BluffMind who to issue the prompt to after a challenge is issued.  

When the agent decides to taunt, it also returns a message in the format of `COMMENT: <taunt>`, which we detect and pass accordingly to the game state. The agent itself determines when the game ends, and returns only a message in the format of `GAME OVER: <winner> won!`

The following diagram shows the overall flow of a game run. The agent logic (in the dotted box) is described in the rule prompt given to the LLM, rather than hard-coded in the program. 

<p align="center" width="100%">
    <img width="773" height="806" alt="bluffmindagent drawio" src="https://github.com/user-attachments/assets/55cc3895-9aa1-4ed8-9c65-cd3fe1e7d83b" />
</p>

## Game Rules

The game uses 20 playing cards, consisting of 6 Queens (Q), 6 Kings (K), 6 Aces (A), and 2 Jokers. Jokers can be used as any card, functioning as wild cards.

The game is played by 4 players and proceeds in rounds. In each round, every player is dealt 5 cards, and one of the three card types (Q, K, or A) is randomly selected as the **"table card"**. 

The players sit around a table and take turns to play cards in clockwise order, starting with a random person. On each turn, a player may play 1 to 3 cards and **claim** they are all the "table card" (they may bluff). The next player may choose whether or not to **challenge** this claim. If the next player does not challenge, the next player proceeds to play cards. The next player must challenge if he has no card left in his hand. 

Each player has a **revolver** with 3 chambers. At the start of the game, **one bullet is randomly loaded** into one of the chambers. Each time a player files the revolver,  the chamber advances by one position. The chamber does not advance if the revolver is not fired. 

During the challenge phase:

- If the challenge **succeeds** (the previous player included at least one non-table card), the **previous player loses** and must fire the revolver at themselves.
    
- If the challenge **fails** (all cards played were table cards or Joker), the **challenger loses** and must fire the revolver at himself.
    
Once a challenge occurs, the round ends. All surviving players proceed to the next round. At the start of a new round, all previous cards are discarded, each player is dealt a new hand of 5 cards, a new table card is selected, and the players are reseated in a random order. The chambers of all revolvers stay in their current position. 

The game ends when only **one player remains alive**.

##  Files

### `bm.py`
The main program.

### `blmp.py`
The basic client used to interact with OpenRouter/Ollama's APIs for LLM usage.

### `tts.py`
The text-to-speech pipeline, OS specific, which handles the real time generation and playing of each players' and the game announcer's voicelines.

### `log.py`
Basic logging functions for `bm.py`.

### `display.py`
Display functions for the terminal dashboard.

### `config.json`
The default config file for the players. 

### `config-z.json`
An example config file for players in Chinese.
