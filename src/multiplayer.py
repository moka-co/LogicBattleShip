"""Multiplayer (agent vs agent) mode for the Battleship SAT Solver.

Provides the AgentVsAgent class which runs a game where two agents with
independently configured strategies take turns shooting at each other's boards.
"""

from src.board import TruthBoardFactory, AgentBoardFactory
from src.game_logic import (
    BattleshipSimpleRandomStrategy,
    BattleshipIntelligentRandomStrategy,
    BattleshipCheckerboardIntelligentStrategy,
    record_shot,
    is_ship_part,
    visualize_board,
)
from src.utils import get_var


STRATEGY_MAP = {
    "simple": BattleshipSimpleRandomStrategy,
    "intelligent": BattleshipIntelligentRandomStrategy,
    "checkerboard": BattleshipCheckerboardIntelligentStrategy,
}


class AgentVsAgent:
    """Runs a multiplayer game where two agents take turns shooting each other.

    Each agent has:
      - A truth board with randomly placed ships (the opponent shoots at this).
      - An agent board (KB) that it reasons over to decide where to shoot.
      - A strategy that selects targets.

    The game alternates turns. The first agent to sink all of the opponent's
    ships wins. If both agents exhaust their shots, the one with more hits wins.

    Attributes:
        board_size: Side length of the square board.
        max_shots: Maximum shots per agent.
        use_gui: Whether to launch Pygame visualization after the game.
    """

    def __init__(self, board_size, max_shots, strategy_name_1, strategy_name_2, use_gui=False):
        """Initializes and immediately runs the agent-vs-agent game.

        Args:
            board_size: The side length of the square board.
            max_shots: Maximum number of shots each agent may fire.
            strategy_name_1: Strategy name for Agent 1 ('simple', 'intelligent', 'checkerboard').
            strategy_name_2: Strategy name for Agent 2.
            use_gui: If True, launch Pygame visualization after the game.
        """
        self.board_size = board_size
        self.max_shots = max_shots
        self.use_gui = use_gui

        # Agent 1: has its own ships (truth board) and its own KB (agent board)
        # Agent 1 shoots at Agent 2's truth board, reasoning with its own agent board
        self.truth_board_1 = TruthBoardFactory(board_size)
        self.agent_board_1 = AgentBoardFactory(board_size)
        self.strategy_1 = STRATEGY_MAP[strategy_name_1]()
        self.shots_taken_1 = set()
        self.shot_history_1 = []

        # Agent 2: same structure
        self.truth_board_2 = TruthBoardFactory(board_size)
        self.agent_board_2 = AgentBoardFactory(board_size)
        self.strategy_2 = STRATEGY_MAP[strategy_name_2]()
        self.shots_taken_2 = set()
        self.shot_history_2 = []

        # Precompute ship cells for each player
        self.ship_cells_1 = self._get_all_ship_cells(self.truth_board_1)
        self.ship_cells_2 = self._get_all_ship_cells(self.truth_board_2)

        print(f"Agent vs Agent — Board: {board_size}x{board_size}, Max shots: {max_shots}")
        print(f"   Agent 1 strategy: {strategy_name_1} ({len(self.ship_cells_1)} ship cells)")
        print(f"   Agent 2 strategy: {strategy_name_2} ({len(self.ship_cells_2)} ship cells)")
        print()

        self._run()

    def _get_all_ship_cells(self, truth_board):
        """Returns the set of all ship cells on a truth board.

        Args:
            truth_board: A ``TruthBoardFactory`` instance.

        Returns:
            Set of (row, col) tuples.
        """
        unit_clauses = {clause[0] for clause in truth_board.cnf.clauses if len(clause) == 1}
        return {(r, c) for r in range(self.board_size) for c in range(self.board_size)
                if get_var(self.board_size, 1, r, c) in unit_clauses}

    def _all_sunk(self, ship_cells, shot_history):
        """Checks whether all ship cells have been hit.

        Args:
            ship_cells: Set of (row, col) ship cells.
            shot_history: List of (row, col, was_hit) tuples.

        Returns:
            True if every ship cell has been hit.
        """
        hit_cells = {(r, c) for r, c, was_hit in shot_history if was_hit}
        return ship_cells.issubset(hit_cells)

    def _agent_turn(self, agent_name, strategy, agent_board, opponent_truth_board,
                    shots_taken, shot_history, opponent_ship_cells):
        """Executes a single turn for one agent.

        Args:
            agent_name: Display name (e.g. "Agent 1").
            strategy: The agent's ``BattleshipStrategy`` instance.
            agent_board: The agent's ``AgentBoardFactory`` (its KB).
            opponent_truth_board: The opponent's ``TruthBoardFactory`` (to check hits).
            shots_taken: The agent's set of already-shot cells (mutated in place).
            shot_history: The agent's shot history list (mutated in place).
            opponent_ship_cells: Set of the opponent's ship cells.

        Returns:
            True if the agent just sank all opponent ships, False otherwise.
        """
        target, active = strategy.get_hunt_candidates(
            self.board_size, agent_board.cnf, shots_taken
        )
        if not active or target is None:
            return False

        shots_taken.add(target)
        r, c = target
        was_hit = is_ship_part(self.board_size, opponent_truth_board.cnf, r, c)
        record_shot(self.board_size, agent_board.cnf, r, c, was_hit)
        shot_history.append((r, c, was_hit))

        status = "HIT" if was_hit else "miss"
        print(f"  {agent_name} fires at ({r},{c}) — {status}")

        if was_hit and self._all_sunk(opponent_ship_cells, shot_history):
            return True
        return False

    def _run(self):
        """Runs the alternating-turn game loop until a winner is found or shots are exhausted."""
        for turn in range(1, self.max_shots + 1):
            print(f"── Turn {turn} ──")

            # Agent 1 shoots at Agent 2's board
            if self._agent_turn(
                "Agent 1", self.strategy_1, self.agent_board_1,
                self.truth_board_2, self.shots_taken_1, self.shot_history_1,
                self.ship_cells_2
            ):
                print(f"\nAgent 1 wins in {len(self.shot_history_1)} shots!")
                self._print_summary()
                return

            # Agent 2 shoots at Agent 1's board
            if self._agent_turn(
                "Agent 2", self.strategy_2, self.agent_board_2,
                self.truth_board_1, self.shots_taken_2, self.shot_history_2,
                self.ship_cells_1
            ):
                print(f"\nAgent 2 wins in {len(self.shot_history_2)} shots!")
                self._print_summary()
                return

        print(f"\nMax shots ({self.max_shots}) reached — no winner!")
        self._print_summary()

    def _print_summary(self):
        """Prints final statistics for both agents."""
        hits_1 = len([h for h in self.shot_history_1 if h[2]])
        hits_2 = len([h for h in self.shot_history_2 if h[2]])

        print(f"\nFinal Summary:")
        print(f"   Agent 1: {hits_1}/{len(self.ship_cells_2)} hits in {len(self.shot_history_1)} shots "
              f"(accuracy: {hits_1/max(len(self.shot_history_1),1)*100:.1f}%)")
        print(f"   Agent 2: {hits_2}/{len(self.ship_cells_1)} hits in {len(self.shot_history_2)} shots "
              f"(accuracy: {hits_2/max(len(self.shot_history_2),1)*100:.1f}%)")

        print(f"\n   Agent 2's board (Agent 1 shoots here):")
        visualize_board(self.board_size, self.truth_board_2.cnf)
        print(f"\n   Agent 1's board (Agent 2 shoots here):")
        visualize_board(self.board_size, self.truth_board_1.cnf)
