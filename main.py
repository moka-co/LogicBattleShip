import argparse
import random
from pysat.formula import CNF
from src.game import GameFactory, record_shot
from src.utils import get_var

def visualize_board(board_size, cnf):
    """Prints a simple text representation of the board."""
    print("Board Visualization:")
    # Create a set of unit clauses for faster lookup
    unit_clauses = {c[0] for c in cnf.clauses if len(c) == 1}
    
    for r in range(board_size):
        row_str = ""
        for c in range(board_size):
            # Check for Hit (8), Miss (9), or Ship Part (1)
            if get_var(board_size, 8, r, c) in unit_clauses:
                row_str += "[H]" # Hit
            elif get_var(board_size, 9, r, c) in unit_clauses:
                row_str += "[M]"
            elif get_var(board_size, 1, r, c) in unit_clauses:
                row_str += "[S]"
            else:
                row_str += "[ ]"
        print(row_str)

def main():
    parser = argparse.ArgumentParser(description="Battleship SAT Solver")
    parser.add_argument(
        "--size", 
        type=int, 
        default=10, 
        help="The size of the square board (default: 10)"
    )
    parser.add_argument(
        "--shots",
        type=int,
        default=5,
        help="Number of random shots to simulate (default: 5)"
    )
    args = parser.parse_args()
    
    print(f"Board Size: {args.size}")
    game_factory = GameFactory(args.size)
    
    # Visualize board before shoots 

    visualize_board(args.size, game_factory.cnf)
    # Simulate random shots
    for _ in range(args.shots):
        r = random.randint(0, args.size - 1)
        c = random.randint(0, args.size - 1)
        # Simulate a hit/miss randomly for demonstration
        was_hit = random.choice([True, False])
        record_shot(args.size, game_factory.cnf, r, c, was_hit)
        print(f"Shot at ({r}, {c}) - Hit: {was_hit}")

    visualize_board(args.size, game_factory.cnf)
    return game_factory.cnf


if __name__ == "__main__":
    main()
