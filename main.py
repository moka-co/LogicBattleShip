import argparse
from src.game_logic import GameFactory, simulate_game

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
    
    return simulate_game(args.size, args.shots, game_factory)


if __name__ == "__main__":
    main()
