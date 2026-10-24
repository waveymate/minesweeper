"""Minesweeper — text-based terminal game."""

import random
import time
import os
import sys


class Cell:
    def __init__(self):
        self.mine = False
        self.revealed = False
        self.flagged = False
        self.adjacent = 0


class Board:
    def __init__(self, rows, cols, mines):
        self.rows = rows
        self.cols = cols
        self.total_mines = mines
        self.cells = [[Cell() for _ in range(cols)] for _ in range(rows)]
        self.state = "playing"  # playing / won / lost
        self.start_time = None
        self.end_time = None
        self.first_move = True
        self.flags = 0

    def _neighbors(self, r, c):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    yield nr, nc

    def _place_mines(self, safe_r, safe_c):
        safe = {(safe_r, safe_c)} | set(self._neighbors(safe_r, safe_c))
        candidates = [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if (r, c) not in safe
        ]
        for r, c in random.sample(candidates, min(self.total_mines, len(candidates))):
            self.cells[r][c].mine = True
        for r in range(self.rows):
            for c in range(self.cols):
                if not self.cells[r][c].mine:
                    self.cells[r][c].adjacent = sum(
                        1 for nr, nc in self._neighbors(r, c)
                        if self.cells[nr][nc].mine
                    )

    def reveal(self, r, c):
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            raise ValueError(f"Position ({r},{c}) is out of bounds.")
        if self.first_move:
            self.first_move = False
            self.start_time = time.time()
            self._place_mines(r, c)
        cell = self.cells[r][c]
        if cell.flagged:
            raise ValueError("That cell is flagged. Unflag it first with 'u'.")
        if cell.revealed:
            raise ValueError("That cell is already revealed.")
        cell.revealed = True
        if cell.mine:
            self.state = "lost"
            self.end_time = time.time()
            self._reveal_all()
            return
        if cell.adjacent == 0:
            for nr, nc in self._neighbors(r, c):
                nb = self.cells[nr][nc]
                if not nb.revealed and not nb.flagged:
                    self.reveal(nr, nc)
        self._check_win()

    def chord(self, r, c):
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            raise ValueError(f"Position ({r},{c}) is out of bounds.")
        cell = self.cells[r][c]
        if not cell.revealed:
            raise ValueError("Cell is not revealed yet.")
        if cell.adjacent == 0:
            raise ValueError("No adjacent mines — nothing to chord.")
        flag_count = sum(
            1 for nr, nc in self._neighbors(r, c) if self.cells[nr][nc].flagged
        )
        if flag_count != cell.adjacent:
            raise ValueError(
                f"Need {cell.adjacent} flag(s) around this cell, found {flag_count}."
            )
        for nr, nc in self._neighbors(r, c):
            nb = self.cells[nr][nc]
            if not nb.flagged and not nb.revealed:
                nb.revealed = True
                if nb.mine:
                    self.state = "lost"
                    self.end_time = time.time()
                    self._reveal_all()
                    return
                if nb.adjacent == 0:
                    self.reveal(nr, nc)
                if self.state != "playing":
                    return
        self._check_win()

    def flag(self, r, c):
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            raise ValueError(f"Position ({r},{c}) is out of bounds.")
        cell = self.cells[r][c]
        if cell.revealed:
            raise ValueError("Cell is already revealed.")
        if cell.flagged:
            raise ValueError("Already flagged. Use 'u' to unflag.")
        cell.flagged = True
        self.flags += 1

    def unflag(self, r, c):
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            raise ValueError(f"Position ({r},{c}) is out of bounds.")
        cell = self.cells[r][c]
        if not cell.flagged:
            raise ValueError("Cell is not flagged.")
        cell.flagged = False
        self.flags -= 1

    def _reveal_all(self):
        for r in range(self.rows):
            for c in range(self.cols):
                if self.cells[r][c].mine:
                    self.cells[r][c].revealed = True

    def _check_win(self):
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                if not cell.mine and not cell.revealed:
                    return
        self.state = "won"
        self.end_time = time.time()

    def elapsed(self):
        if self.start_time is None:
            return 0
        end = self.end_time if self.end_time else time.time()
        return int(end - self.start_time)

    def mines_remaining(self):
        return self.total_mines - self.flags


NUM_COLORS = {
    1: "\033[94m",  # blue
    2: "\033[92m",  # green
    3: "\033[91m",  # red
    4: "\033[34m",  # dark blue
    5: "\033[31m",  # dark red
    6: "\033[96m",  # cyan
    7: "\033[95m",  # magenta
    8: "\033[90m",  # grey
}
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
DIM = "\033[2m"


def cell_str(cell):
    if cell.revealed:
        if cell.mine:
            return f"{RED}{BOLD}*{RESET}"
        elif cell.adjacent > 0:
            color = NUM_COLORS.get(cell.adjacent, "")
            return f"{color}{cell.adjacent}{RESET}"
        else:
            return " "
    elif cell.flagged:
        return f"{YELLOW}{BOLD}F{RESET}"
    else:
        return f"{DIM}.{RESET}"


def clear():
    os.system("clear" if os.name != "nt" else "cls")


def draw(board):
    clear()
    # Header
    status = ""
    if board.state == "won":
        status = f"  {GREEN}{BOLD}*** YOU WIN! ***{RESET}"
    elif board.state == "lost":
        status = f"  {RED}{BOLD}*** GAME OVER ***{RESET}"
    print(
        f"  Mines remaining: {BOLD}{board.mines_remaining():3d}{RESET}"
        f"  Time: {BOLD}{board.elapsed():4d}s{RESET}"
        f"{status}"
    )
    print()

    # Column headers
    col_w = 2
    indent = "    "
    col_nums = "".join(f"{c:<{col_w}}" for c in range(board.cols))
    print(f"{indent}  {DIM}{col_nums}{RESET}")
    sep = "  " + "-" * (board.cols * col_w + 1)
    print(f"{indent}{sep}")

    for r in range(board.rows):
        row_str = " ".join(cell_str(board.cells[r][c]) for c in range(board.cols))
        print(f"{indent}{r:2d}| {row_str}")

    print()


HELP = """\
Commands:
  r <row> <col>   Reveal a cell            e.g.  r 3 5
  f <row> <col>   Flag a cell              e.g.  f 3 5
  u <row> <col>   Unflag a cell            e.g.  u 3 5
  c <row> <col>   Chord (auto-reveal)      e.g.  c 3 5
  n               New game
  h               Show this help
  q               Quit
"""


def parse_cmd(line):
    parts = line.strip().lower().split()
    if not parts:
        return None, None, None
    cmd = parts[0]
    if cmd in ("n", "h", "q"):
        return cmd, None, None
    if cmd in ("r", "f", "u", "c"):
        if len(parts) != 3:
            raise ValueError(f"'{cmd}' needs row and col, e.g.: {cmd} 3 5")
        r, c = int(parts[1]), int(parts[2])
        return cmd, r, c
    raise ValueError(f"Unknown command '{cmd}'. Type 'h' for help.")


DIFFICULTIES = {
    "b": ("Beginner",     9,  9,  10),
    "i": ("Intermediate", 16, 16, 40),
    "e": ("Expert",       16, 30, 99),
}


def select_difficulty():
    clear()
    print(f"\n  {BOLD}MINESWEEPER{RESET}\n")
    print("  Select difficulty:")
    print("    [b] Beginner     (9x9,   10 mines)")
    print("    [i] Intermediate (16x16, 40 mines)")
    print("    [e] Expert       (16x30, 99 mines)")
    print()
    while True:
        try:
            choice = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None
        if choice in DIFFICULTIES:
            return DIFFICULTIES[choice]
        if choice in ("q", "quit"):
            return None
        print("  Please enter b, i, or e.")


def play(rows, cols, mines):
    board = Board(rows, cols, mines)
    draw(board)
    print(HELP)

    while True:
        if board.state != "playing":
            try:
                again = input("  Play again? [y/n] > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return False
            return again.startswith("y")

        try:
            line = input("  > ")
        except (EOFError, KeyboardInterrupt):
            return False

        try:
            cmd, r, c = parse_cmd(line)
        except ValueError as e:
            print(f"  {RED}Error:{RESET} {e}")
            continue

        if cmd is None:
            continue
        if cmd == "q":
            return False
        if cmd == "n":
            return True
        if cmd == "h":
            print(HELP)
            continue

        try:
            if cmd == "r":
                board.reveal(r, c)
            elif cmd == "f":
                board.flag(r, c)
            elif cmd == "u":
                board.unflag(r, c)
            elif cmd == "c":
                board.chord(r, c)
        except (ValueError, RecursionError) as e:
            print(f"  {RED}Error:{RESET} {e}")
            continue

        draw(board)
        if board.state == "lost":
            print(f"  {RED}{BOLD}BOOM! You hit a mine.{RESET}\n")
        elif board.state == "won":
            print(
                f"  {GREEN}{BOLD}Congratulations! Cleared in {board.elapsed()}s.{RESET}\n"
            )


def main():
    while True:
        result = select_difficulty()
        if result is None:
            break
        name, rows, cols, mines = result
        replay = play(rows, cols, mines)
        if not replay:
            break
    print("\n  Thanks for playing!\n")


if __name__ == "__main__":
    main()
