from pysat.formula import CNF
from src.game import GameFactory
from src.utils import get_var

BOARD_SIZE = 10

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
    print(f"Board Size: {BOARD_SIZE}")
    game_factory = GameFactory(BOARD_SIZE)
    visualize_board(BOARD_SIZE, game_factory.cnf)
    return game_factory.cnf


if __name__ == "__main__":
    main()
