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
    # Place ships physically on the board (chooses random valid positions)
    occupied = add_patrol_boat_to_board(cnf)
    occupied = add_submarine_to_board(cnf, occupied)
    # Add ship placement and adjacency constraints
    cnf = add_patrol_boat_constraints(cnf)
    cnf = add_submarine_constraints(cnf)
    # Per-ship non-adjacency constraints (replaces the old combined
    # add_non_adjacent_constraints; split per ship type to scale as more
    # ship types are added).
    cnf = add_patrol_boat_non_adjacent_constraints(BOARD_SIZE, cnf)
    cnf = add_submarine_non_adjacent_constraints(BOARD_SIZE, cnf)
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
