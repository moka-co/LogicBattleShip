"""Multiplayer (agent vs agent) mode for the Battleship SAT Solver.

This module implements a complete agent-vs-agent Battleship game where two
independent agents compete to sink each other's ships. Each agent has:
  - A truth board with randomly placed ships (opponent shoots here)
  - An agent board (knowledge base) for reasoning about opponent's board
  - A strategy for selecting targets (simple, intelligent, or checkerboard)

**Game Flow:**
  1. Two truth boards are created with randomly placed ships
  2. Two agent boards are created (empty, no ships placed)
  3. Agents alternate turns, each firing one shot per turn
  4. After each shot, the agent's KB is updated with the result
  5. Game ends when one agent sinks all opponent ships or max shots reached
  6. Final statistics and board visualizations are printed
  7. Optionally, a Pygame GUI replay is launched

**Agent Strategies:**
  - "simple":       Random neighbors of open hits; random fallback
  - "intelligent":  SAT-guided forced/consistent targets; random fallback
  - "checkerboard": Checkerboard discovery + SAT-guided hunting

**Example Usage:**
  >>> from src.multiplayer import AgentVsAgent
  >>> game = AgentVsAgent(
  ...     board_size=10,
  ...     max_shots=100,
  ...     strategy_name_1="intelligent",
  ...     strategy_name_2="checkerboard",
  ...     use_gui=True
  ... )

**Output:**
  - Console output with turn-by-turn shot results
  - Final summary with hit rates and accuracy
  - Text-based board visualizations
  - Optional Pygame GUI replay of the game
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
    """Orchestrates a complete agent-vs-agent Battleship game.

    This class manages the entire game lifecycle: board initialization, turn
    alternation, shot recording, win detection, and optional GUI replay.

    **Game Mechanics:**
      - Each agent has a truth board (opponent shoots here) and an agent board (KB)
      - Agents alternate turns; each turn consists of one shot
      - A shot is recorded in the opponent's agent board (updating their KB)
      - The game ends when one agent sinks all opponent ships or max shots reached
      - If both agents exhaust shots without a winner, the one with more hits wins

    **Attributes:**
        board_size (int):
            Side length of the square board (typically 10).

        max_shots (int):
            Maximum number of shots each agent is allowed to fire.
            Game ends after max_shots turns per agent or when a winner is found.

        use_gui (bool):
            If True, launches a Pygame GUI replay after the game completes.

        strategy_name_1 (str):
            Name of Agent 1's strategy ('simple', 'intelligent', 'checkerboard').

        strategy_name_2 (str):
            Name of Agent 2's strategy ('simple', 'intelligent', 'checkerboard').

        truth_board_1 (TruthBoardFactory):
            Agent 1's truth board with randomly placed ships.
            Agent 2 shoots at this board.

        agent_board_1 (AgentBoardFactory):
            Agent 1's knowledge base (no ships placed).
            Agent 1 reasons over this board to decide where to shoot.

        strategy_1 (BattleshipStrategy):
            Agent 1's target-selection strategy instance.

        shots_taken_1 (set):
            Set of (row, col) cells Agent 1 has already shot.

        shot_history_1 (list):
            Ordered list of Agent 1's shots: [(row, col, was_hit), ...].

        truth_board_2, agent_board_2, strategy_2, shots_taken_2, shot_history_2:
            Analogous attributes for Agent 2.

        ship_cells_1 (set):
            Set of (row, col) cells containing Agent 1's ships.
            Used to detect when all ships are sunk.

        ship_cells_2 (set):
            Set of (row, col) cells containing Agent 2's ships.

    **Initialization:**
      The constructor immediately calls ``_run()`` to execute the game loop.
      No separate method call is needed; the game completes during instantiation.
    """

    def __init__(self, board_size, max_shots, strategy_name_1, strategy_name_2, use_gui=False):
        """Initializes the game and immediately executes the complete game loop.

        This constructor performs all setup and runs the game to completion.
        The game loop alternates between agents until a winner is found or
        max_shots is reached.

        **Initialization Steps:**
          1. Store configuration parameters
          2. Create truth boards for both agents (with random ship placements)
          3. Create agent boards for both agents (empty, no ships)
          4. Instantiate strategy objects for both agents
          5. Precompute ship cell locations for win detection
          6. Print initial game configuration
          7. Call _run() to execute the game loop

        **Game Execution:**
          The _run() method handles all turn logic, shot recording, and win detection.
          After _run() completes, _print_summary() displays final statistics and
          optionally launches the Pygame GUI via _launch_gui().

        Args:
            board_size (int):
                Side length of the square board (typically 10).
                Must be >= 5 to accommodate all ship types.

            max_shots (int):
                Maximum number of shots each agent is allowed to fire.
                Game ends after max_shots turns per agent or when a winner is found.
                Typical value: 100 for a 10×10 board.

            strategy_name_1 (str):
                Strategy for Agent 1. Must be one of:
                  - "simple":       Random neighbors of open hits
                  - "intelligent":  SAT-guided forced/consistent targets
                  - "checkerboard": Checkerboard discovery + SAT hunting

            strategy_name_2 (str):
                Strategy for Agent 2. Same options as strategy_name_1.

            use_gui (bool, optional):
                If True, launches a Pygame GUI replay after the game completes.
                The GUI displays both boards side by side with animated shot replay.
                Default: False.

        Raises:
            KeyError: If strategy_name_1 or strategy_name_2 is not in STRATEGY_MAP.
            RuntimeError: If ship placement fails (no valid placement exists).

        Example:
            >>> game = AgentVsAgent(
            ...     board_size=10,
            ...     max_shots=100,
            ...     strategy_name_1="intelligent",
            ...     strategy_name_2="checkerboard",
            ...     use_gui=True
            ... )
            # Game runs immediately; output printed to console
            # GUI launches after game completes
        """
        self.board_size = board_size
        self.max_shots = max_shots
        self.use_gui = use_gui
        self.strategy_name_1 = strategy_name_1
        self.strategy_name_2 = strategy_name_2

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
        """Executes a single turn for one agent: select target, fire, record result.

        This method encapsulates the complete turn logic for one agent:
          1. Query the strategy for a target cell
          2. Check if the target is a hit or miss on the opponent's truth board
          3. Record the shot in the agent's KB (updating its knowledge)
          4. Append the result to the shot history
          5. Print the result to console
          6. Check if all opponent ships are now sunk

        **Shot Recording:**
          The shot is recorded in the agent's own agent_board (KB), not the
          opponent's. This allows the agent to reason about the opponent's board
          based on its own observations.

        **Win Detection:**
          After each shot, the method checks if all opponent ship cells have been
          hit. If so, the agent has won and the method returns True.

        Args:
            agent_name (str):
                Display name for console output (e.g., "Agent 1", "Agent 2").

            strategy (BattleshipStrategy):
                The agent's strategy instance (simple, intelligent, or checkerboard).
                Its get_hunt_candidates() method is called to select the target.

            agent_board (AgentBoardFactory):
                The agent's knowledge base (CNF). The shot result is recorded here
                via record_shot(), updating the agent's beliefs.

            opponent_truth_board (TruthBoardFactory):
                The opponent's truth board. Used to determine if the shot is a hit
                or miss via is_ship_part().

            shots_taken (set):
                Set of (row, col) cells the agent has already shot.
                Mutated in place: the new target is added to this set.

            shot_history (list):
                Ordered list of the agent's shots: [(row, col, was_hit), ...].
                Mutated in place: the new shot result is appended.

            opponent_ship_cells (set):
                Set of (row, col) cells containing the opponent's ships.
                Used to detect if all opponent ships are now sunk.

        Returns:
            bool:
                True if the agent just sank all opponent ships (game-winning shot).
                False otherwise (game continues).

        **Side Effects:**
          - Prints shot result to console (HIT or miss)
          - Mutates shots_taken (adds new target)
          - Mutates shot_history (appends new result)
          - Mutates agent_board.cnf (records shot via record_shot())

        **Example:**
          >>> won = game._agent_turn(
          ...     "Agent 1",
          ...     game.strategy_1,
          ...     game.agent_board_1,
          ...     game.truth_board_2,
          ...     game.shots_taken_1,
          ...     game.shot_history_1,
          ...     game.ship_cells_2
          ... )
          # Prints: "  Agent 1 fires at (3,5) — HIT" or "  Agent 1 fires at (3,5) — miss"
          # Returns: True if all of Agent 2's ships are now sunk, False otherwise
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
        """Executes the main game loop: alternating turns until a winner or max shots.

        **Game Loop Logic:**
          1. For each turn from 1 to max_shots:
             a. Agent 1 takes a turn (shoots at Agent 2's board)
             b. If Agent 1 sinks all ships → Agent 1 wins, game ends
             c. Agent 2 takes a turn (shoots at Agent 1's board)
             d. If Agent 2 sinks all ships → Agent 2 wins, game ends
          2. If max_shots is reached without a winner → draw

        **Win Conditions:**
          - Agent 1 wins if all cells in ship_cells_2 are hit
          - Agent 2 wins if all cells in ship_cells_1 are hit
          - Draw if both agents exhaust max_shots without sinking all opponent ships

        **Output:**
          - Prints turn number at the start of each turn
          - Prints each shot result (HIT or miss) via _agent_turn()
          - Prints winner announcement or draw message
          - Calls _print_summary() to display final statistics
          - Optionally calls _launch_gui() to show Pygame replay

        **Post-Game Actions:**
          After the game ends (win or draw), the method:
          1. Sets self._winner_label to the winner name or None for draw
          2. Calls _print_summary() to display final board states and statistics
          3. Calls _launch_gui() if use_gui is True

        Returns:
            None. The method returns after the game ends.

        **Example Output:**
          ── Turn 1 ──
            Agent 1 fires at (5,5) — miss
            Agent 2 fires at (3,3) — HIT
          ── Turn 2 ──
            Agent 1 fires at (5,6) — HIT
            Agent 2 fires at (3,4) — HIT

          Agent 1 wins in 42 shots!

          Final Summary:
             Agent 1: 20/20 hits in 42 shots (accuracy: 47.6%)
             Agent 2: 18/20 hits in 38 shots (accuracy: 47.4%)
        """
        self._winner_label = None

        for turn in range(1, self.max_shots + 1):
            print(f"── Turn {turn} ──")

            # Agent 1 shoots at Agent 2's board
            if self._agent_turn(
                "Agent 1", self.strategy_1, self.agent_board_1,
                self.truth_board_2, self.shots_taken_1, self.shot_history_1,
                self.ship_cells_2
            ):
                print(f"\nAgent 1 wins in {len(self.shot_history_1)} shots!")
                self._winner_label = "Agent 1"
                self._print_summary()
                if self.use_gui:
                    self._launch_gui()
                return

            # Agent 2 shoots at Agent 1's board
            if self._agent_turn(
                "Agent 2", self.strategy_2, self.agent_board_2,
                self.truth_board_1, self.shots_taken_2, self.shot_history_2,
                self.ship_cells_1
            ):
                print(f"\nAgent 2 wins in {len(self.shot_history_2)} shots!")
                self._winner_label = "Agent 2"
                self._print_summary()
                if self.use_gui:
                    self._launch_gui()
                return

        print(f"\nMax shots ({self.max_shots}) reached — no winner!")
        self._print_summary()
        if self.use_gui:
            self._launch_gui()

    def _print_summary(self):
        """Prints final game statistics and board visualizations.

        **Output Includes:**
          1. Hit counts and accuracy for each agent
          2. Text-based board visualizations for both truth boards
          3. Legend: [H] = hit, [S] = ship (unrevealed), [0] = miss, [ ] = unknown

        **Statistics Displayed:**
          - Hits scored / total opponent ship cells
          - Total shots fired
          - Accuracy percentage (hits / shots)

        **Board Visualizations:**
          - Agent 2's board (where Agent 1 shot)
          - Agent 1's board (where Agent 2 shot)
          - Each cell shows the final state after all shots

        **Example Output:**
          Final Summary:
             Agent 1: 20/20 hits in 42 shots (accuracy: 47.6%)
             Agent 2: 18/20 hits in 38 shots (accuracy: 47.4%)

             Agent 2's board (Agent 1 shoots here):
          [H][H][0][ ][ ][ ][ ][ ][ ][ ]
          [H][H][0][ ][ ][ ][ ][ ][ ][ ]
          [0][0][0][ ][ ][ ][ ][ ][ ][ ]
          ...

        Returns:
            None. Output is printed to console.
        """
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

    def _launch_gui(self):
        """Launches the Pygame GUI to replay the completed game.

        **GUI Features:**
          - Displays both boards side by side
          - Animates shots sequentially with visual feedback
          - Shows agent names, strategies, and shot statistics
          - Reveals ship locations after all shots are replayed
          - Displays winner banner or draw message
          - Remains open for inspection; close window to exit

        **Board Layout:**
          - Left panel:  Agent 2's board (Agent 1 shoots here)
          - Right panel: Agent 1's board (Agent 2 shoots here)

        **Animation:**
          - Shots are replayed in turn order (Agent 1, then Agent 2, alternating)
          - Each shot is displayed with a 0.35-second delay
          - Progress indicator shows current shot number
          - Once all shots are replayed, ship locations are revealed in green

        **Data Passed to GUI:**
          - board_size: The board dimensions
          - truth_cnf_1, truth_cnf_2: Truth boards (for ship location extraction)
          - shot_history_1, shot_history_2: Complete shot histories
          - winner_label: Name of winning agent or None for draw
          - strategy_1, strategy_2: Strategy names for display

        Returns:
            None. The function blocks until the user closes the Pygame window.

        **Example:**
          # Called automatically after game ends if use_gui=True
          >>> game = AgentVsAgent(..., use_gui=True)
          # After game completes, GUI launches automatically
        """
        from src.multiplayer_gui import run_multiplayer_gui
        run_multiplayer_gui(
            board_size=self.board_size,
            truth_cnf_1=self.truth_board_1.cnf,
            truth_cnf_2=self.truth_board_2.cnf,
            shot_history_1=self.shot_history_1,
            shot_history_2=self.shot_history_2,
            winner_label=self._winner_label,
            strategy_1=self.strategy_name_1,
            strategy_2=self.strategy_name_2,
        )
