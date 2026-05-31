import pygame
import time

def run_gui(board_size, cnf, shot_history):
    """Pygame visualization of the board state with step-by-step animation."""
    pygame.init()
    cell_size = 40
    screen = pygame.display.set_mode((board_size * cell_size, board_size * cell_size))
    pygame.display.set_caption("Battleship Animation")
    
    from src.utils import get_var
    
    # We track shots applied to the board incrementally
    applied_shots = []
    
    clock = pygame.time.Clock()
    running = True
    shot_index = 0
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Apply next shot if available
        if shot_index < len(shot_history):
            applied_shots.append(shot_history[shot_index])
            shot_index += 1
            time.sleep(0.5) # Animation delay
        
        screen.fill((255, 255, 255))
        
        # Build current state from applied shots
        hits = {(r, c) for r, c, hit in applied_shots if hit}
        misses = {(r, c) for r, c, hit in applied_shots if not hit}
        
        # Only show ships if they were hit
        ships = { (r, c) for r, c, hit in applied_shots if hit }
        
        for r in range(board_size):
            for c in range(board_size):
                rect = pygame.Rect(c * cell_size, r * cell_size, cell_size, cell_size)
                color = (200, 200, 200)
                
                if (r, c) in hits:
                    color = (255, 0, 0) # Hit
                elif (r, c) in misses:
                    color = (0, 0, 255) # Miss
                
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (0, 0, 0), rect, 1)
        
        pygame.display.flip()
        clock.tick(30)
        
    pygame.quit()
