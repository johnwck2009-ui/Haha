# haha777bot — Football Player Statistics

A lightweight Telegram bot for searching popular footballers and viewing manually maintained career statistics.

## Features

- Search the local player database by name.
- Browse the seeded popular-player list.
- View player profiles and club history.
- View club and international appearances, goals and assists.
- Display combined appearances and goals when both component totals are available.
- Show a top-scorers list after verified goal totals have been entered.
- Restrict statistics updates to configured Telegram administrators.

## No external sports API

The bot uses only the Telegram Bot API for messaging. Player records live in `data/players.json`; statistics must be researched, checked and updated by an administrator. The initial player records intentionally have blank statistics rather than fabricated numbers.

## Requirements

- Python 3.10+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## Setup

1. Clone this repository.
2. Create and activate a virtual environment.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Set environment variables:

   - `BOT_TOKEN`: token issued by BotFather.
   - `ADMIN_USER_IDS`: comma-separated numeric Telegram user IDs allowed to update statistics.
   - `LOG_LEVEL`: optional logging level (defaults to `INFO`).

   Example:

   ```bash
   export BOT_TOKEN="your-token"
   export ADMIN_USER_IDS="123456789"
   ```

5. Start the bot:

   ```bash
   python main.py
   ```

Never commit a real bot token or a real `.env` file.

## User commands

- `/start` — open the main menu.
- `/search NAME` — search for a player.
- `/popular` — browse popular players.
- `/top` — list players with complete club and international goal totals.
- `/help` — show help.

## Administrator command

Set all available career totals for a player:

```text
/setstats PLAYER_ID CLUB_APPS CLUB_GOALS CLUB_ASSISTS INTL_APPS INTL_GOALS
```

Example format (illustrative values only):

```text
/setstats 1 100 80 20 30 15
```

The command is available only to Telegram user IDs listed in `ADMIN_USER_IDS`. It updates the selected player's `career` record and records the update date. Use verified totals and a consistent statistical source/definition.

## Data definitions

- Club appearances, goals and assists cover the player's senior club career.
- International appearances and goals cover senior national-team matches.
- Combined appearances and goals are shown only when both club and international values have been entered.
- Assists are currently tracked for club career only.
- Missing values are displayed as "Not added yet"; they are not treated as zero.

## Database maintenance

Edit `data/players.json` to add player profiles or update club history. Keep player IDs unique. The bot writes statistics updates back to this JSON file.

For reliable long-term hosting, use persistent storage and run one bot instance at a time because the JSON file is the database.
