"""Entry point for the Battleship SAT Solver.

Parses command-line arguments and launches a simulation with the chosen
board size, shot count, strategy, and optional GUI.

Supports single-agent mode (agent vs hidden board) and multiplayer mode
(agent vs agent), where each agent has its own strategy.
"""

import argparse
from src.board import TruthBoardFactory, AgentBoardFactory
from src.game_logic import (
    SimulateSimpleGame,
    SimulateIntelligentGame,
    SimulateCheckerboardIntelligentGame,
)
from src.multiplayer import AgentVsAgent




def main():
    """Parses CLI arguments, builds the truth and agent boards, and runs the simulation."""
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
        choices=["simple", "intelligent", "checkerboard"],
        default="simple",
        help="Hunting strategy: 'simple' (random neighbors), 'intelligent' (directional hunting), or 'checkerboard' (checkerboard search + intelligent hunting) (default: simple)"
    )
    parser.add_argument(
        "--multiplayer",
        action="store_true",
        help="Enable agent vs agent multiplayer mode"
    )
    parser.add_argument(
        "--strategy2",
        choices=["simple", "intelligent", "checkerboard"],
        default=None,
        help="Strategy for Agent 2 in multiplayer mode (default: same as --strategy)"
    )
    args = parser.parse_args()

    print(f"Board Size: {args.size}")

    if args.multiplayer:
        strategy2 = args.strategy2 if args.strategy2 else args.strategy
        print(f"Mode: Multiplayer (Agent vs Agent)")
        print(f"Agent 1 Strategy: {args.strategy}")
        print(f"Agent 2 Strategy: {strategy2}")
        print()
        AgentVsAgent(
            board_size=args.size,
            max_shots=args.shots,
            strategy_name_1=args.strategy,
            strategy_name_2=strategy2,
            use_gui=args.gui,
        )
    else:
        print(f"Strategy: {args.strategy}")

        truth_board = TruthBoardFactory(args.size)
        agent_board = AgentBoardFactory(args.size)

        if args.strategy == "intelligent":
            SimulateIntelligentGame(args.size, args.shots, truth_board=truth_board, agent_board=agent_board, use_gui=args.gui)
        elif args.strategy == "checkerboard":
            SimulateCheckerboardIntelligentGame(args.size, args.shots, truth_board=truth_board, agent_board=agent_board, use_gui=args.gui)
        else:
            SimulateSimpleGame(args.size, args.shots, truth_board=truth_board, agent_board=agent_board, use_gui=args.gui)


if __name__ == "__main__":
    main()
