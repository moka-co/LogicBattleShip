"""Pygame GUI for the multiplayer (agent vs agent) Battleship mode.

Displays two boards side by side and animates the shot history turn by turn.
Left board  = Agent 2's board (Agent 1 shoots here).
Right board = Agent 1's board (Agent 2 shoots here).
"""

import pygame
import time
from src.utils import get_var


# ── Visual constants ──────────────────────────────────────────────────────────
CELL_SIZE      = 44
MARGIN         = 60          # gap between the two boards
TOP_BAR        = 80          # height reserved for title / turn info
BOTTOM_BAR     = 60          # height reserved for summary line
BORDER         = 2           # cell border thickness

# Colours
C_BG           = (15,  20,  35)
C_GRID         = (50,  60,  80)
C_UNKNOWN      = (40,  50,  70)
C_SHIP         = (60, 180,  75)   # revealed ship (end of game)
C_HIT          = (220,  50,  50)  # hit cell
C_MISS         = (50,  100, 200)  # miss cell
C_LABEL_1      = (100, 200, 255)  # Agent 1 accent colour
C_LABEL_2      = (255, 180,  80)  # Agent 2 accent colour
C_TEXT         = (220, 220, 220)
C_WIN          = (255, 215,   0)  # gold for winner banner

SHOT_DELAY     = 0.35        # seconds between shots in the animation
FPS            = 60


def _get_ship_cells_from_cnf(board_size, cnf):
    """Returns the set of all ship cells asserted in a truth-board CNF."""
    unit_clauses = {c[0] for c in cnf.clauses if len(c) == 1}
    return {(r, c) for r in range(board_size) for c in range(board_size)
            if get_var(board_size, 1, r, c) in unit_clauses}


def run_multiplayer_gui(board_size, truth_cnf_1, truth_cnf_2,
                        shot_history_1, shot_history_2,
                        winner_label=None, strategy_1=None, strategy_2=None):
    """Animates an agent-vs-agent game in a Pygame window.

    The left panel shows Agent 2's board (where Agent 1 shoots).
    The right panel shows Agent 1's board (where Agent 2 shoots).
    Shots are interleaved turn by turn (one from each agent per turn).

    Args:
        board_size:     Side length of the square board.
        truth_cnf_1:    CNF of Agent 1's truth board (Agent 2 shoots here).
        truth_cnf_2:    CNF of Agent 2's truth board (Agent 1 shoots here).
        shot_history_1: List of (row, col, was_hit) for Agent 1's shots.
        shot_history_2: List of (row, col, was_hit) for Agent 2's shots.
        winner_label:   String such as "Agent 1" or "Agent 2" or None for draw.
        strategy_1:     Strategy name for Agent 1 (optional).
        strategy_2:     Strategy name for Agent 2 (optional).
    """
    pygame.init()
    pygame.display.set_caption("Battleship — Agent vs Agent")

    board_px   = board_size * CELL_SIZE
    win_width  = board_px * 2 + MARGIN + 40
    win_height = board_px + TOP_BAR + BOTTOM_BAR

    screen = pygame.display.set_mode((win_width, win_height))
    clock  = pygame.time.Clock()

    try:
        font_large = pygame.font.SysFont("consolas", 22, bold=True)
        font_small = pygame.font.SysFont("consolas", 15)
        font_strategy = pygame.font.SysFont("consolas", 13)
        font_win   = pygame.font.SysFont("consolas", 28, bold=True)
    except Exception:
        font_large = pygame.font.Font(None, 26)
        font_small = pygame.font.Font(None, 19)
        font_strategy = pygame.font.Font(None, 17)
        font_win   = pygame.font.Font(None, 34)

    # Pre-compute ship locations (revealed at end)
    ships_1 = _get_ship_cells_from_cnf(board_size, truth_cnf_1)
    ships_2 = _get_ship_cells_from_cnf(board_size, truth_cnf_2)

    # Board origins (top-left corner of the grid)
    left_origin_x  = 20
    right_origin_x = 20 + board_px + MARGIN
    origin_y       = TOP_BAR

    # Interleave shots: turn k → shot_history_1[k] then shot_history_2[k]
    max_turns = max(len(shot_history_1), len(shot_history_2))
    interleaved = []   # list of (agent_idx 1|2, r, c, was_hit)
    for k in range(max_turns):
        if k < len(shot_history_1):
            r, c, h = shot_history_1[k]
            interleaved.append((1, r, c, h))
        if k < len(shot_history_2):
            r, c, h = shot_history_2[k]
            interleaved.append((2, r, c, h))

    applied_1 = []
    applied_2 = []

    shot_index     = 0
    last_shot_time = time.time()
    animation_done = False
    running        = True

    def _draw_board(origin_x, ship_cells, applied_shots, reveal_ships, accent):
        """Draws one board at the given x origin."""
        hits   = {(r, c) for r, c, h in applied_shots if h}
        misses = {(r, c) for r, c, h in applied_shots if not h}

        for row in range(board_size):
            for col in range(board_size):
                rx = origin_x + col * CELL_SIZE
                ry = origin_y + row * CELL_SIZE
                rect = pygame.Rect(rx, ry, CELL_SIZE, CELL_SIZE)

                if (row, col) in hits:
                    colour = C_HIT
                elif (row, col) in misses:
                    colour = C_MISS
                elif reveal_ships and (row, col) in ship_cells:
                    colour = C_SHIP
                else:
                    colour = C_UNKNOWN

                pygame.draw.rect(screen, colour, rect)
                pygame.draw.rect(screen, C_GRID, rect, BORDER)

        border_rect = pygame.Rect(origin_x, origin_y, board_px, board_px)
        pygame.draw.rect(screen, accent, border_rect, 2)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Advance animation
        if not animation_done and shot_index < len(interleaved):
            if time.time() - last_shot_time >= SHOT_DELAY:
                agent, r, c, h = interleaved[shot_index]
                if agent == 1:
                    applied_1.append((r, c, h))
                else:
                    applied_2.append((r, c, h))
                shot_index += 1
                last_shot_time = time.time()
        elif shot_index >= len(interleaved):
            animation_done = True

        # ── Draw ──────────────────────────────────────────────────────────────
        screen.fill(C_BG)

        reveal = animation_done

        # Left board: Agent 2's ships, Agent 1 shoots here
        _draw_board(left_origin_x,  ships_2, applied_1, reveal, C_LABEL_1)
        # Right board: Agent 1's ships, Agent 2 shoots here
        _draw_board(right_origin_x, ships_1, applied_2, reveal, C_LABEL_2)

        # ── Labels above boards ───────────────────────────────────────────────
        lbl1 = font_large.render("Agent 1 shoots", True, C_LABEL_1)
        lbl2 = font_large.render("Agent 2 shoots", True, C_LABEL_2)
        screen.blit(lbl1, (left_origin_x, 8))
        screen.blit(lbl2, (right_origin_x, 8))

        sub1 = font_small.render("(Agent 2's board)", True, C_TEXT)
        sub2 = font_small.render("(Agent 1's board)", True, C_TEXT)
        screen.blit(sub1, (left_origin_x, 28))
        screen.blit(sub2, (right_origin_x, 28))

        # Strategy labels
        strat1_text = f"Strategy: {strategy_1}" if strategy_1 else ""
        strat2_text = f"Strategy: {strategy_2}" if strategy_2 else ""
        strat1 = font_strategy.render(strat1_text, True, C_LABEL_1)
        strat2 = font_strategy.render(strat2_text, True, C_LABEL_2)
        screen.blit(strat1, (left_origin_x, 46))
        screen.blit(strat2, (right_origin_x, 46))

        # Shot counters
        hits_1 = sum(1 for _, _, h in applied_1 if h)
        hits_2 = sum(1 for _, _, h in applied_2 if h)
        cnt1 = font_small.render(
            f"Shots: {len(applied_1)}  Hits: {hits_1}/{len(ships_2)}", True, C_LABEL_1)
        cnt2 = font_small.render(
            f"Shots: {len(applied_2)}  Hits: {hits_2}/{len(ships_1)}", True, C_LABEL_2)
        screen.blit(cnt1, (left_origin_x, 62))
        screen.blit(cnt2, (right_origin_x, 62))

        # ── Bottom bar ────────────────────────────────────────────────────────
        bottom_y = origin_y + board_px + 15
        if animation_done:
            if winner_label:
                win_surf = font_win.render(f"{winner_label} wins!", True, C_WIN)
            else:
                win_surf = font_win.render("Draw — no winner!", True, C_WIN)
            wx = (win_width - win_surf.get_width()) // 2
            screen.blit(win_surf, (wx, bottom_y))
        else:
            progress = font_small.render(
                f"Replaying shot {shot_index} / {len(interleaved)}", True, C_TEXT)
            px = (win_width - progress.get_width()) // 2
            screen.blit(progress, (px, bottom_y))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
