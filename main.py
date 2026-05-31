import argparse
from pysat.formula import CNF
from src.game import GameFactory
from src.utils import get_var

def visualize_board(board_size, cnf):
    """Prints a simple text representation of the board."""
    print("Board Visualization:")
    # Create a set of unit clauses for faster lookup
    unit_clauses = {c[0] for c in cnf.clauses if len(c) == 1}
    
    for r in range(board_size):
        row_str = ""
        for c in range(board_size):
            # Assuming variable type 1 represents Ship Part (SP)
            var = get_var(board_size, 1, r, c)
            row_str += "[S]" if var in unit_clauses else "[ ]"
        print(row_str)

def main():
    parser = argparse.ArgumentParser(description="Battleship SAT Solver")
    parser.add_argument(
        "--size", 
        type=int, 
        default=10, 
        help="The size of the square board (default: 10)"
    )
    args = parser.parse_args()
    
    print(f"Board Size: {args.size}")
    game_factory = GameFactory(args.size)
    visualize_board(args.size, game_factory.cnf)
    return game_factory.cnf


if __name__ == "__main__":
    main()
