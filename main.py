from pysat.formula import CNF

from src.board import *
from src.ship_types import *
from src.ship_logic import *
from src.utils import *

BOARD_SIZE=10



def record_shot(cnf, r, c, was_hit):
    """Records a shot outcome by appending unit clauses to the CNF.

    This function is called dynamically during gameplay after each shot.
    The static constraints in `add_shot_hit_miss_constraints` will then
    propagate the consequences (e.g., Hit -> SP, Miss -> ¬SP) via the SAT solver.

    Args:
        cnf: the CNF knowledge base to update (mutated in place).
        r, c: the row and column of the shot tile.
        was_hit: True if the shot hit a ship part, False if it missed.
    """
    # Assert Shot_{r,c} (the tile has been shot)
    cnf.append([get_var(7, r, c)])

    if was_hit:
        # Assert Hit_{r,c}
        cnf.append([get_var(8, r, c)])
    else:
        # Assert Miss_{r,c}
        cnf.append([get_var(9, r, c)])


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
