"""Pygame-based GUI visualization for the Battleship game.

Provides a text-based board printer and an animated Pygame window that replays
the shot history step-by-step.
"""

import pygame
import time
from src.utils import get_var


def visualize_board(board_size, cnf):
    """Prints a text representation of the board to stdout.

    Legend:
      - ``[H]`` — Hit.
      - ``[S]`` — Ship part (unrevealed).
      - ``[0]`` — Miss.
      - ``[ ]`` — Unknown / empty.

    Args:
        board_size: The side length of the square board.
        cnf: The CNF whose unit clauses determine cell states.
    """
    print("Board Visualization:")
    # Create a set of unit clauses for faster lookup
    unit_clauses = {c[0] for c in cnf.clauses if len(c) == 1}
    
    for r in range(board_size):
        row_str = ""
        for c in range(board_size):
            # Check for Hit (8), Ship Part (1), or Miss (9)
            if get_var(board_size, 8, r, c) in unit_clauses:
                row_str += "[H]"
            elif get_var(board_size, 1, r, c) in unit_clauses:
                row_str += "[S]"
            elif get_var(board_size, 9, r, c) in unit_clauses:
                row_str += "[0]"
            else:
                row_str += "[ ]"
        print(row_str)

def run_gui(board_size, cnf, shot_history):
    """Launches a Pygame window that animates the shot history step-by-step.

    Each shot is replayed at 0.5-second intervals. Hits are shown in red,
    misses in blue, and remaining ship cells are revealed in green once all
    ships are sunk or all shots have been replayed.

    Args:
        board_size: The side length of the square board.
        cnf: The truth board's CNF (used to identify ship locations).
        shot_history: Ordered list of ``(row, col, was_hit)`` tuples.
    """
    pygame.init()
    cell_size = 40
    screen = pygame.display.set_mode((board_size * cell_size, board_size * cell_size))
    pygame.display.set_caption("Battleship Animation")
    
    from src.utils import get_var
    
    # Identify all ship locations from the CNF
    unit_clauses = {c[0] for c in cnf.clauses if len(c) == 1}
    all_ships = {(r, c) for r in range(board_size) for c in range(board_size) 
                 if get_var(board_size, 1, r, c) in unit_clauses}
    
    # We track shots applied to the board incrementally
    applied_shots = []
    
    clock = pygame.time.Clock()
    running = True
    shot_index = 0
    last_update_time = time.time()
    game_over = False
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Build current state from applied shots
        hits = {(r, c) for r, c, hit in applied_shots if hit}
        
        # Check if all ships are sunk
        if all_ships and all_ships.issubset(hits):
            game_over = True
        
        # Apply next shot if available (every 0.5 seconds)
        if not game_over and shot_index < len(shot_history) and time.time() - last_update_time > 0.5:
            applied_shots.append(shot_history[shot_index])
            shot_index += 1
            last_update_time = time.time()
        
        screen.fill((255, 255, 255))
        
        misses = {(r, c) for r, c, hit in applied_shots if not hit}
        
        for r in range(board_size):
            for c in range(board_size):
                rect = pygame.Rect(c * cell_size, r * cell_size, cell_size, cell_size)
                color = (200, 200, 200)
                
                # Logic: Show ships (green) if animation finished or if hit
                if (r, c) in hits:
                    color = (255, 0, 0) # Hit
                elif (r, c) in misses:
                    color = (0, 0, 255) # Miss
                elif (r, c) in all_ships and (game_over or shot_index >= len(shot_history)):
                    color = (0, 255, 0) # Ship (revealed at end or if sunk)
                
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (0, 0, 0), rect, 1)
        
        pygame.display.flip()
        clock.tick(30)
        
    pygame.quit()
