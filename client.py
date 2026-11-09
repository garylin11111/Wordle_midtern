import os
import sys

import pygame
import requests

API_BASE_URL = "https://wordle-midtern.onrender.com"

COLOR_BG = (18, 18, 19)
COLOR_TEXT = (255, 255, 255)
COLOR_EMPTY = (58, 58, 60)
COLOR_CORRECT = (83, 141, 78)
COLOR_PRESENT = (181, 159, 59)
COLOR_ABSENT = (58, 58, 60)
COLOR_MUTED = (180, 180, 185)
COLOR_PANEL = (35, 35, 38)
COLOR_BORDER = (80, 80, 80)

pygame.init()
WIDTH, HEIGHT = 700, 650 
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Wordle + FastAPI — Midterm")
font = pygame.font.SysFont("Arial", 36, bold=True)
small_font = pygame.font.SysFont("Arial", 18)
mini_font = pygame.font.SysFont("Arial", 15)
side_font = pygame.font.SysFont("Arial", 20, bold=True)


class WordleGame:
    def __init__(self):
        self.game_id = None
        self.grid = [["" for _ in range(5)] for _ in range(6)]
        self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
        self.history = []
        self.row = 0
        self.col = 0
        self.game_over = False
        self.hard_mode = False       
        self.next_hard_mode = False 
        self.total_games = 0
        self.wins = 0
        self.win_rate = 0.0
        self.message = "Press ENTER to submit, Ctrl+R to restart"
        self.start_new_game()

    def refresh_stats(self):
        try:
            response = requests.get(f"{API_BASE_URL}/api/stats", timeout=10)
            response.raise_for_status()
            data = response.json()
            self.total_games = data.get("total_games", 0)
            self.wins = data.get("wins", 0)
            self.win_rate = data.get("win_rate", 0.0)
        except (requests.exceptions.RequestException, ValueError):
            pass  

    def start_new_game(self):
        """R 重新開始時，才把 H 選定的模式送至後端。"""
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/new-game",
                params={"hard_mode": str(self.next_hard_mode).lower()},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            self.game_id = data["game_id"]
            self.hard_mode = data.get("hard_mode", self.next_hard_mode)
            self.grid = [["" for _ in range(5)] for _ in range(6)]
            self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
            self.history = []
            self.row = 0
            self.col = 0
            self.game_over = False
            self.message = "New game! Enter 5 letters. (Ctrl+H: next mode)"
            self.refresh_stats()
        except (requests.exceptions.RequestException, ValueError, KeyError):
            if self.game_id is None:
                self.message = "Cannot connect to FastAPI server!"
            else:
                self.message = "Server error. Ctrl+R to try again."

    def submit_guess(self):
        if self.game_id is None:
            self.message = "Server offline. Press Ctrl+R to retry."
            return
        if self.game_over or self.row >= 6:
            return
        if self.col < 5:
            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/guess",
                json={"game_id": self.game_id, "guess": guess_word},
                timeout=60,
            )
            if response.status_code != 200:
                try:
                    detail = response.json().get("detail", "Error processing guess")
                except ValueError:
                    detail = "Server returned an error."
                if detail == "Word not in dictionary":
                    self.message = "Not in word list! Use BACKSPACE to edit."
                elif detail.startswith("Hard Mode:"):
                    self.message = "Hard Mode: keep green letters in their positions!"
                else:
                    self.message = detail
                return  

            data = response.json()
            feedback = data["feedback"]
            colors = {
                "correct": COLOR_CORRECT,
                "present": COLOR_PRESENT,
                "absent": COLOR_ABSENT,
            }
            for i in range(5):
                self.colors[self.row][i] = colors.get(feedback[i], COLOR_ABSENT)
            self.history.append((guess_word, feedback))

            if data["is_correct"]:
                self.game_over = True
                self.message = "Congratulations! You won! Press Ctrl+R to restart."
                self.refresh_stats()
            elif data.get("game_over", False) or self.row == 5:
                self.game_over = True
                word = data.get("target_word", "?????")
                self.message = f"Game Over! The word was {word}. Press Ctrl+R to restart."
                self.refresh_stats()
            else:
                self.row += 1
                self.col = 0
                tries_left = data.get("tries_left", 6 - self.row)
                self.message = f"Row {self.row + 1}/6: Enter next word! ({tries_left} tries left)"
        except (requests.exceptions.RequestException, ValueError, KeyError, IndexError):
            self.message = "Network / server error during guess!"

    def handle_keydown(self, event):
        if event.mod & pygame.KMOD_CTRL and event.key == pygame.K_h:
            self.next_hard_mode = not self.next_hard_mode
            next_mode = "HARD" if self.next_hard_mode else "Normal"
            self.message = f"Next game mode: {next_mode}. Press Ctrl+R to start."
            return
        if event.mod & pygame.KMOD_CTRL and event.key == pygame.K_r:
            self.start_new_game()
            return
        if self.game_over or self.game_id is None or self.row >= 6:
            return

        if event.key == pygame.K_BACKSPACE:
            if self.col > 0:
                self.col -= 1
                self.grid[self.row][self.col] = ""
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.submit_guess()
        elif len(event.unicode) == 1 and event.unicode.isascii() and event.unicode.isalpha():
            if self.col < 5:
                self.grid[self.row][self.col] = event.unicode.upper()
                self.col += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)
        margin_x, margin_y = 75, 78
        box_size, gap = 60, 10

        for row in range(6):
            for col in range(5):
                x = margin_x + col * (box_size + gap)
                y = margin_y + row * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)
                pygame.draw.rect(surface, self.colors[row][col], rect, border_radius=4)
                if self.colors[row][col] == COLOR_EMPTY:
                    pygame.draw.rect(surface, COLOR_BORDER, rect, width=2, border_radius=4)
                char = self.grid[row][col]
                if char:
                    letter = font.render(char, True, COLOR_TEXT)
                    surface.blit(letter, letter.get_rect(center=rect.center))

        pygame.draw.rect(surface, COLOR_PANEL, pygame.Rect(500, 0, 200, HEIGHT))
        pygame.draw.line(surface, COLOR_BORDER, (500, 0), (500, HEIGHT), 2)
        title = side_font.render("History", True, COLOR_TEXT)
        surface.blit(title, (520, 85))
        for index, (word, feedback) in enumerate(self.history):
            y = 130 + index * 58
            no = mini_font.render(str(index + 1), True, COLOR_MUTED)
            surface.blit(no, (514, y + 7))
            for i, char in enumerate(word):
                rect = pygame.Rect(530 + i * 32, y, 29, 32)
                shade = {
                    "correct": COLOR_CORRECT,
                    "present": COLOR_PRESENT,
                    "absent": COLOR_ABSENT,
                }.get(feedback[i], COLOR_ABSENT)
                pygame.draw.rect(surface, shade, rect, border_radius=3)
                txt = mini_font.render(char, True, COLOR_TEXT)
                surface.blit(txt, txt.get_rect(center=rect.center))

        mode = "HARD" if self.next_hard_mode else "Normal"
        current = "HARD" if self.hard_mode else "Normal"
        surface.blit(mini_font.render(f"Mode: {mode}", True, COLOR_TEXT), (518, 12))
        detail = f"Current: {current}" if mode != current else "Ctrl+H: Toggle / Ctrl+R: Start"
        surface.blit(mini_font.render(detail, True, COLOR_MUTED), (518, 38))

        status_font = small_font
        msg_surface = status_font.render(self.message, True, COLOR_TEXT)
        if msg_surface.get_width() > WIDTH - 24:
            status_font = mini_font
            msg_surface = status_font.render(self.message, True, COLOR_TEXT)
        surface.blit(msg_surface, msg_surface.get_rect(center=(WIDTH // 2, 556)))

        stats_text = f"Total: {self.total_games} | Wins: {self.wins} | Win Rate: {self.win_rate:.1f}%"
        stats_surface = small_font.render(stats_text, True, COLOR_TEXT)
        surface.blit(stats_surface, stats_surface.get_rect(center=(WIDTH // 2, 612)))
        hint = mini_font.render("ENTER: Guess  BACKSPACE: Edit  Ctrl+R: Restart  Ctrl+H: Mode", True, COLOR_MUTED)
        surface.blit(hint, hint.get_rect(center=(WIDTH // 2, 583)))


def main():
    clock = pygame.time.Clock()
    game = WordleGame()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event)
        game.draw(screen)
        pygame.display.flip()
        clock.tick(30)


if __name__ == "__main__":
    main()
