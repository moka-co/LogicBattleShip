import pygame
import time

def run_gui(board_size, cnf, shot_history):
    """Pygame visualization of the board state with step-by-step animation."""
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
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Apply next shot if available (every 0.5 seconds)
        if shot_index < len(shot_history) and time.time() - last_update_time > 0.5:
            applied_shots.append(shot_history[shot_index])
            shot_index += 1
            last_update_time = time.time()
        
        screen.fill((255, 255, 255))
        
        # Build current state from applied shots
        hits = {(r, c) for r, c, hit in applied_shots if hit}
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
                elif (r, c) in all_ships and shot_index >= len(shot_history):
                    color = (0, 255, 0) # Ship (revealed at end)
                
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (0, 0, 0), rect, 1)
        
        pygame.display.flip()
        clock.tick(30)
        
    pygame.quit()
