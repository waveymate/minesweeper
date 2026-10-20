"""Minesweeper — terminal game using curses."""

import curses
import random
import time
from enum import Enum


class State(Enum):
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


class Cell:
    def __init__(self):
        self.mine = False
        self.revealed = False
        self.flagged = False
        self.adjacent = 0


class Board:
    COLORS = {
        1: curses.COLOR_BLUE,
        2: curses.COLOR_GREEN,
        3: curses.COLOR_RED,
        4: curses.COLOR_MAGENTA,
        5: curses.COLOR_RED,
        6: curses.COLOR_CYAN,
        7: curses.COLOR_MAGENTA,
        8: curses.COLOR_WHITE,
    }

    def __init__(self, rows, cols, mines):
        self.rows = rows
        self.cols = cols
        self.total_mines = mines
        self.cells = [[Cell() for _ in range(cols)] for _ in range(rows)]
        self.state = State.PLAYING
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
                        1 for nr, nc in self._neighbors(r, c) if self.cells[nr][nc].mine
                    )

    def reveal(self, r, c):
        if self.first_move:
            self.first_move = False
            self.start_time = time.time()
            self._place_mines(r, c)

        cell = self.cells[r][c]
        if cell.flagged or cell.revealed:
            return
        cell.revealed = True

        if cell.mine:
            self.state = State.LOST
            self.end_time = time.time()
            self._reveal_all_mines()
            return

        if cell.adjacent == 0:
            for nr, nc in self._neighbors(r, c):
                if not self.cells[nr][nc].revealed and not self.cells[nr][nc].flagged:
                    self.reveal(nr, nc)

        self._check_win()

    def chord(self, r, c):
        """Reveal all unflagged neighbors when adjacent flag count matches."""
        cell = self.cells[r][c]
        if not cell.revealed or cell.adjacent == 0:
            return
        flag_count = sum(1 for nr, nc in self._neighbors(r, c) if self.cells[nr][nc].flagged)
        if flag_count == cell.adjacent:
            for nr, nc in self._neighbors(r, c):
                if not self.cells[nr][nc].flagged and not self.cells[nr][nc].revealed:
                    self.reveal(nr, nc)
                    if self.state != State.PLAYING:
                        return

    def toggle_flag(self, r, c):
        cell = self.cells[r][c]
        if cell.revealed:
            return
        if cell.flagged:
            cell.flagged = False
            self.flags -= 1
        else:
            cell.flagged = True
            self.flags += 1

    def _reveal_all_mines(self):
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
        self.state = State.WON
        self.end_time = time.time()

    def elapsed(self):
        if self.start_time is None:
            return 0
        end = self.end_time if self.end_time else time.time()
        return int(end - self.start_time)

    def mines_remaining(self):
        return self.total_mines - self.flags


DIFFICULTIES = {
    "b": ("Beginner", 9, 9, 10),
    "i": ("Intermediate", 16, 16, 40),
    "e": ("Expert", 16, 30, 99),
}

CELL_WIDTH = 3  # chars per cell


def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLUE, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.init_pair(4, curses.COLOR_MAGENTA, -1)
    curses.init_pair(5, curses.COLOR_RED, -1)
    curses.init_pair(6, curses.COLOR_CYAN, -1)
    curses.init_pair(7, curses.COLOR_YELLOW, -1)
    curses.init_pair(8, curses.COLOR_WHITE, -1)
    curses.init_pair(9, curses.COLOR_RED, -1)    # mine
    curses.init_pair(10, curses.COLOR_YELLOW, -1) # flag
    curses.init_pair(11, curses.COLOR_WHITE, -1)  # unrevealed
    curses.init_pair(12, curses.COLOR_BLACK, -1)  # revealed empty
    curses.init_pair(13, curses.COLOR_GREEN, -1)  # status bar win
    curses.init_pair(14, curses.COLOR_RED, -1)    # status bar lose


def draw_board(stdscr, board, cursor_r, cursor_c, offset_r, offset_c):
    stdscr.erase()
    height, width = stdscr.getmaxyx()

    # Header
    mines_str = f" Mines: {board.mines_remaining():3d} "
    time_str = f" Time: {board.elapsed():4d}s "
    if board.state == State.WON:
        status = " *** YOU WIN! *** "
        attr = curses.color_pair(13) | curses.A_BOLD
    elif board.state == State.LOST:
        status = " *** GAME OVER *** "
        attr = curses.color_pair(14) | curses.A_BOLD
    else:
        status = ""
        attr = curses.A_NORMAL

    header = mines_str + status + time_str
    try:
        stdscr.addstr(0, 0, header[:width - 1], attr)
    except curses.error:
        pass

    # Grid
    for r in range(board.rows):
        for c in range(board.cols):
            cell = board.cells[r][c]
            screen_r = offset_r + r
            screen_c = offset_c + c * CELL_WIDTH

            if screen_r < 1 or screen_r >= height - 2:
                continue
            if screen_c < 0 or screen_c + CELL_WIDTH > width:
                continue

            is_cursor = (r == cursor_r and c == cursor_c)

            if cell.revealed:
                if cell.mine:
                    ch = " * "
                    pair = curses.color_pair(9) | curses.A_BOLD
                elif cell.adjacent > 0:
                    ch = f" {cell.adjacent} "
                    pair = curses.color_pair(cell.adjacent)
                else:
                    ch = "   "
                    pair = curses.color_pair(12)
            elif cell.flagged:
                ch = " F "
                pair = curses.color_pair(10) | curses.A_BOLD
            else:
                ch = " . "
                pair = curses.color_pair(11)

            if is_cursor:
                pair = pair | curses.A_REVERSE

            try:
                stdscr.addstr(screen_r, screen_c, ch, pair)
            except curses.error:
                pass

    # Footer
    footer = " Arrow/HJKL:move  Space:reveal  F:flag  Enter:chord  N:new  Q:quit "
    try:
        stdscr.addstr(height - 1, 0, footer[:width - 1], curses.A_DIM)
    except curses.error:
        pass

    stdscr.refresh()


def select_difficulty(stdscr):
    stdscr.clear()
    lines = [
        "  MINESWEEPER",
        "",
        "  Select difficulty:",
        "    [B] Beginner     (9x9,   10 mines)",
        "    [I] Intermediate (16x16, 40 mines)",
        "    [E] Expert       (16x30, 99 mines)",
        "",
        "  Press B, I, or E",
    ]
    for i, line in enumerate(lines):
        try:
            stdscr.addstr(i + 2, 0, line)
        except curses.error:
            pass
    stdscr.refresh()

    while True:
        key = stdscr.getch()
        ch = chr(key).lower() if 0 <= key < 256 else ""
        if ch in DIFFICULTIES:
            return DIFFICULTIES[ch]
        if key in (ord("q"), ord("Q"), 27):
            return None


def game_loop(stdscr, rows, cols, mines):
    curses.curs_set(0)
    board = Board(rows, cols, mines)
    cursor_r, cursor_c = 0, 0

    height, width = stdscr.getmaxyx()
    offset_r = 1
    offset_c = max(0, (width - cols * CELL_WIDTH) // 2)

    while True:
        draw_board(stdscr, board, cursor_r, cursor_c, offset_r, offset_c)
        key = stdscr.getch()

        if key in (ord("q"), ord("Q")):
            return False

        if key in (ord("n"), ord("N")):
            return True

        if board.state != State.PLAYING:
            continue

        # Movement
        if key in (curses.KEY_UP, ord("k"), ord("K")):
            cursor_r = max(0, cursor_r - 1)
        elif key in (curses.KEY_DOWN, ord("j"), ord("J")):
            cursor_r = min(rows - 1, cursor_r + 1)
        elif key in (curses.KEY_LEFT, ord("h"), ord("H")):
            cursor_c = max(0, cursor_c - 1)
        elif key in (curses.KEY_RIGHT, ord("l"), ord("L")):
            cursor_c = min(cols - 1, cursor_c + 1)

        # Actions
        elif key in (ord(" "), ord("\n"), curses.KEY_ENTER):
            if key in (ord("\n"), curses.KEY_ENTER, 10, 13):
                board.chord(cursor_r, cursor_c)
            else:
                board.reveal(cursor_r, cursor_c)
        elif key in (ord("f"), ord("F")):
            board.toggle_flag(cursor_r, cursor_c)

    return False


def main(stdscr):
    init_colors()
    curses.curs_set(0)

    while True:
        result = select_difficulty(stdscr)
        if result is None:
            break
        name, rows, cols, mines = result
        replay = game_loop(stdscr, rows, cols, mines)
        if not replay:
            break


if __name__ == "__main__":
    curses.wrapper(main)
