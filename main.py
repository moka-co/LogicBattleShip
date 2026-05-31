from pysat.formula import CNF
from src.game import GameFactory

BOARD_SIZE=10

def main():
    print(f"Board Size: {BOARD_SIZE}")
    game_factory = GameFactory(BOARD_SIZE)
    return game_factory.cnf


if __name__ == "__main__":
    main()
