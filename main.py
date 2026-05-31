from pysat.formula import CNF

from src.board import *
from src.ship_types import *
from src.ship_logic import *
from src.utils import *

BOARD_SIZE=10


def main():
    print(f"Board Size: {BOARD_SIZE}")
    cnf = init_empty_board()
    # Place ships physically on the board and add their constraints
    pb_factory = PatrolBoatFactory(BOARD_SIZE)
    sm_factory = SubmarineFactory(BOARD_SIZE)
    occupied = pb_factory.build(cnf)
    occupied = sm_factory.build(cnf, occupied)
    # Add Shot/Hit/Miss static constraints (dynamic unit clauses are added later
    # via `record_shot` during gameplay). Now lives in src/ship_logic.py.
    cnf = add_shot_hit_miss_constraints(BOARD_SIZE, cnf)
    # Add Sinking Ships biconditionals and AllPartsSunk consequences
    # (also in src/ship_logic.py).
    cnf = add_sinking_constraints(BOARD_SIZE, cnf)
    cnf = add_all_parts_sunk_consequences(BOARD_SIZE, cnf)
    return cnf
    

if __name__ == "__main__":
    main()
