"""Wordle FastAPI server — 程式設計期中考 (2026)."""

import os
import random
import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORD_BANK = [
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART", "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT",
    "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIKE", "ALIVE", "ALLOW", "ALONE",
    "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE", "ANGRY", "APART", "APPLY", "ARGUE", "ARISE",
    "ARRAY", "ARROW", "ASIDE", "ASSET", "AUDIO", "AUDIT", "AVOID", "AWAKE", "AWARE", "BADGE",
    "BAKER", "BASIC", "BASIS", "BEACH", "BEGIN", "BEING", "BELOW", "BENCH", "BLACK", "BLAME",
    "BLANK", "BLAST", "BLEED", "BLEND", "BLOCK", "BLOOD", "BOARD", "BOAST", "BONUS", "BOOST",
    "BOUND", "BREAD", "BREAK", "BRICK", "BRIEF", "BRING", "BROAD", "BROWN", "BRUSH", "BUILD",
    "BUNCH", "BUYER", "CABLE", "CANDY", "CARGO", "CARRY", "CATCH", "CAUSE", "CHAIN", "CHAIR",
    "CHALK", "CHARM", "CHART", "CHASE", "CHEAP", "CHECK", "CHEST", "CHIEF", "CHILD", "CHOSE",
    "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR", "CLIMB", "CLOCK", "CLOSE", "COACH", "COAST",
    "COUNT", "COURT", "COVER", "CRASH", "CREAM", "CRIME", "CROSS", "CROWD", "CROWN", "CURVE",
    "CYCLE", "DAILY", "DANCE", "DEATH", "DELAY", "DEPTH", "DRAFT", "DRAMA", "DREAM", "DRIVE",
    "EAGLE", "EARLY", "EARTH", "EIGHT", "EMPTY", "ENEMY", "ENJOY", "ENTER", "EQUAL", "ERROR",
    "EVENT", "EVERY", "EXACT", "EXIST", "FAITH", "FALSE", "FAULT", "FIELD", "FIGHT", "FINAL",
    "FIRST", "FLAME", "FLASH", "FLOAT", "FLOOR", "FLOUR", "FLUID", "FOCUS", "FORCE", "FORTH",
    "FORTY", "FORUM", "FRAME", "FRESH", "FRONT", "FRUIT", "GIANT", "GLASS", "GLOBE", "GRACE",
    "GRADE", "GRAND", "GRANT", "GRASS", "GREAT", "GREEN", "GROUP", "GUARD", "GUESS", "GUIDE",
    "HAPPY", "HEART", "HEAVY", "HOTEL", "HUMAN", "IMAGE", "INDEX", "INPUT", "ISSUE", "JUDGE",
    "KNIFE", "LAYER", "LEMON", "LEVEL", "LIMIT", "LUNCH", "MAGIC", "MAJOR", "MARCH", "MATCH",
    "MEDAL", "MONEY", "MONTH", "MUSIC", "NIGHT", "NOVEL", "NURSE", "OCEAN", "OFFER", "ORDER",
]

games_db: Dict[str, dict] = {}
stats = {"total_games": 0, "wins": 0}


class GuessRequest(BaseModel):
    game_id: str
    guess: str


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/stats")
def get_stats():
    total = stats["total_games"]
    wins = stats["wins"]
    return {
        "total_games": total,
        "wins": wins,
        "win_rate": round(wins / total * 100, 1) if total else 0.0,
    }


@app.post("/api/new-game")
def start_new_game(hard_mode: bool = False):
    """新遊戲；hard_mode 是可選的 query 參數，預設 False。"""
    game_id = str(uuid.uuid4())
    games_db[game_id] = {
        "target": random.choice(WORD_BANK),
        "status": "PLAYING",
        "hard_mode": hard_mode,
        "attempts": [],
    }
    stats["total_games"] += 1
    return {
        "game_id": game_id,
        "message": "New game started!",
        "hard_mode": hard_mode,
    }


@app.post("/api/guess")
def process_guess(req: GuessRequest):
    """驗證輸入、判斷顏色，並在第 6 次失敗時揭曉答案。"""
    if req.game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game session not found.")

    game = games_db[req.game_id]
    if game["status"] != "PLAYING":
        raise HTTPException(status_code=400, detail="Game is already over.")

    guess = req.guess.upper()
    if len(guess) != 5 or not guess.isascii() or not guess.isalpha():
        raise HTTPException(status_code=400, detail="Word must be 5 English letters.")
    if guess not in WORD_BANK:
        raise HTTPException(status_code=400, detail="Word not in dictionary")

    if game["hard_mode"]:
        for previous in game["attempts"]:
            for i, result in enumerate(previous["feedback"]):
                if result == "correct" and guess[i] != previous["guess"][i]:
                    raise HTTPException(
                        status_code=400,
                        detail="Hard Mode: Must use revealed hint at green position",
                    )

    target = game["target"]
    feedback = ["absent"] * 5
    remaining = {}
    for letter in target:
        remaining[letter] = remaining.get(letter, 0) + 1

    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = "correct"
            remaining[guess[i]] -= 1

    for i in range(5):
        if feedback[i] != "correct" and remaining.get(guess[i], 0) > 0:
            feedback[i] = "present"
            remaining[guess[i]] -= 1

    game["attempts"].append({"guess": guess, "feedback": feedback})
    attempts_used = len(game["attempts"])
    is_correct = guess == target

    if is_correct:
        game["status"] = "WON"
        stats["wins"] += 1  
    elif attempts_used >= 6:
        game["status"] = "LOST"

    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        "target_word": target if game["status"] != "PLAYING" else None,
        "attempts_used": attempts_used,
        "tries_left": max(0, 6 - attempts_used),
        "game_over": game["status"] != "PLAYING",
        "hard_mode": game["hard_mode"],
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
