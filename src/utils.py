"""Utility functions for the Battleship SAT solver.

Provides variable encoding, ship cell computation, and adjacency/forbidden-cell
helpers used throughout the project.
"""


# Map a unique integer to each cell for each variable type:
# 0  = hidden (H_{i,j})
# 1  = ship piece (SP_{i,j})
# 2  = empty (E_{i,j})
# 3  = patrol boat horizontal placement (PB_{h,i,j})
# 4  = patrol boat vertical placement (PB_{v,i,j})
# 5  = submarine horizontal placement (SM_{h,i,j})
# 6  = submarine vertical placement (SM_{v,i,j})
# 7  = shot (Shot_{i,j})
# 8  = hit (Hit_{i,j})
# 9  = miss (Miss_{i,j})
# 10 = sunk patrol boat horizontal (Sunk_PB_{h,i,j})
# 11 = sunk patrol boat vertical   (Sunk_PB_{v,i,j})
# 12 = sunk submarine horizontal   (Sunk_SM_{h,i,j})
# 13 = sunk submarine vertical     (Sunk_SM_{v,i,j})
# 14 = battleship horizontal placement (BS_{h,i,j})
# 15 = battleship vertical placement (BS_{v,i,j})
# 16 = sunk battleship horizontal (Sunk_BS_{h,i,j})
# 17 = sunk battleship vertical   (Sunk_BS_{v,i,j})
# 18 = carrier placement (CR_{i,j})
# 19 = sunk carrier (Sunk_CR_{i,j})
def get_var(board_size, v_type, r, c):
    """Encodes a propositional variable as a unique positive integer for PySAT.

    Each (v_type, r, c) triple is mapped to a distinct integer so that the SAT
    solver can distinguish every variable on the board.

    Args:
        board_size: The side length of the square board (e.g. 10).
        v_type: The variable type index (see module-level comment for the mapping).
        r: Row index (0-based).
        c: Column index (0-based).

    Returns:
        A positive integer uniquely identifying this variable.
    """
    return v_type * (board_size * board_size) + r * board_size + c + 1

def _get_ship_cells(orientation, r, c, length):
    """Returns the list of (row, col) tuples occupied by a ship.

    Args:
        orientation: 'h' for horizontal, 'v' for vertical.
        r: Starting row index.
        c: Starting column index.
        length: Number of cells the ship occupies.

    Returns:
        A list of (row, col) tuples representing the ship's footprint.
    """
    if orientation == 'h':
        return [(r, c + k) for k in range(length)]
    else:
        return [(r + k, c) for k in range(length)]


def _get_forbidden_cells(board_size, cells):
    """Returns the set of cells adjacent (including diagonals) to a ship's footprint.

    Used both for random ship placement (to prevent overlapping buffers) and for
    encoding AllPartsSunk consequence constraints (surrounding cells must be empty).

    Args:
        board_size: The side length of the square board.
        cells: An iterable of (row, col) tuples representing the ship's cells.

    Returns:
        A set of (row, col) tuples that are within bounds and orthogonally or
        diagonally adjacent to at least one cell in ``cells`` (including the
        cells themselves).
    """
    forbidden = set()
    for (r, c) in cells:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < board_size and 0 <= nc < board_size:
                    forbidden.add((nr, nc))
    return forbidden
