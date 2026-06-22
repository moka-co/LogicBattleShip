"""Pygame GUI for the multiplayer (agent vs agent) Battleship mode.

This module provides a comprehensive visual replay of agent-vs-agent Battleship games
using Pygame. It displays two boards side by side, animates shots turn by turn, and
reveals the final game outcome.

**Board Layout:**
  - Left panel:  Agent 2's board (where Agent 1 shoots)
  - Right panel: Agent 1's board (where Agent 2 shoots)

**Visual Elements:**
  - Each board is a grid of cells color-coded by state (hit, miss, ship, unknown)
  - Agent names and strategies are displayed above each board
  - Shot counters show progress (shots fired, hits scored, total ship cells)
  - A progress indicator shows animation status during replay
  - A winner banner displays the final outcome

**Animation:**
  - Shots are replayed sequentially with a configurable delay between each shot
  - Shots are interleaved: Agent 1 shoots, then Agent 2 shoots, alternating
  - Once all shots are replayed, ship locations are revealed
  - The window remains open to allow inspection of the final board state

**Usage:**
  Call ``run_multiplayer_gui()`` with the board size, truth CNFs, shot histories,
  and optional strategy names. The function blocks until the user closes the window.

**Example:**
  >>> from src.multiplayer_gui import run_multiplayer_gui
  >>> run_multiplayer_gui(
  ...     board_size=10,
  ...     truth_cnf_1=agent1_truth_board.cnf,
  ...     truth_cnf_2=agent2_truth_board.cnf,
  ...     shot_history_1=[(0, 0, False), (1, 1, True), ...],
  ...     shot_history_2=[(2, 2, False), (3, 3, True), ...],
  ...     winner_label="Agent 1",
  ...     strategy_1="intelligent",
  ...     strategy_2="checkerboard"
  ... )
"""

import pygame
import time
from src.utils import get_var


# ── Visual constants ──────────────────────────────────────────────────────────
"""
Layout and rendering constants for the Pygame GUI.

CELL_SIZE:  Pixel width/height of each board cell (44px).
MARGIN:     Horizontal gap between the two boards (60px).
TOP_BAR:    Vertical space reserved for agent names, strategies, and shot counters (80px).
BOTTOM_BAR: Vertical space reserved for progress/winner message (60px).
BORDER:     Thickness of cell borders in pixels (2px).

Color palette (RGB tuples):
  C_BG:      Dark background for the window.
  C_GRID:    Grid line color (subtle, dark).
  C_UNKNOWN: Unshot cell color (dark blue-gray).
  C_SHIP:    Revealed ship cell color (green, shown only at end of game).
  C_HIT:     Hit cell color (red).
  C_MISS:    Miss cell color (blue).
  C_LABEL_1: Agent 1 accent color (light blue).
  C_LABEL_2: Agent 2 accent color (orange).
  C_TEXT:    General text color (light gray).
  C_WIN:     Winner banner color (gold).

Animation timing:
  SHOT_DELAY: Delay in seconds between consecutive shots during replay (0.35s).
  FPS:        Target frames per second for the Pygame event loop (60 FPS).
"""
CELL_SIZE      = 44
MARGIN         = 60
TOP_BAR        = 80
BOTTOM_BAR     = 60
BORDER         = 2

C_BG           = (15,  20,  35)
C_GRID         = (50,  60,  80)
C_UNKNOWN      = (40,  50,  70)
C_SHIP         = (60, 180,  75)
C_HIT          = (220,  50,  50)
C_MISS         = (50,  100, 200)
C_LABEL_1      = (100, 200, 255)
C_LABEL_2      = (255, 180,  80)
C_TEXT         = (220, 220, 220)
C_WIN          = (255, 215,   0)

SHOT_DELAY     = 0.35
FPS            = 60


def _get_ship_cells_from_cnf(board_size, cnf):
    """Extracts all ship cell locations from a truth-board CNF.

    Scans the CNF for unit clauses (single-literal clauses) that assert
    ShipPart variables (type 1). These represent cells that contain ship parts
    on the truth board.

    Args:
        board_size: The side length of the square board.
        cnf: A ``pysat.formula.CNF`` object representing a truth board
             (must have ship placements asserted as unit clauses).

    Returns:
        A set of (row, col) tuples representing all cells that contain ship parts.

    Example:
        >>> ships = _get_ship_cells_from_cnf(10, truth_board.cnf)
        >>> print(ships)
        {(0, 0), (0, 1), (2, 3), (2, 4), (2, 5), ...}
    """
    unit_clauses = {c[0] for c in cnf.clauses if len(c) == 1}
    return {(r, c) for r in range(board_size) for c in range(board_size)
            if get_var(board_size, 1, r, c) in unit_clauses}


def run_multiplayer_gui(board_size, truth_cnf_1, truth_cnf_2,
                        shot_history_1, shot_history_2,
                        winner_label=None, strategy_1=None, strategy_2=None):
    """Animates an agent-vs-agent Battleship game in a Pygame window.

    This function creates an interactive replay of a completed multiplayer game,
    displaying both agents' boards side by side and animating shots sequentially.

    **Board Interpretation:**
      - Left panel:  Agent 2's board (Agent 1 shoots here)
        - Shows hits/misses from Agent 1's shots
        - Reveals Agent 2's ship locations at game end
      - Right panel: Agent 1's board (Agent 2 shoots here)
        - Shows hits/misses from Agent 2's shots
        - Reveals Agent 1's ship locations at game end

    **Shot Interleaving:**
      Shots are replayed in turn order: Agent 1 shoots, then Agent 2 shoots,
      alternating. If one agent has more shots than the other (e.g., due to
      early victory), the remaining shots are played after the other agent's
      shots are exhausted.

    **Animation Flow:**
      1. Window opens with empty boards
      2. Shots are applied one at a time with SHOT_DELAY between each
      3. Progress indicator shows current shot number
      4. Once all shots are replayed, ship locations are revealed
      5. Winner banner displays the game outcome
      6. Window remains open for inspection; close to exit

    **Cell Color Coding:**
      - Red:       Hit cell (shot landed on a ship part)
      - Blue:      Miss cell (shot landed on empty water)
      - Green:     Ship cell (revealed only at end of game)
      - Dark gray: Unknown cell (not yet shot)

    Args:
        board_size (int):
            Side length of the square board (typically 10).

        truth_cnf_1 (pysat.formula.CNF):
            CNF of Agent 1's truth board. Must have ship placements asserted
            as unit clauses. Agent 2 shoots at this board.

        truth_cnf_2 (pysat.formula.CNF):
            CNF of Agent 2's truth board. Must have ship placements asserted
            as unit clauses. Agent 1 shoots at this board.

        shot_history_1 (list of tuples):
            Ordered list of Agent 1's shots: [(row, col, was_hit), ...].
            Each tuple contains:
              - row (int): Row index of the shot (0-based).
              - col (int): Column index of the shot (0-based).
              - was_hit (bool): True if the shot hit a ship part, False if miss.

        shot_history_2 (list of tuples):
            Ordered list of Agent 2's shots: [(row, col, was_hit), ...].
            Same format as shot_history_1.

        winner_label (str, optional):
            Name of the winning agent (e.g., "Agent 1", "Agent 2").
            If None, displays "Draw — no winner!". Default: None.

        strategy_1 (str, optional):
            Name of Agent 1's strategy (e.g., "intelligent", "checkerboard").
            Displayed below Agent 1's name. If None, strategy line is omitted.
            Default: None.

        strategy_2 (str, optional):
            Name of Agent 2's strategy. Displayed below Agent 2's name.
            If None, strategy line is omitted. Default: None.

    Returns:
        None. The function blocks until the user closes the Pygame window.

    Raises:
        pygame.error: If Pygame initialization fails or display mode cannot be set.

    Example:
        >>> from src.multiplayer_gui import run_multiplayer_gui
        >>> from src.board import TruthBoardFactory
        >>> board1 = TruthBoardFactory(10)
        >>> board2 = TruthBoardFactory(10)
        >>> shot_hist_1 = [(0, 0, False), (1, 1, True), (2, 2, False)]
        >>> shot_hist_2 = [(3, 3, False), (4, 4, True), (5, 5, False)]
        >>> run_multiplayer_gui(
        ...     board_size=10,
        ...     truth_cnf_1=board1.cnf,
        ...     truth_cnf_2=board2.cnf,
        ...     shot_history_1=shot_hist_1,
        ...     shot_history_2=shot_hist_2,
        ...     winner_label="Agent 1",
        ...     strategy_1="intelligent",
        ...     strategy_2="checkerboard"
        ... )

    **Implementation Notes:**
      - The function uses Pygame's event loop to handle window close events.
      - Shots are applied at a fixed interval (SHOT_DELAY) to allow visual inspection.
      - The FPS constant controls the event loop refresh rate (independent of shot timing).
      - Ship cells are extracted from the CNF using _get_ship_cells_from_cnf().
      - The _draw_board() helper renders a single board with current shot state.
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
        """Renders a single board grid with current shot state and ship locations.

        This nested function is called once per frame for each board (left and right).
        It iterates through all cells, determines their current state (hit, miss, ship,
        or unknown), and renders them with appropriate colors. A colored border is
        drawn around the entire board to distinguish the two agents.

        **Cell State Logic:**
          1. If the cell has been shot and hit → RED (C_HIT)
          2. If the cell has been shot and missed → BLUE (C_MISS)
          3. If the cell contains a ship AND reveal_ships is True → GREEN (C_SHIP)
          4. Otherwise → DARK GRAY (C_UNKNOWN)

        The reveal_ships flag is set to True only after all shots have been replayed,
        allowing the final board state to show ship locations.

        Args:
            origin_x (int):
                X-coordinate (in pixels) of the top-left corner of the board.
                Used to position the board horizontally on the screen.

            ship_cells (set of tuples):
                Set of (row, col) tuples representing all ship cell locations
                on this board. Extracted from the truth CNF.

            applied_shots (list of tuples):
                List of shots that have been applied so far: [(row, col, was_hit), ...].
                Only shots in this list are rendered; future shots are not shown.

            reveal_ships (bool):
                If True, ship cells are rendered in green (C_SHIP).
                If False, ship cells are rendered as unknown (C_UNKNOWN).
                Typically False during animation, True after all shots are replayed.

            accent (tuple):
                RGB color tuple for the board border. Used to distinguish agents:
                  - C_LABEL_1 (light blue) for Agent 1's board
                  - C_LABEL_2 (orange) for Agent 2's board

        Returns:
            None. Modifies the Pygame screen directly via pygame.draw.rect().

        **Rendering Details:**
          - Each cell is a CELL_SIZE × CELL_SIZE square
          - Cells are filled with their state color
          - A thin border (BORDER pixels) is drawn around each cell in C_GRID color
          - The entire board is surrounded by a 2-pixel border in the accent color
        """
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
