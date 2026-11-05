import html
import json
import logging
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "data" / "players.json"
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
logger = logging.getLogger("haha777bot")


def load_players() -> list[dict[str, Any]]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DATABASE_PATH.exists():
        return []
    with DATABASE_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("The player database must contain a JSON list.")
    return data


def save_players(players: list[dict[str, Any]]) -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(
        prefix="players_", suffix=".json", dir=DATABASE_PATH.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(players, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary_path, DATABASE_PATH)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def find_player(player_id: int) -> dict[str, Any] | None:
    return next((p for p in load_players() if p.get("id") == player_id), None)


def is_admin(user_id: int) -> bool:
    configured = os.getenv("ADMIN_USER_IDS", "")
    allowed = {value.strip() for value in configured.split(",") if value.strip()}
    return str(user_id) in allowed


def number(value: Any) -> str:
    return f"{value:,}" if isinstance(value, int) else "Not added yet"


def combined_value(club_value: Any, international_value: Any) -> int | None:
    if isinstance(club_value, int) and isinstance(international_value, int):
        return club_value + international_value
    return None


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔎 Search player", callback_data="search"),
            InlineKeyboardButton("⭐ Popular players", callback_data="popular"),
        ],
        [
            InlineKeyboardButton("⚽ Top goal scorers", callback_data="top"),
            InlineKeyboardButton("ℹ️ About", callback_data="about"),
        ],
    ])


def player_keyboard(player_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Career statistics", callback_data=f"stats:{player_id}")],
        [InlineKeyboardButton("⬅️ Main menu", callback_data="menu")],
    ])


def player_summary(player: dict[str, Any]) -> str:
    name = html.escape(player.get("name", "Unknown player"))
    nationality = html.escape(player.get("nationality") or "Not added")
    position = html.escape(player.get("position") or "Not added")
    birth_date = html.escape(player.get("date_of_birth") or "Not added")
    club = html.escape(player.get("current_club") or "Not added")
    return (
        f"⚽ <b>{name}</b>\n\n"
        f"🌍 Nationality: {nationality}\n"
        f"📍 Position: {position}\n"
        f"🎂 Date of birth: {birth_date}\n"
        f"🏟 Current club: {club}\n\n"
        "Choose an option to explore this player."
    )


def career_statistics(player: dict[str, Any]) -> str:
    name = html.escape(player.get("name", "Unknown player"))
    career = player.get("career", {})
    club = career.get("club", {})
    international = career.get("international", {})
    clubs = player.get("clubs", [])
    club_lines = "\n".join(f"• {html.escape(str(item))}" for item in clubs) or "Not added yet"

    club_apps = club.get("appearances")
    club_goals = club.get("goals")
    club_assists = club.get("assists")
    intl_apps = international.get("appearances")
    intl_goals = international.get("goals")

    total_apps = combined_value(club_apps, intl_apps)
    total_goals = combined_value(club_goals, intl_goals)

    updated = html.escape(player.get("last_updated") or "Not updated")
    return (
        f"📊 <b>CAREER STATISTICS</b>\n"
        f"<b>{name}</b>\n\n"
        "🏟 <b>Club career</b>\n"
        f"Appearances: {number(club_apps)}\n"
        f"Goals: {number(club_goals)}\n"
        f"Assists: {number(club_assists)}\n\n"
        "🌍 <b>International career</b>\n"
        f"Appearances: {number(intl_apps)}\n"
        f"Goals: {number(intl_goals)}\n\n"
        "➕ <b>Combined totals</b>\n"
        f"Appearances: {number(total_apps)}\n"
        f"Goals: {number(total_goals)}\n\n"
        f"🏆 <b>Club history</b>\n{club_lines}\n\n"
        f"🗓 Last updated: {updated}\n"
        "<i>Statistics are maintained by the bot administrator. "
        "A missing value means it has not yet been entered.</i>"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("waiting_for_search", None)
    await update.message.reply_text(
        "⚽ <b>Welcome to haha777bot!</b>\n\n"
        "Your football player career statistics companion.\n\n"
        "Search popular players and explore their profiles, club records "
        "and international career totals.\n\n"
        "Choose an option below:",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "<b>haha777bot commands</b>\n\n"
        "/start — Open the main menu\n"
        "/search NAME — Search for a player\n"
        "/popular — Browse popular players\n"
        "/top — View the top goal scorers\n"
        "/help — Show this help message\n\n"
        "Administrators: /setstats for updating player totals.",
        parse_mode=ParseMode.HTML,
    )


async def send_search_results(message, query: str) -> None:
    normalized = query.casefold().strip()
    if not normalized:
        await message.reply_text("Please enter a player's name.")
        return
    matches = [
        player for player in load_players()
        if normalized in player.get("name", "").casefold()
    ][:10]
    if not matches:
        await message.reply_text(
            "I couldn't find that player in the local database. Try another name."
        )
        return
    rows = [
        [InlineKeyboardButton(
            f"⚽ {player['name']}",
            callback_data=f"player:{player['id']}",
        )]
        for player in matches
    ]
    rows.append([InlineKeyboardButton("⬅️ Main menu", callback_data="menu")])
    await message.reply_text(
        f"Found {len(matches)} matching player(s). Select one:",
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args).strip()
    if not query:
        context.user_data["waiting_for_search"] = True
        await update.message.reply_text("🔎 Send the player's name to search.")
        return
    await send_search_results(update.message, query)


async def popular_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_popular(update.message)


async def show_popular(message) -> None:
    players = load_players()[:20]
    if not players:
        await message.reply_text("The player database is currently empty.")
        return
    rows = [
        [InlineKeyboardButton(f"⭐ {p['name']}", callback_data=f"player:{p['id']}")]
        for p in players
    ]
    rows.append([InlineKeyboardButton("⬅️ Main menu", callback_data="menu")])
    await message.reply_text(
        "⭐ <b>Popular players</b>\nChoose a player:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_top(update.message)


async def show_top(message) -> None:
    players = []
    for player in load_players():
        career = player.get("career", {})
        club_goals = career.get("club", {}).get("goals")
        intl_goals = career.get("international", {}).get("goals")
        total = combined_value(club_goals, intl_goals)
        if total is not None:
            players.append((total, player))
    players.sort(key=lambda item: item[0], reverse=True)
    if not players:
        await message.reply_text(
            "Top scorers will appear once verified club and international goal "
            "totals have been entered by the administrator."
        )
        return
    lines = ["⚽ <b>TOP CAREER GOAL SCORERS</b>\n"]
    for rank, (goals, player) in enumerate(players[:10], start=1):
        lines.append(
            f"{rank}. {html.escape(player['name'])} — <b>{goals:,}</b> goals"
        )
    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "menu":
        context.user_data.pop("waiting_for_search", None)
        await query.edit_message_text(
            "⚽ <b>haha777bot</b>\n\nChoose what you'd like to explore:",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(),
        )
    elif data == "search":
        context.user_data["waiting_for_search"] = True
        await query.message.reply_text("🔎 Send the player's name to search.")
    elif data == "popular":
        await show_popular(query.message)
    elif data == "top":
        await show_top(query.message)
    elif data == "about":
        await query.message.reply_text(
            "<b>About haha777bot</b>\n\n"
            "A community-maintained football player database for exploring "
            "player profiles and career statistics. No external sports API is used.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(),
        )
    elif data.startswith("player:") or data.startswith("stats:"):
        action, raw_id = data.split(":", 1)
        try:
            player = find_player(int(raw_id))
        except ValueError:
            player = None
        if not player:
            await query.message.reply_text("That player could not be found.")
            return
        if action == "player":
            await query.message.reply_text(
                player_summary(player),
                parse_mode=ParseMode.HTML,
                reply_markup=player_keyboard(player["id"]),
            )
        else:
            await query.message.reply_text(
                career_statistics(player),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "⬅️ Player profile",
                        callback_data=f"player:{player['id']}",
                    ),
                    InlineKeyboardButton("🏠 Main menu", callback_data="menu"),
                ]]),
            )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("waiting_for_search"):
        context.user_data.pop("waiting_for_search", None)
        await send_search_results(update.message, update.message.text or "")
        return
    await update.message.reply_text(
        "Use the menu or /help to see what I can do.",
        reply_markup=main_menu(),
    )


async def setstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ This command is restricted to the bot administrator.")
        return
    if len(context.args) != 6:
        await update.message.reply_text(
            "Usage:\n/setstats PLAYER_ID CLUB_APPS CLUB_GOALS CLUB_ASSISTS INTL_APPS INTL_GOALS\n\n"
            "Use whole numbers. Example:\n"
            "/setstats 1 1200 900 250 200 130"
        )
        return
    try:
        player_id = int(context.args[0])
        values = [int(value) for value in context.args[1:]]
        if any(value < 0 for value in values):
            raise ValueError
    except ValueError:
        await update.message.reply_text("Player ID and statistics must be non-negative whole numbers.")
        return

    players = load_players()
    player = next((p for p in players if p.get("id") == player_id), None)
    if not player:
        await update.message.reply_text("Player ID not found.")
        return
    club_apps, club_goals, club_assists, intl_apps, intl_goals = values
    player["career"] = {
        "club": {
            "appearances": club_apps,
            "goals": club_goals,
            "assists": club_assists,
        },
        "international": {
            "appearances": intl_apps,
            "goals": intl_goals,
        },
    }
    player["last_updated"] = date.today().isoformat()
    save_players(players)
    await update.message.reply_text(
        f"✅ Updated career statistics for {player['name']}."
    )


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN is missing. Set it as an environment variable; "
            "never place your Telegram token in source code."
        )
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("popular", popular_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("setstats", setstats_command))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("Starting haha777bot polling.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
