"""Minesweeper — Pygame version (Pygbag-compatible for web deployment)."""

import random
import time
from enum import Enum

import pygame

# ---------------------------------------------------------------------------
# Game logic (unchanged from curses version)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Difficulty presets
# ---------------------------------------------------------------------------

DIFFICULTIES = [
    ("Beginner",     9,  9,  10),
    ("Intermediate", 16, 16, 40),
    ("Expert",       16, 30, 99),
]

# ---------------------------------------------------------------------------
# Colours & sizing
# ---------------------------------------------------------------------------

BG          = (30,  30,  35)
HEADER_BG   = (20,  20,  25)
CELL_HIDDEN = (70,  75,  90)
CELL_REVEAL = (45,  48,  58)
CELL_BORDER = (100, 105, 120)
CELL_HOVER  = (90,  95, 115)
MINE_COL    = (220,  60,  60)
FLAG_COL    = (240, 180,  40)
WIN_COL     = (80,  200, 120)
LOSE_COL    = (220,  60,  60)
BTN_NORMAL  = (60,  65,  80)
BTN_HOVER   = (80,  85, 105)
BTN_ACTIVE  = (50,  55,  70)
TEXT_MAIN   = (220, 222, 230)
TEXT_DIM    = (130, 135, 155)

# Number colours matching classic Minesweeper
NUMBER_COLORS = {
    1: (80,  120, 220),
    2: (80,  180,  80),
    3: (220,  70,  70),
    4: (60,   60, 160),
    5: (160,  40,  40),
    6: (60,  160, 160),
    7: (160,  60, 160),
    8: (130, 130, 130),
}

CELL_SIZE   = 36
HEADER_H    = 64
PADDING     = 16
BTN_H       = 36
BTN_W       = 140
BTN_RADIUS  = 8
CELL_RADIUS = 4


# ---------------------------------------------------------------------------
# Pygame renderer
# ---------------------------------------------------------------------------

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Minesweeper")

        self.screen = None
        self.font_num   = None
        self.font_ui    = None
        self.font_title = None
        self.font_small = None

        self.board  = None
        self.diff_idx = 0       # selected difficulty index on menu
        self.scene  = "menu"    # "menu" | "game"
        self.hover_cell  = None
        self.hover_btn   = None

        self._init_display(DIFFICULTIES[0])

    # ------------------------------------------------------------------
    def _init_display(self, difficulty):
        _, rows, cols, _ = difficulty
        w = max(cols * CELL_SIZE + PADDING * 2, 420)
        h = rows * CELL_SIZE + HEADER_H + PADDING * 2
        self.screen = pygame.display.set_mode((w, h))
        self.font_num   = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_ui    = pygame.font.SysFont("Arial", 16)
        self.font_title = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 13)

    def _start_game(self, diff_idx):
        self.diff_idx = diff_idx
        name, rows, cols, mines = DIFFICULTIES[diff_idx]
        self._init_display(DIFFICULTIES[diff_idx])
        self.board = Board(rows, cols, mines)
        self.scene = "game"
        self.hover_cell = None

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    def _board_origin(self):
        cols = self.board.cols
        w = self.screen.get_width()
        ox = (w - cols * CELL_SIZE) // 2
        oy = HEADER_H
        return ox, oy

    def _cell_at(self, mx, my):
        ox, oy = self._board_origin()
        c = (mx - ox) // CELL_SIZE
        r = (my - oy) // CELL_SIZE
        if 0 <= r < self.board.rows and 0 <= c < self.board.cols:
            return r, c
        return None

    def _cell_rect(self, r, c):
        ox, oy = self._board_origin()
        return pygame.Rect(ox + c * CELL_SIZE, oy + r * CELL_SIZE, CELL_SIZE, CELL_SIZE)

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_round_rect(self, surf, color, rect, radius, border=0, border_color=None):
        pygame.draw.rect(surf, color, rect, border_radius=radius)
        if border and border_color:
            pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)

    def _draw_button(self, label, rect, hover):
        color = BTN_HOVER if hover else BTN_NORMAL
        self._draw_round_rect(self.screen, color, rect, BTN_RADIUS)
        txt = self.font_ui.render(label, True, TEXT_MAIN)
        self.screen.blit(txt, txt.get_rect(center=rect.center))

    # ------------------------------------------------------------------
    # Menu scene
    # ------------------------------------------------------------------

    def _draw_menu(self):
        w, h = self.screen.get_size()
        self.screen.fill(BG)

        title = self.font_title.render("💣  Minesweeper", True, TEXT_MAIN)
        self.screen.blit(title, title.get_rect(center=(w // 2, 80)))

        sub = self.font_ui.render("Select difficulty", True, TEXT_DIM)
        self.screen.blit(sub, sub.get_rect(center=(w // 2, 120)))

        self._menu_btn_rects = []
        for i, (name, rows, cols, mines) in enumerate(DIFFICULTIES):
            rect = pygame.Rect(0, 0, BTN_W + 60, BTN_H + 4)
            rect.center = (w // 2, 165 + i * 56)
            hover = (self.hover_btn == i)
            color = BTN_HOVER if hover else BTN_NORMAL
            if i == self.diff_idx:
                color = (55, 100, 160)
            self._draw_round_rect(self.screen, color, rect, BTN_RADIUS)
            label = f"{name}  ({rows}×{cols}, {mines} mines)"
            txt = self.font_ui.render(label, True, TEXT_MAIN)
            self.screen.blit(txt, txt.get_rect(center=rect.center))
            self._menu_btn_rects.append(rect)

        # Play button
        play_rect = pygame.Rect(0, 0, BTN_W, BTN_H + 4)
        play_rect.center = (w // 2, 165 + len(DIFFICULTIES) * 56 + 10)
        hover = (self.hover_btn == len(DIFFICULTIES))
        self._draw_button("▶  Play", play_rect, hover)
        self._menu_btn_rects.append(play_rect)

        pygame.display.flip()

    # ------------------------------------------------------------------
    # Game scene
    # ------------------------------------------------------------------

    def _draw_header(self):
        w = self.screen.get_width()
        pygame.draw.rect(self.screen, HEADER_BG, (0, 0, w, HEADER_H))

        # Mines remaining
        mine_txt = self.font_title.render(f"💣 {self.board.mines_remaining():3d}", True, TEXT_MAIN)
        self.screen.blit(mine_txt, (PADDING, HEADER_H // 2 - mine_txt.get_height() // 2))

        # Timer
        time_txt = self.font_title.render(f"⏱ {self.board.elapsed():4d}s", True, TEXT_MAIN)
        self.screen.blit(time_txt, (w - time_txt.get_width() - PADDING,
                                    HEADER_H // 2 - time_txt.get_height() // 2))

        # Status / new game button
        if self.board.state == State.WON:
            label = "🎉 You Win!  New Game"
            col = WIN_COL
        elif self.board.state == State.LOST:
            label = "💥 Game Over  New Game"
            col = LOSE_COL
        else:
            label = "☰ Menu"
            col = TEXT_DIM

        btn_w = 180
        self._menu_game_btn = pygame.Rect(w // 2 - btn_w // 2,
                                          HEADER_H // 2 - BTN_H // 2,
                                          btn_w, BTN_H)
        hover = (self.hover_btn == "menu")
        bg = BTN_HOVER if hover else BTN_NORMAL
        self._draw_round_rect(self.screen, bg, self._menu_game_btn, BTN_RADIUS)
        txt = self.font_ui.render(label, True, col)
        self.screen.blit(txt, txt.get_rect(center=self._menu_game_btn.center))

    def _draw_cells(self):
        for r in range(self.board.rows):
            for c in range(self.board.cols):
                cell = self.board.cells[r][c]
                rect = self._cell_rect(r, c)
                inner = rect.inflate(-3, -3)
                is_hover = (self.hover_cell == (r, c))

                if cell.revealed:
                    if cell.mine:
                        self._draw_round_rect(self.screen, MINE_COL, inner, CELL_RADIUS)
                        t = self.font_num.render("*", True, (255, 255, 255))
                        self.screen.blit(t, t.get_rect(center=inner.center))
                    elif cell.adjacent > 0:
                        self._draw_round_rect(self.screen, CELL_REVEAL, inner, CELL_RADIUS)
                        col = NUMBER_COLORS.get(cell.adjacent, TEXT_MAIN)
                        t = self.font_num.render(str(cell.adjacent), True, col)
                        self.screen.blit(t, t.get_rect(center=inner.center))
                    else:
                        self._draw_round_rect(self.screen, CELL_REVEAL, inner, CELL_RADIUS)
                elif cell.flagged:
                    bg = CELL_HOVER if is_hover else CELL_HIDDEN
                    self._draw_round_rect(self.screen, bg, inner, CELL_RADIUS,
                                          border=1, border_color=CELL_BORDER)
                    t = self.font_num.render("🚩", True, FLAG_COL)
                    self.screen.blit(t, t.get_rect(center=inner.center))
                else:
                    bg = CELL_HOVER if is_hover else CELL_HIDDEN
                    self._draw_round_rect(self.screen, bg, inner, CELL_RADIUS,
                                          border=1, border_color=CELL_BORDER)

    def _draw_game(self):
        self.screen.fill(BG)
        self._draw_header()
        self._draw_cells()

        # Controls hint at bottom
        hint = "Left click: reveal   Right click: flag   Middle / chord: auto-reveal"
        t = self.font_small.render(hint, True, TEXT_DIM)
        w, h = self.screen.get_size()
        self.screen.blit(t, t.get_rect(center=(w // 2, h - 10)))

        pygame.display.flip()

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _handle_menu_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hover_btn = None
            for i, rect in enumerate(self._menu_btn_rects):
                if rect.collidepoint(mx, my):
                    self.hover_btn = i
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, rect in enumerate(self._menu_btn_rects):
                if rect.collidepoint(mx, my):
                    if i < len(DIFFICULTIES):
                        self.diff_idx = i
                    else:
                        # Play button
                        self._start_game(self.diff_idx)
                    break

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_b):
                self.diff_idx = 0
            elif event.key in (pygame.K_2, pygame.K_i):
                self.diff_idx = 1
            elif event.key in (pygame.K_3, pygame.K_e):
                self.diff_idx = 2
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._start_game(self.diff_idx)

    def _handle_game_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hover_cell = self._cell_at(mx, my)
            self.hover_btn = "menu" if self._menu_game_btn.collidepoint(mx, my) else None

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos

            # Header button
            if self._menu_game_btn.collidepoint(mx, my):
                if self.board.state != State.PLAYING:
                    self._start_game(self.diff_idx)
                else:
                    self.scene = "menu"
                return

            rc = self._cell_at(mx, my)
            if rc is None or self.board.state != State.PLAYING:
                return
            r, c = rc

            if event.button == 1:
                self.board.reveal(r, c)
            elif event.button == 3:
                self.board.toggle_flag(r, c)
            elif event.button == 2:
                self.board.chord(r, c)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.scene = "menu"
            elif event.key == pygame.K_n:
                self._start_game(self.diff_idx)

    # ------------------------------------------------------------------
    # Main loop (Pygbag-compatible async)
    # ------------------------------------------------------------------

    async def run(self):
        import asyncio
        clock = pygame.time.Clock()
        # Draw menu first so it's visible before any events
        self._menu_btn_rects = []
        self._menu_game_btn = pygame.Rect(0, 0, 0, 0)

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                if self.scene == "menu":
                    self._handle_menu_event(event)
                else:
                    self._handle_game_event(event)

            if self.scene == "menu":
                self._draw_menu()
            else:
                self._draw_game()

            clock.tick(30)
            await asyncio.sleep(0)  # yield to browser event loop (Pygbag requirement)

        pygame.quit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

import asyncio

async def main():
    game = Game()
    await game.run()

asyncio.run(main())
