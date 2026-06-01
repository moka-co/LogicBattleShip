from pysat.formula import CNF
from src.utils import get_var
from src.ship_types import *
from src.ship_logic import *


def init_empty_board(board_size = 10):
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
    """
    A factory class responsible for initializing the Battleship game state.

    This class sets up the initial CNF formula by placing ships on the board,
    applying static game rules (shot/hit/miss constraints), and configuring
    the logic for sinking ships and their consequences.
    """
    def __init__(self, board_size):
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
    def __init__(self, board_size):
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
