"""Board initialization and factory classes for the Battleship SAT solver.

Provides helpers to create the base CNF (ShipPart / Empty exclusivity) and two
factory classes:
  - ``TruthBoardFactory``: builds the fully-specified truth board with randomly
    placed ships, used to answer "was this shot a hit?" queries.
  - ``AgentBoardFactory``: builds the agent's knowledge base *without* placing
    ships, so the agent must deduce ship locations via SAT reasoning.
"""

from pysat.formula import CNF
from src.utils import get_var
from src.ship_types import *
from src.ship_logic import *


def init_empty_board(board_size=10):
    """Creates a base CNF encoding the ShipPart / Empty exclusivity for every cell.

    For each cell (r, c) on the board, two clauses are added:
      - ``[SP, E]``   — at least one of ShipPart or Empty is true.
      - ``[-SP, -E]`` — at most one of ShipPart or Empty is true.

    Together these enforce that every cell is *exactly one* of {ShipPart, Empty}.

    Args:
        board_size: The side length of the square board (default 10).

    Returns:
        A ``pysat.formula.CNF`` object containing the base exclusivity clauses.
    """
    board_cnf = CNF()

    for r in range(board_size):
        for c in range(board_size):
            sp = get_var(board_size,1, r, c)
            e = get_var(board_size, 2, r, c)

            # A tile either contains a ShipPart or is Empty (exclusive)
            board_cnf.append([sp, e])
            board_cnf.append([-sp, -e])
    
    return board_cnf



class TruthBoardFactory:
    """Factory that builds the *truth board* — the fully-specified game state.

    The truth board contains:
      1. Randomly placed ships (PatrolBoat, Submarine, Battleship, Carrier) with
         non-adjacency buffers enforced.
      2. Ship placement and exactly-one constraints.
      3. Shot / Hit / Miss static constraints.
      4. Sinking biconditionals and AllPartsSunk consequence constraints.

    The resulting ``self.cnf`` is used by the simulation loop to answer
    ``is_ship_part`` queries (i.e. whether a shot is a hit or miss).

    Attributes:
        board_size: Side length of the square board.
        occupied: Set of (row, col) cells occupied by ships and their adjacency
            buffers, used during placement to prevent overlaps.
        cnf: The fully-built ``pysat.formula.CNF`` knowledge base.
    """

    def __init__(self, board_size):
        """Initializes the truth board by placing ships and adding all constraints.

        Args:
            board_size: The side length of the square board.
        """
        self.board_size = board_size
        self.occupied = set()
        self.cnf = init_empty_board(self.board_size)
        
        # Place ships physically on the board and add their constraints
        pb_factory = PatrolBoatFactory(self.board_size)
        sm_factory = SubmarineFactory(self.board_size)
        bs_factory = BattleshipFactory(self.board_size)
        cr_factory = CarrierFactory(self.board_size)
        self.occupied = pb_factory.build(self.cnf, self.occupied)
        self.occupied = sm_factory.build(self.cnf, self.occupied)
        self.occupied = bs_factory.build(self.cnf, self.occupied)
        self.occupied = cr_factory.build(self.cnf, self.occupied)
        
        # Add Shot/Hit/Miss static constraints (dynamic unit clauses are added later
        # via `record_shot` during gameplay).
        self.cnf = add_shot_hit_miss_constraints(self.board_size, self.cnf)
        
        # Add Sinking Ships biconditionals and AllPartsSunk consequences
        self.cnf = add_sinking_constraints(self.board_size, self.cnf)
        self.cnf = add_all_parts_sunk_consequences(self.board_size, self.cnf)

class AgentBoardFactory:
    """Factory that builds the *agent board* — the agent's knowledge base.

    Unlike ``TruthBoardFactory``, no ships are physically placed. Instead, only
    the structural constraints are added (placement implications, exactly-one,
    non-adjacency, shot/hit/miss, sinking, and AllPartsSunk consequences).
    The agent deduces ship locations by recording shots and querying the SAT
    solver.

    Attributes:
        board_size: Side length of the square board.
        cnf: The ``pysat.formula.CNF`` knowledge base the agent reasons over.
    """

    def __init__(self, board_size):
        """Initializes the agent board with all structural constraints but no ship placements.

        Args:
            board_size: The side length of the square board.
        """
        self.board_size = board_size
        self.cnf = init_empty_board(self.board_size)
        
        # Add ship constraints (but don't place actual ships - agent must deduce locations)
        from src.ship_types import add_patrol_boat_constraints, add_patrol_boat_non_adjacent_constraints
        from src.ship_types import add_submarine_constraints, add_submarine_non_adjacent_constraints
        from src.ship_types import add_battleship_constraints, add_battleship_non_adjacent_constraints
        from src.ship_types import add_carrier_constraints, add_carrier_non_adjacent_constraints
        
        add_patrol_boat_constraints(self.board_size, self.cnf)
        add_patrol_boat_non_adjacent_constraints(self.board_size, self.cnf)
        add_submarine_constraints(self.board_size, self.cnf)
        add_submarine_non_adjacent_constraints(self.board_size, self.cnf)
        add_battleship_constraints(self.board_size, self.cnf)
        add_battleship_non_adjacent_constraints(self.board_size, self.cnf)
        add_carrier_constraints(self.board_size, self.cnf)
        add_carrier_non_adjacent_constraints(self.board_size, self.cnf)
        
        # Add Shot/Hit/Miss static constraints (dynamic unit clauses are added later
        # via `record_shot` during gameplay).
        self.cnf = add_shot_hit_miss_constraints(self.board_size, self.cnf)
        
        # Add Sinking Ships biconditionals and AllPartsSunk consequences
        self.cnf = add_sinking_constraints(self.board_size, self.cnf)
        self.cnf = add_all_parts_sunk_consequences(self.board_size, self.cnf)
