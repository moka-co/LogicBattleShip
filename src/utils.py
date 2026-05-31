


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
def get_var(board_size, v_type, r, c):
    return v_type * (board_size * board_size) + r * board_size + c + 1

def _get_ship_cells(orientation, r, c, length):
    """Returns the list of cells occupied by a ship of given length/orientation starting at (r,c)."""
    if orientation == 'h':
        return [(r, c + k) for k in range(length)]
    else:
        return [(r + k, c) for k in range(length)]


def _get_forbidden_cells(board_size, cells):
    """Returns the set of cells that would be adjacent (including diagonals) to a ship occupying `cells`.
    Used to enforce non-adjacent ship placement when randomly placing ships."""
    forbidden = set()
    for (r, c) in cells:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < board_size and 0 <= nc < board_size:
                    forbidden.add((nr, nc))
    return forbidden
