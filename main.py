import argparse
from src.game_logic import TruthBoardFactory, AgentBoardFactory, simulate_game, simulate_game_intelligent

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
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Enable Pygame GUI visualization"
    )
    parser.add_argument(
        "--strategy",
        choices=["simple", "intelligent"],
        default="simple",
        help="Hunting strategy: 'simple' (random neighbors) or 'intelligent' (directional hunting) (default: simple)"
    )
    args = parser.parse_args()
    
    print(f"Board Size: {args.size}")
    print(f"Strategy: {args.strategy}")
    
    truth_board = TruthBoardFactory(args.size)
    agent_board = AgentBoardFactory(args.size)
    
    if args.strategy == "intelligent":
        return simulate_game_intelligent(args.size, args.shots, truth_board=truth_board, agent_board=agent_board, use_gui=args.gui)
    else:
        return simulate_game(args.size, args.shots, truth_board=truth_board, agent_board=agent_board, use_gui=args.gui)


if __name__ == "__main__":
    main()
