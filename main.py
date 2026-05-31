from pysat.formula import CNF

from src.board import *
from src.ships import *
from src.ship_logic import *
from src.utils import *

BOARD_SIZE=10



def add_sinking_constraints(cnf):
    """Adds the Sinking Ships biconditional constraints.

    A ship is "sunk" iff all of its parts have been Hit. We encode the biconditional
    Sunk_X_{o,i,j} <=> (Hit_{cell_1} AND Hit_{cell_2} AND ... AND Hit_{cell_n})
    for each ship type X (PatrolBoat, Submarine), orientation o (h, v), and starting
    position (i,j) where the ship fits on the board.

    The biconditional A <=> (B1 AND B2 AND ... AND Bn) decomposes into CNF as:
      - A -> Bk            (for each k): [-A, Bk]
      - (B1 ∧ ... ∧ Bn) -> A : [-B1, -B2, ..., -Bn, A]

    Variable types used:
      - Type 10 = Sunk_PB_{h,i,j}
      - Type 11 = Sunk_PB_{v,i,j}
      - Type 12 = Sunk_SM_{h,i,j}
      - Type 13 = Sunk_SM_{v,i,j}
    """

    # --- Sunk PatrolBoat horizontal: Sunk_PB_{h,i,j} <=> (Hit_{i,j} ∧ Hit_{i,j+1}) ---
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE - 1):  # needs c+1 in bounds
            sunk = get_var(10, r, c)
            h1 = get_var(8, r, c)
            h2 = get_var(8, r, c + 1)
            # Sunk -> Hit_k
            cnf.append([-sunk, h1])
            cnf.append([-sunk, h2])
            # (Hit_1 ∧ Hit_2) -> Sunk
            cnf.append([-h1, -h2, sunk])

    # --- Sunk PatrolBoat vertical: Sunk_PB_{v,i,j} <=> (Hit_{i,j} ∧ Hit_{i+1,j}) ---
    for r in range(BOARD_SIZE - 1):  # needs r+1 in bounds
        for c in range(BOARD_SIZE):
            sunk = get_var(11, r, c)
            h1 = get_var(8, r, c)
            h2 = get_var(8, r + 1, c)
            cnf.append([-sunk, h1])
            cnf.append([-sunk, h2])
            cnf.append([-h1, -h2, sunk])

    # --- Sunk Submarine horizontal: Sunk_SM_{h,i,j} <=> (Hit_{i,j} ∧ Hit_{i,j+1} ∧ Hit_{i,j+2}) ---
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE - 2):  # needs c+2 in bounds
            sunk = get_var(12, r, c)
            h1 = get_var(8, r, c)
            h2 = get_var(8, r, c + 1)
            h3 = get_var(8, r, c + 2)
            cnf.append([-sunk, h1])
            cnf.append([-sunk, h2])
            cnf.append([-sunk, h3])
            cnf.append([-h1, -h2, -h3, sunk])

    # --- Sunk Submarine vertical: Sunk_SM_{v,i,j} <=> (Hit_{i,j} ∧ Hit_{i+1,j} ∧ Hit_{i+2,j}) ---
    for r in range(BOARD_SIZE - 2):  # needs r+2 in bounds
        for c in range(BOARD_SIZE):
            sunk = get_var(13, r, c)
            h1 = get_var(8, r, c)
            h2 = get_var(8, r + 1, c)
            h3 = get_var(8, r + 2, c)
            cnf.append([-sunk, h1])
            cnf.append([-sunk, h2])
            cnf.append([-sunk, h3])
            cnf.append([-h1, -h2, -h3, sunk])

    return cnf


def add_all_parts_sunk_consequences(cnf):
    """Adds the AllPartsSunk consequence constraints.

    Once a ship is fully sunk, the surrounding tiles (adjacent + diagonals) are
    known to be empty (¬SP). Each consequence Sunk_X -> (¬SP_a ∧ ¬SP_b ∧ ...) is
    encoded as one binary clause per surrounding cell: [-Sunk_X, -SP_a].

    Surrounding cells per README:
      - PB horizontal at (i,j):   (i, j-1), (i, j+2), (i-1, j), (i-1, j+1),
                                  (i+1, j), (i+1, j+1)
      - PB vertical   at (i,j):   (i-1, j), (i+2, j), (i, j-1), (i+1, j-1),
                                  (i, j+1), (i+1, j+1)
      - SM horizontal at (i,j):   (i, j-1), (i, j+3),
                                  (i-1, j), (i-1, j+1), (i-1, j+2),
                                  (i+1, j), (i+1, j+1), (i+1, j+2)
      - SM vertical   at (i,j):   (i-1, j), (i+3, j),
                                  (i, j-1), (i+1, j-1), (i+2, j-1),
                                  (i, j+1), (i+1, j+1), (i+2, j+1)

    All surrounding cells are guarded by board-bound checks.
    """

    def _add_neg_sp(sunk_var, neighbors):
        """Helper: for each (r,c) in `neighbors` that is in bounds, append [-sunk, -SP_{r,c}]."""
        for (nr, nc) in neighbors:
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                cnf.append([-sunk_var, -get_var(1, nr, nc)])

    # --- Sunk PB horizontal: Sunk_PB_{h,i,j} -> 6 surrounding cells are not SP ---
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE - 1):
            sunk = get_var(10, r, c)
            neighbors = [
                (r,     c - 1),  # left of first part
                (r,     c + 2),  # right of second part
                (r - 1, c),      # above first part
                (r - 1, c + 1),  # above second part
                (r + 1, c),      # below first part
                (r + 1, c + 1),  # below second part
            ]
            _add_neg_sp(sunk, neighbors)

    # --- Sunk PB vertical: Sunk_PB_{v,i,j} -> 6 surrounding cells are not SP ---
    for r in range(BOARD_SIZE - 1):
        for c in range(BOARD_SIZE):
            sunk = get_var(11, r, c)
            neighbors = [
                (r - 1, c),      # above first part
                (r + 2, c),      # below second part
                (r,     c - 1),  # left of first part
                (r + 1, c - 1),  # left of second part
                (r,     c + 1),  # right of first part
                (r + 1, c + 1),  # right of second part
            ]
            _add_neg_sp(sunk, neighbors)

    # --- Sunk SM horizontal: Sunk_SM_{h,i,j} -> 8 surrounding cells are not SP ---
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE - 2):
            sunk = get_var(12, r, c)
            neighbors = [
                (r,     c - 1),  # left of first part
                (r,     c + 3),  # right of third part
                (r - 1, c),      # above first part
                (r - 1, c + 1),  # above second part
                (r - 1, c + 2),  # above third part
                (r + 1, c),      # below first part
                (r + 1, c + 1),  # below second part
                (r + 1, c + 2),  # below third part
            ]
            _add_neg_sp(sunk, neighbors)

    # --- Sunk SM vertical: Sunk_SM_{v,i,j} -> 8 surrounding cells are not SP ---
    for r in range(BOARD_SIZE - 2):
        for c in range(BOARD_SIZE):
            sunk = get_var(13, r, c)
            neighbors = [
                (r - 1, c),      # above first part
                (r + 3, c),      # below third part
                (r,     c - 1),  # left of first part
                (r + 1, c - 1),  # left of second part
                (r + 2, c - 1),  # left of third part
                (r,     c + 1),  # right of first part
                (r + 1, c + 1),  # right of second part
                (r + 2, c + 1),  # right of third part
            ]
            _add_neg_sp(sunk, neighbors)

    return cnf


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
    # Add Sinking Ships biconditionals and AllPartsSunk consequences.
    cnf = add_sinking_constraints(cnf)
    cnf = add_all_parts_sunk_consequences(cnf)
    return cnf
    

if __name__ == "__main__":
    main()
