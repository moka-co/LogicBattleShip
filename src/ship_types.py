import random
from utils import _get_ship_cells, get_var, _get_forbidden_cells

# Patrol Boat
def add_patrol_boat_to_board(board_size, cnf, occupied=None):
    """Adds exactly one patrol boat to the board by choosing a random valid placement.
    `occupied` is a set of cells already taken (including adjacency buffer) to avoid conflicts.
    Returns the set of cells (including buffer) now occupied."""
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



# Submarine
def add_submarine_to_board(board_size, cnf, occupied=None):
    """Adds exactly one submarine to the board by choosing a random valid placement.
    `occupied` is a set of cells already taken (including adjacency buffer) to avoid conflicts.
    Returns the set of cells (including buffer) now occupied."""
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


class PatrolBoatFactory:
    def __init__(self, board_size):
        self.board_size = board_size

    def build(self, cnf, occupied=None):
        if occupied is None:
            occupied = set()
        occupied = add_patrol_boat_to_board(self.board_size, cnf, occupied)
        add_patrol_boat_constraints(self.board_size, cnf)
        add_patrol_boat_non_adjacent_constraints(self.board_size, cnf)
        return occupied


class SubmarineFactory:
    def __init__(self, board_size):
        self.board_size = board_size

    def build(self, cnf, occupied=None):
        if occupied is None:
            occupied = set()
        occupied = add_submarine_to_board(self.board_size, cnf, occupied)
        add_submarine_constraints(self.board_size, cnf)
        add_submarine_non_adjacent_constraints(self.board_size, cnf)
        return occupied

