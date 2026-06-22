"""Ship type definitions, placement, and constraint functions.

Each ship type (PatrolBoat, Submarine, Battleship, Carrier) has:
  - A ``add_<ship>_to_board`` function that randomly places one instance.
  - A ``add_<ship>_constraints`` function that encodes placement implications
    and exactly-one constraints.
  - A ``add_<ship>_non_adjacent_constraints`` function that forbids ship parts
    in the buffer zone around each possible placement.
  - A ``<Ship>Factory`` class that orchestrates all three for convenience.
"""

import random
from src.utils import _get_ship_cells, get_var, _get_forbidden_cells


# ──────────────────────────────────────────────────────────────────────────────
# Patrol Boat (1×2)
# ──────────────────────────────────────────────────────────────────────────────

def add_patrol_boat_to_board(board_size, cnf, occupied=None):
    """Randomly places exactly one patrol boat (1×2) on the board.

    Collects all valid horizontal and vertical placements that do not conflict
    with already-occupied cells (including adjacency buffers), then picks one
    uniformly at random. Asserts the placement variable and SP variables as
    unit clauses.

    Args:
        board_size: The side length of the square board.
        cnf: The CNF to append placement unit clauses to.
        occupied: Set of (row, col) cells already taken. Defaults to empty.

    Returns:
        Updated occupied set including the new ship's cells and buffer.

    Raises:
        RuntimeError: If no valid placement exists.
    """
    if occupied is None:
        occupied = set()

    # Collect all valid placements that don't conflict with already-occupied cells
    valid_placements = []
    for r in range(board_size):
        for c in range(board_size - 1):
            cells = _get_ship_cells('h', r, c, 2)
            if not any(cell in occupied for cell in cells):
                valid_placements.append(('h', r, c, cells))
    for r in range(board_size - 1):
        for c in range(board_size):
            cells = _get_ship_cells('v', r, c, 2)
            if not any(cell in occupied for cell in cells):
                valid_placements.append(('v', r, c, cells))

    if not valid_placements:
        raise RuntimeError("No valid placement for patrol boat")

    orientation, r, c, cells = random.choice(valid_placements)

    if orientation == 'h':
        pb_var = get_var(board_size, 3, r, c)
    else:
        pb_var = get_var(board_size, 4, r, c)
    cnf.append([pb_var])

    # Ensure the ship parts are set
    for (cr, cc) in cells:
        cnf.append([get_var(board_size, 1, cr, cc)])

    # Update occupied with cells + buffer
    return occupied | _get_forbidden_cells(board_size, cells)

def add_patrol_boat_constraints(board_size, cnf):
    """Encodes patrol boat placement implications and exactly-one constraints.

    For every valid horizontal placement ``PB_{h,r,c}``:
      - ``PB_{h,r,c} -> SP_{r,c} ∧ SP_{r,c+1}``

    For every valid vertical placement ``PB_{v,r,c}``:
      - ``PB_{v,r,c} -> SP_{r,c} ∧ SP_{r+1,c}``

    Exactly-one: at least one placement must be true, and no two placements
    can be true simultaneously (pairwise mutual exclusion).

    Args:
        board_size: The side length of the square board.
        cnf: The CNF to append clauses to.

    Returns:
        The same CNF object with the new clauses appended.
    """
    # Variables: 
    # Type 3 = Patrol Boat Horizontal placement
    # Type 4 = Patrol Boat Vertical placement
    
    all_placements = []
    
    # 1. Define all valid placements
    for r in range(board_size):
        for c in range(board_size):
            # Horizontal (fits if c < 9)
            if c < board_size - 1:
                var_h = get_var(board_size, 3, r, c)
                all_placements.append(var_h)
                
                # PatrolBoat horizontal constraint: PatrolBoat_{h,i,j} -> (SP_{i,j} AND SP_{i,j+1})
                sp1 = get_var(board_size, 1, r, c)
                sp2 = get_var(board_size, 1, r, c + 1)
                cnf.append([-var_h, sp1])
                cnf.append([-var_h, sp2])
            
            # Vertical (fits if r < 9)
            if r < board_size - 1:
                var_v = get_var(board_size, 4, r, c)
                all_placements.append(var_v)
                
                # PatrolBoat vertical constraint: PatrolBoat_{v,i,j} -> (SP_{i,j} AND SP_{i+1,j})
                sp1 = get_var(board_size,1, r, c)
                sp2 = get_var(board_size, 1, r + 1, c)
                cnf.append([-var_v, sp1])
                cnf.append([-var_v, sp2])
                
    # 2. Exactly one placement: At least one
    cnf.append(list(all_placements))
    
    # 3. Exactly one placement: At most one (Pairwise negation)
    # This subsumes the per-cell XOR orientation constraint, so we don't add it separately.
    for i in range(len(all_placements)):
        for j in range(i + 1, len(all_placements)):
            cnf.append([-all_placements[i], -all_placements[j]])
    
    # 4. Non adjacent constraint
    
    return cnf 


def add_patrol_boat_non_adjacent_constraints(board_size, cnf):
    """Encodes the non-adjacency constraints for the patrol boat (length 2).

    For each valid patrol-boat placement (horizontal or vertical) at (r, c),
    no ship part (SP) may appear in any of the 6 buffer cells surrounding the
    2-cell ship (orthogonally or diagonally adjacent, excluding the ship's own
    cells).

    Variable types used:
      - Type 1 = SP_{i,j}   (ship part)
      - Type 3 = PB_{h,i,j} (patrol boat horizontal placement)
      - Type 4 = PB_{v,i,j} (patrol boat vertical placement)
    """

    # PatrolBoat horizontal: PB_{h,i,j} -> (¬SP_{i,j-1} ∧ ¬SP_{i,j+2} ∧ ¬SP_{i+1,j} ∧ ¬SP_{i-1,j} ∧ ¬SP_{i+1,j+1} ∧ ¬SP_{i-1,j+1})
    for r in range(board_size):
        for c in range(board_size - 1):  # Horizontal placement needs c < board_size - 1
            pb_h = get_var(board_size, 3, r, c)

            adj_positions = []
            if c > 0:  # Left of first part (i, j-1)
                adj_positions.append(get_var(board_size, 1, r, c - 1))
            if c + 2 < board_size:  # Right of second part (i, j+2)
                adj_positions.append(get_var(board_size, 1, r, c + 2))
            if r + 1 < board_size:  # Below first part (i+1, j)
                adj_positions.append(get_var(board_size, 1, r + 1, c))
                # Below second part (i+1, j+1)
                adj_positions.append(get_var(board_size, 1, r + 1, c + 1))
            if r - 1 >= 0:  # Above first part (i-1, j)
                adj_positions.append(get_var(board_size, 1, r - 1, c))
                # Above second part (i-1, j+1)
                adj_positions.append(get_var(board_size, 1, r - 1, c + 1))

            for adj_sp in adj_positions:
                cnf.append([-pb_h, -adj_sp])

    # PatrolBoat vertical: PB_{v,i,j} -> (¬SP_{i-1,j} ∧ ¬SP_{i+2,j} ∧ ¬SP_{i,j+1} ∧ ¬SP_{i,j-1} ∧ ¬SP_{i+1,j+1} ∧ ¬SP_{i+1,j-1})
    for r in range(board_size - 1):  # Vertical placement needs r < board_size - 1
        for c in range(board_size):
            pb_v = get_var(board_size, 4, r, c)

            adj_positions = []
            if r - 1 >= 0:  # Above (i-1, j)
                adj_positions.append(get_var(board_size, 1, r - 1, c))
            if r + 2 < board_size:  # Below second part (i+2, j)
                adj_positions.append(get_var(board_size, 1, r + 2, c))
            if c + 1 < board_size:  # Right of first part (i, j+1)
                adj_positions.append(get_var(board_size, 1, r, c + 1))
                # Right of second part (i+1, j+1)
                adj_positions.append(get_var(board_size, 1, r + 1, c + 1))
            if c - 1 >= 0:  # Left of first part (i, j-1)
                adj_positions.append(get_var(board_size, 1, r, c - 1))
                # Left of second part (i+1, j-1)
                adj_positions.append(get_var(board_size, 1, r + 1, c - 1))

            for adj_sp in adj_positions:
                cnf.append([-pb_v, -adj_sp])

    return cnf



# ──────────────────────────────────────────────────────────────────────────────
# Submarine (1×3)
# ──────────────────────────────────────────────────────────────────────────────

def add_submarine_to_board(board_size, cnf, occupied=None):
    """Randomly places exactly one submarine (1×3) on the board.

    Args:
        board_size: The side length of the square board.
        cnf: The CNF to append placement unit clauses to.
        occupied: Set of (row, col) cells already taken. Defaults to empty.

    Returns:
        Updated occupied set including the new ship's cells and buffer.

    Raises:
        RuntimeError: If no valid placement exists.
    """
    if occupied is None:
        occupied = set()

    valid_placements = []
    for r in range(board_size):
        for c in range(board_size - 2):
            cells = _get_ship_cells('h', r, c, 3)
            if not any(cell in occupied for cell in cells):
                valid_placements.append(('h', r, c, cells))
    for r in range(board_size - 2):
        for c in range(board_size):
            cells = _get_ship_cells('v', r, c, 3)
            if not any(cell in occupied for cell in cells):
                valid_placements.append(('v', r, c, cells))

    if not valid_placements:
        raise RuntimeError("No valid placement for submarine")

    orientation, r, c, cells = random.choice(valid_placements)

    if orientation == 'h':
        sm_var = get_var(board_size, 5, r, c)
    else:
        sm_var = get_var(board_size, 6, r, c)
    cnf.append([sm_var])

    for (cr, cc) in cells:
        cnf.append([get_var(board_size, 1, cr, cc)])

    return occupied | _get_forbidden_cells(board_size, cells)


def add_submarine_constraints(board_size, cnf):
    """Encodes submarine placement implications and exactly-one constraints.

    For every valid horizontal placement ``SM_{h,r,c}``:
      - ``SM_{h,r,c} -> SP_{r,c} ∧ SP_{r,c+1} ∧ SP_{r,c+2}``

    For every valid vertical placement ``SM_{v,r,c}``:
      - ``SM_{v,r,c} -> SP_{r,c} ∧ SP_{r+1,c} ∧ SP_{r+2,c}``

    Exactly-one: at least one placement must be true, and no two placements
    can be true simultaneously.

    Args:
        board_size: The side length of the square board.
        cnf: The CNF to append clauses to.

    Returns:
        The same CNF object with the new clauses appended.
    """
    # Variables: 
    # Type 5 = Submarine Horizontal placement
    # Type 6 = Submarine Vertical placement
    
    all_placements = []
    
    # 1. Define all valid placements
    for r in range(board_size):
        for c in range(board_size):
            # Horizontal (fits if c < 8)
            if c < board_size - 2:
                var_h = get_var(board_size, 5, r, c)
                all_placements.append(var_h)
                
                # Submarine horizontal constraint: Submarine_{h,i,j} -> (SP_{i,j} AND SP_{i,j+1} AND SP_{i,j+2})
                sp1 = get_var(board_size, 1, r, c)
                sp2 = get_var(board_size, 1, r, c + 1)
                sp3 = get_var(board_size, 1, r, c + 2)
                cnf.append([-var_h, sp1])
                cnf.append([-var_h, sp2])
                cnf.append([-var_h, sp3])
            
            # Vertical (fits if r < 8)
            if r < board_size - 2:
                var_v = get_var(board_size,6, r, c)
                all_placements.append(var_v)
                
                # Submarine vertical constraint: Submarine_{v,i,j} -> (SP_{i,j} AND SP_{i+1,j} AND SP_{i+2,j})
                sp1 = get_var(board_size, 1, r, c)
                sp2 = get_var(board_size, 1, r + 1, c)
                sp3 = get_var(board_size, 1, r + 2, c)
                cnf.append([-var_v, sp1])
                cnf.append([-var_v, sp2])
                cnf.append([-var_v, sp3])
                
    # 2. Exactly one placement: At least one
    cnf.append(list(all_placements))
    
    # 3. Exactly one placement: At most one (Pairwise negation)
    # This subsumes the per-cell XOR orientation constraint, so we don't add it separately.
    for i in range(len(all_placements)):
        for j in range(i + 1, len(all_placements)):
            cnf.append([-all_placements[i], -all_placements[j]])
    
    return cnf


def add_submarine_non_adjacent_constraints(board_size, cnf):
    """Encodes the non-adjacency constraints for the submarine (length 3).

    For each valid submarine placement (horizontal or vertical) at (r, c),
    no ship part (SP) may appear in any of the 8 buffer cells surrounding the
    3-cell ship (orthogonally or diagonally adjacent, excluding the ship's own
    cells).

    Variable types used:
      - Type 1 = SP_{i,j}   (ship part)
      - Type 5 = SM_{h,i,j} (submarine horizontal placement)
      - Type 6 = SM_{v,i,j} (submarine vertical placement)
    """

    # Submarine horizontal: SM_{h,i,j} -> (¬SP_{i,j-1} ∧ ¬SP_{i,j+3} ∧ ¬SP_{i+1,j} ∧ ¬SP_{i-1,j} ∧ ¬SP_{i+1,j-1} ∧ ¬SP_{i-1,j-1} ∧ ¬SP_{i+1,j+1} ∧ ¬SP_{i-1,j+1} ∧ ¬SP_{i+1,j+2} ∧ ¬SP_{i-1,j+2})
    for r in range(board_size):
        for c in range(board_size - 2):  # Horizontal placement needs c < board_size - 2
            sm_h = get_var(board_size, 5, r, c)

            adj_positions = []
            if c - 1 >= 0:  # Left (i, j-1)
                adj_positions.append(get_var(board_size, 1, r, c - 1))
            if c + 3 < board_size:  # Right (i, j+3)
                adj_positions.append(get_var(board_size, 1, r, c + 3))
            if r + 1 < board_size:  # Below row
                adj_positions.append(get_var(board_size, 1, r + 1, c))      # (i+1, j)
                adj_positions.append(get_var(board_size, 1, r + 1, c + 1))  # (i+1, j+1)
                adj_positions.append(get_var(board_size, 1, r + 1, c + 2))  # (i+1, j+2)
                if c - 1 >= 0:
                    adj_positions.append(get_var(board_size, 1, r + 1, c - 1))  # (i+1, j-1)
            if r - 1 >= 0:  # Above row
                adj_positions.append(get_var(board_size, 1, r - 1, c))      # (i-1, j)
                adj_positions.append(get_var(board_size, 1, r - 1, c + 1))  # (i-1, j+1)
                adj_positions.append(get_var(board_size, 1, r - 1, c + 2))  # (i-1, j+2)
                if c - 1 >= 0:
                    adj_positions.append(get_var(board_size, 1, r - 1, c - 1))  # (i-1, j-1)

            for adj_sp in adj_positions:
                cnf.append([-sm_h, -adj_sp])

    # Submarine vertical: SM_{v,i,j} -> (¬SP_{i-1,j} ∧ ¬SP_{i+3,j} ∧ ¬SP_{i,j+1} ∧ ¬SP_{i,j-1} ∧ ¬SP_{i-1,j+1} ∧ ¬SP_{i-1,j-1} ∧ ¬SP_{i+1,j+1} ∧ ¬SP_{i+1,j-1} ∧ ¬SP_{i+2,j+1} ∧ ¬SP_{i+2,j-1})
    for r in range(board_size - 2):  # Vertical placement needs r < board_size - 2
        for c in range(board_size):
            sm_v = get_var(board_size, 6, r, c)

            adj_positions = []
            if r - 1 >= 0:  # Above (i-1, j)
                adj_positions.append(get_var(board_size, 1, r - 1, c))
            if r + 3 < board_size:  # Below (i+3, j)
                adj_positions.append(get_var(board_size, 1, r + 3, c))
            if c + 1 < board_size:  # Right column
                adj_positions.append(get_var(board_size, 1, r, c + 1))      # (i, j+1)
                adj_positions.append(get_var(board_size, 1, r + 1, c + 1))  # (i+1, j+1)
                adj_positions.append(get_var(board_size, 1, r + 2, c + 1))  # (i+2, j+1)
                if r - 1 >= 0:
                    adj_positions.append(get_var(board_size, 1, r - 1, c + 1))  # (i-1, j+1)
            if c - 1 >= 0:  # Left column
                adj_positions.append(get_var(board_size, 1, r, c - 1))      # (i, j-1)
                adj_positions.append(get_var(board_size, 1, r + 1, c - 1))  # (i+1, j-1)
                adj_positions.append(get_var(board_size, 1, r + 2, c - 1))  # (i+2, j-1)
                if r - 1 >= 0:
                    adj_positions.append(get_var(board_size, 1, r - 1, c - 1))  # (i-1, j-1)

            for adj_sp in adj_positions:
                cnf.append([-sm_v, -adj_sp])

    return cnf


# ──────────────────────────────────────────────────────────────────────────────
# Battleship (1×4)
# ──────────────────────────────────────────────────────────────────────────────

def add_battleship_to_board(board_size, cnf, occupied=None):
    """Randomly places exactly one battleship (1×4) on the board.

    Args:
        board_size: The side length of the square board.
        cnf: The CNF to append placement unit clauses to.
        occupied: Set of (row, col) cells already taken. Defaults to empty.

    Returns:
        Updated occupied set including the new ship's cells and buffer.

    Raises:
        RuntimeError: If no valid placement exists.
    """
    if occupied is None:
        occupied = set()

    valid_placements = []
    for r in range(board_size):
        for c in range(board_size - 3):
            cells = _get_ship_cells('h', r, c, 4)
            if not any(cell in occupied for cell in cells):
                valid_placements.append(('h', r, c, cells))
    for r in range(board_size - 3):
        for c in range(board_size):
            cells = _get_ship_cells('v', r, c, 4)
            if not any(cell in occupied for cell in cells):
                valid_placements.append(('v', r, c, cells))

    if not valid_placements:
        raise RuntimeError("No valid placement for battleship")

    orientation, r, c, cells = random.choice(valid_placements)

    if orientation == 'h':
        bs_var = get_var(board_size, 14, r, c)
    else:
        bs_var = get_var(board_size, 15, r, c)
    cnf.append([bs_var])

    for (cr, cc) in cells:
        cnf.append([get_var(board_size, 1, cr, cc)])

    return occupied | _get_forbidden_cells(board_size, cells)


def add_battleship_constraints(board_size, cnf):
    """Encodes battleship placement implications and exactly-one constraints.

    For every valid horizontal placement ``BS_{h,r,c}``:
      - ``BS_{h,r,c} -> SP_{r,c} ∧ SP_{r,c+1} ∧ SP_{r,c+2} ∧ SP_{r,c+3}``

    For every valid vertical placement ``BS_{v,r,c}``:
      - ``BS_{v,r,c} -> SP_{r,c} ∧ SP_{r+1,c} ∧ SP_{r+2,c} ∧ SP_{r+3,c}``

    Exactly-one: at least one placement must be true, and no two placements
    can be true simultaneously.

    Args:
        board_size: The side length of the square board.
        cnf: The CNF to append clauses to.

    Returns:
        The same CNF object with the new clauses appended.
    """
    all_placements = []
    for r in range(board_size):
        for c in range(board_size):
            if c < board_size - 3:
                var_h = get_var(board_size, 14, r, c)
                all_placements.append(var_h)
                for k in range(4):
                    cnf.append([-var_h, get_var(board_size, 1, r, c + k)])
            if r < board_size - 3:
                var_v = get_var(board_size, 15, r, c)
                all_placements.append(var_v)
                for k in range(4):
                    cnf.append([-var_v, get_var(board_size, 1, r + k, c)])
    cnf.append(list(all_placements))
    for i in range(len(all_placements)):
        for j in range(i + 1, len(all_placements)):
            cnf.append([-all_placements[i], -all_placements[j]])
    return cnf


def add_battleship_non_adjacent_constraints(board_size, cnf):
    """Encodes non-adjacency constraints for the battleship (length 4).

    For each valid placement, no ship part may appear in any buffer cell
    surrounding the 4-cell ship.

    Args:
        board_size: The side length of the square board.
        cnf: The CNF to append clauses to.

    Returns:
        The same CNF object with the new clauses appended.
    """
    for r in range(board_size):
        for c in range(board_size - 3):
            bs_h = get_var(board_size, 14, r, c)
            cells = _get_ship_cells('h', r, c, 4)
            for nr, nc in _get_forbidden_cells(board_size, cells):
                if (nr, nc) not in cells:
                    cnf.append([-bs_h, -get_var(board_size, 1, nr, nc)])
    for r in range(board_size - 3):
        for c in range(board_size):
            bs_v = get_var(board_size, 15, r, c)
            cells = _get_ship_cells('v', r, c, 4)
            for nr, nc in _get_forbidden_cells(board_size, cells):
                if (nr, nc) not in cells:
                    cnf.append([-bs_v, -get_var(board_size, 1, nr, nc)])
    return cnf


# ──────────────────────────────────────────────────────────────────────────────
# Carrier (2×2)
# ──────────────────────────────────────────────────────────────────────────────

def add_carrier_to_board(board_size, cnf, occupied=None):
    """Randomly places exactly one carrier (2×2) on the board.

    Args:
        board_size: The side length of the square board.
        cnf: The CNF to append placement unit clauses to.
        occupied: Set of (row, col) cells already taken. Defaults to empty.

    Returns:
        Updated occupied set including the new ship's cells and buffer.

    Raises:
        RuntimeError: If no valid placement exists.
    """
    if occupied is None:
        occupied = set()

    valid_placements = []
    for r in range(board_size - 1):
        for c in range(board_size - 1):
            cells = [(r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1)]
            if not any(cell in occupied for cell in cells):
                valid_placements.append((r, c, cells))

    if not valid_placements:
        raise RuntimeError("No valid placement for carrier")

    r, c, cells = random.choice(valid_placements)
    cr_var = get_var(board_size, 18, r, c)
    cnf.append([cr_var])

    for (cr, cc) in cells:
        cnf.append([get_var(board_size, 1, cr, cc)])

    return occupied | _get_forbidden_cells(board_size, cells)


def add_carrier_constraints(board_size, cnf):
    """Encodes carrier placement implications and exactly-one constraints.

    For every valid placement ``CR_{r,c}``:
      - ``CR_{r,c} -> SP_{r,c} ∧ SP_{r,c+1} ∧ SP_{r+1,c} ∧ SP_{r+1,c+1}``

    Exactly-one: at least one placement must be true, and no two placements
    can be true simultaneously.

    Args:
        board_size: The side length of the square board.
        cnf: The CNF to append clauses to.

    Returns:
        The same CNF object with the new clauses appended.
    """
    all_placements = []
    for r in range(board_size - 1):
        for c in range(board_size - 1):
            var = get_var(board_size, 18, r, c)
            all_placements.append(var)
            # Carrier_{i,j} -> (SP_{i,j} AND SP_{i,j+1} AND SP_{i+1,j} AND SP_{i+1,j+1})
            for dr in range(2):
                for dc in range(2):
                    cnf.append([-var, get_var(board_size, 1, r + dr, c + dc)])

    cnf.append(list(all_placements))
    for i in range(len(all_placements)):
        for j in range(i + 1, len(all_placements)):
            cnf.append([-all_placements[i], -all_placements[j]])
    return cnf


def add_carrier_non_adjacent_constraints(board_size, cnf):
    """Encodes non-adjacency constraints for the carrier (2×2).

    For each valid placement, no ship part may appear in any buffer cell
    surrounding the 4-cell (2×2) ship.

    Args:
        board_size: The side length of the square board.
        cnf: The CNF to append clauses to.

    Returns:
        The same CNF object with the new clauses appended.
    """
    for r in range(board_size - 1):
        for c in range(board_size - 1):
            cr_var = get_var(board_size, 18, r, c)
            cells = [(r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1)]
            for nr, nc in _get_forbidden_cells(board_size, cells):
                if (nr, nc) not in cells:
                    cnf.append([-cr_var, -get_var(board_size, 1, nr, nc)])
    return cnf


class PatrolBoatFactory:
    """Factory that places a patrol boat and adds all its constraints.

    Orchestrates ``add_patrol_boat_to_board``, ``add_patrol_boat_constraints``,
    and ``add_patrol_boat_non_adjacent_constraints`` in a single ``build`` call.

    Attributes:
        board_size: The side length of the square board.
    """

    def __init__(self, board_size):
        """Initializes the factory.

        Args:
            board_size: The side length of the square board.
        """
        self.board_size = board_size

    def build(self, cnf, occupied=None):
        """Places a patrol boat and adds placement + non-adjacency constraints.

        Args:
            cnf: The CNF to modify.
            occupied: Set of already-occupied cells. Defaults to empty.

        Returns:
            Updated occupied set.
        """
        if occupied is None:
            occupied = set()
        occupied = add_patrol_boat_to_board(self.board_size, cnf, occupied)
        add_patrol_boat_constraints(self.board_size, cnf)
        add_patrol_boat_non_adjacent_constraints(self.board_size, cnf)
        return occupied


class SubmarineFactory:
    """Factory that places a submarine and adds all its constraints.

    Attributes:
        board_size: The side length of the square board.
    """

    def __init__(self, board_size):
        """Initializes the factory.

        Args:
            board_size: The side length of the square board.
        """
        self.board_size = board_size

    def build(self, cnf, occupied=None):
        """Places a submarine and adds placement + non-adjacency constraints.

        Args:
            cnf: The CNF to modify.
            occupied: Set of already-occupied cells. Defaults to empty.

        Returns:
            Updated occupied set.
        """
        if occupied is None:
            occupied = set()
        occupied = add_submarine_to_board(self.board_size, cnf, occupied)
        add_submarine_constraints(self.board_size, cnf)
        add_submarine_non_adjacent_constraints(self.board_size, cnf)
        return occupied


class BattleshipFactory:
    """Factory that places a battleship and adds all its constraints.

    Attributes:
        board_size: The side length of the square board.
    """

    def __init__(self, board_size):
        """Initializes the factory.

        Args:
            board_size: The side length of the square board.
        """
        self.board_size = board_size

    def build(self, cnf, occupied=None):
        """Places a battleship and adds placement + non-adjacency constraints.

        Args:
            cnf: The CNF to modify.
            occupied: Set of already-occupied cells. Defaults to empty.

        Returns:
            Updated occupied set.
        """
        if occupied is None:
            occupied = set()
        occupied = add_battleship_to_board(self.board_size, cnf, occupied)
        add_battleship_constraints(self.board_size, cnf)
        add_battleship_non_adjacent_constraints(self.board_size, cnf)
        return occupied


class CarrierFactory:
    """Factory that places a carrier and adds all its constraints.

    Attributes:
        board_size: The side length of the square board.
    """

    def __init__(self, board_size):
        """Initializes the factory.

        Args:
            board_size: The side length of the square board.
        """
        self.board_size = board_size

    def build(self, cnf, occupied=None):
        """Places a carrier and adds placement + non-adjacency constraints.

        Args:
            cnf: The CNF to modify.
            occupied: Set of already-occupied cells. Defaults to empty.

        Returns:
            Updated occupied set.
        """
        if occupied is None:
            occupied = set()
        occupied = add_carrier_to_board(self.board_size, cnf, occupied)
        add_carrier_constraints(self.board_size, cnf)
        add_carrier_non_adjacent_constraints(self.board_size, cnf)
        return occupied

