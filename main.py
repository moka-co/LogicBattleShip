import random
from pysat.formula import CNF

BOARD_SIZE=10

# Map a unique integer to each cell for each of the three types 
# (0 = hidden, 1=shippiece, 2=empty, 3=patrol_boat_horizontal, 4=patrol_boat_vertical, 5=submarine_horizontal, 6=submarine_vertical)
def get_var(v_type, r, c):
    return v_type * (BOARD_SIZE * BOARD_SIZE) + r * BOARD_SIZE + c + 1

def init_empty_board():
    board_cnf = CNF()

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            sp = get_var(1, r, c)
            e = get_var(2, r, c)

            # A tile either contains a ShipPart or is Empty (exclusive)
            board_cnf.append([sp, e])
            board_cnf.append([-sp, -e])
    
    return board_cnf


def _get_ship_cells(orientation, r, c, length):
    """Returns the list of cells occupied by a ship of given length/orientation starting at (r,c)."""
    if orientation == 'h':
        return [(r, c + k) for k in range(length)]
    else:
        return [(r + k, c) for k in range(length)]


def _get_forbidden_cells(cells):
    """Returns the set of cells that would be adjacent (including diagonals) to a ship occupying `cells`.
    Used to enforce non-adjacent ship placement when randomly placing ships."""
    forbidden = set()
    for (r, c) in cells:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                    forbidden.add((nr, nc))
    return forbidden


def add_patrol_boat_to_board(cnf, occupied=None):
    """Adds exactly one patrol boat to the board by choosing a random valid placement.
    `occupied` is a set of cells already taken (including adjacency buffer) to avoid conflicts.
    Returns the set of cells (including buffer) now occupied."""
    if occupied is None:
        occupied = set()

    # Collect all valid placements that don't conflict with already-occupied cells
    valid_placements = []
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE - 1):
            cells = _get_ship_cells('h', r, c, 2)
            if not any(cell in occupied for cell in cells):
                valid_placements.append(('h', r, c, cells))
    for r in range(BOARD_SIZE - 1):
        for c in range(BOARD_SIZE):
            cells = _get_ship_cells('v', r, c, 2)
            if not any(cell in occupied for cell in cells):
                valid_placements.append(('v', r, c, cells))

    if not valid_placements:
        raise RuntimeError("No valid placement for patrol boat")

    orientation, r, c, cells = random.choice(valid_placements)

    if orientation == 'h':
        pb_var = get_var(3, r, c)
    else:
        pb_var = get_var(4, r, c)
    cnf.append([pb_var])

    # Ensure the ship parts are set
    for (cr, cc) in cells:
        cnf.append([get_var(1, cr, cc)])

    # Update occupied with cells + buffer
    return occupied | _get_forbidden_cells(cells)


def add_submarine_to_board(cnf, occupied=None):
    """Adds exactly one submarine to the board by choosing a random valid placement.
    `occupied` is a set of cells already taken (including adjacency buffer) to avoid conflicts.
    Returns the set of cells (including buffer) now occupied."""
    if occupied is None:
        occupied = set()

    valid_placements = []
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE - 2):
            cells = _get_ship_cells('h', r, c, 3)
            if not any(cell in occupied for cell in cells):
                valid_placements.append(('h', r, c, cells))
    for r in range(BOARD_SIZE - 2):
        for c in range(BOARD_SIZE):
            cells = _get_ship_cells('v', r, c, 3)
            if not any(cell in occupied for cell in cells):
                valid_placements.append(('v', r, c, cells))

    if not valid_placements:
        raise RuntimeError("No valid placement for submarine")

    orientation, r, c, cells = random.choice(valid_placements)

    if orientation == 'h':
        sm_var = get_var(5, r, c)
    else:
        sm_var = get_var(6, r, c)
    cnf.append([sm_var])

    for (cr, cc) in cells:
        cnf.append([get_var(1, cr, cc)])

    return occupied | _get_forbidden_cells(cells)


def add_random_boat(board_cnf, boat_type="PatrolBoat"):
    """Adds a 1x2 PatrolBoat to the CNF by forcing specific SP variables to be True."""

    # Randomly choose orientation: 0 for Horizontal, 1 for Vertical
    orientation = random.choice(['H', 'V'])
    
    if orientation == 'H':
        # Need r in 0-9, c in 0-8 (to leave room for c+1)
        r, c = random.randint(0, 9), random.randint(0, 8)
        cells = [(r, c), (r, c + 1)]
    else:
        # Need r in 0-8, c in 0-9
        r, c = random.randint(0, 8), random.randint(0, 9)
        cells = [(r, c), (r + 1, c)]
    
    # Add constraints: These specific cells MUST be ShipParts (SP)
    # Variable mapping: get_var(1, r, c) is the SP variable
    for r_cell, c_cell in cells:
        sp_var = get_var(1, r_cell, c_cell)
        board_cnf.append([sp_var])
        
    return cells

def add_patrol_boat_constraints(cnf):
    # Variables: 
    # Type 3 = Patrol Boat Horizontal placement
    # Type 4 = Patrol Boat Vertical placement
    
    all_placements = []
    
    # 1. Define all valid placements
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            # Horizontal (fits if c < 9)
            if c < BOARD_SIZE - 1:
                var_h = get_var(3, r, c)
                all_placements.append(var_h)
                
                # PatrolBoat horizontal constraint: PatrolBoat_{h,i,j} -> (SP_{i,j} AND SP_{i,j+1})
                sp1 = get_var(1, r, c)
                sp2 = get_var(1, r, c + 1)
                cnf.append([-var_h, sp1])
                cnf.append([-var_h, sp2])
            
            # Vertical (fits if r < 9)
            if r < BOARD_SIZE - 1:
                var_v = get_var(4, r, c)
                all_placements.append(var_v)
                
                # PatrolBoat vertical constraint: PatrolBoat_{v,i,j} -> (SP_{i,j} AND SP_{i+1,j})
                sp1 = get_var(1, r, c)
                sp2 = get_var(1, r + 1, c)
                cnf.append([-var_v, sp1])
                cnf.append([-var_v, sp2])
                
    # 2. Exactly one placement: At least one
    cnf.append(list(all_placements))
    
    # 3. Exactly one placement: At most one (Pairwise negation)
    # This subsumes the per-cell XOR orientation constraint, so we don't add it separately.
    for i in range(len(all_placements)):
        for j in range(i + 1, len(all_placements)):
            cnf.append([-all_placements[i], -all_placements[j]])
    
    return cnf 

def add_submarine_constraints(cnf):
    # Variables: 
    # Type 5 = Submarine Horizontal placement
    # Type 6 = Submarine Vertical placement
    
    all_placements = []
    
    # 1. Define all valid placements
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            # Horizontal (fits if c < 8)
            if c < BOARD_SIZE - 2:
                var_h = get_var(5, r, c)
                all_placements.append(var_h)
                
                # Submarine horizontal constraint: Submarine_{h,i,j} -> (SP_{i,j} AND SP_{i,j+1} AND SP_{i,j+2})
                sp1 = get_var(1, r, c)
                sp2 = get_var(1, r, c + 1)
                sp3 = get_var(1, r, c + 2)
                cnf.append([-var_h, sp1])
                cnf.append([-var_h, sp2])
                cnf.append([-var_h, sp3])
            
            # Vertical (fits if r < 8)
            if r < BOARD_SIZE - 2:
                var_v = get_var(6, r, c)
                all_placements.append(var_v)
                
                # Submarine vertical constraint: Submarine_{v,i,j} -> (SP_{i,j} AND SP_{i+1,j} AND SP_{i+2,j})
                sp1 = get_var(1, r, c)
                sp2 = get_var(1, r + 1, c)
                sp3 = get_var(1, r + 2, c)
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

def add_non_adjacent_constraints(cnf):
    # Cannot place any ships adjacently
    
    # PatrolBoat horizontal: PB_{h,i,j} -> (¬SP_{i,j-1} ∧ ¬SP_{i,j+2} ∧ ¬SP_{i+1,j} ∧ ¬SP_{i-1,j} ∧ ¬SP_{i+1,j+1} ∧ ¬SP_{i-1,j+1})
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE - 1):  # Horizontal placement needs c < 9
            pb_h = get_var(3, r, c)
            
            adj_positions = []
            if c > 0:  # Left of first part (i, j-1)
                adj_positions.append(get_var(1, r, c - 1))
            if c + 2 < BOARD_SIZE:  # Right of second part (i, j+2)
                adj_positions.append(get_var(1, r, c + 2))
            if r + 1 < BOARD_SIZE:  # Below first part (i+1, j)
                adj_positions.append(get_var(1, r + 1, c))
                # Below second part (i+1, j+1)
                adj_positions.append(get_var(1, r + 1, c + 1))
            if r - 1 >= 0:  # Above first part (i-1, j)
                adj_positions.append(get_var(1, r - 1, c))
                # Above second part (i-1, j+1)
                adj_positions.append(get_var(1, r - 1, c + 1))
            
            for adj_sp in adj_positions:
                cnf.append([-pb_h, -adj_sp])
    
    # PatrolBoat vertical: PB_{v,i,j} -> (¬SP_{i-1,j} ∧ ¬SP_{i+2,j} ∧ ¬SP_{i,j+1} ∧ ¬SP_{i,j-1} ∧ ¬SP_{i+1,j+1} ∧ ¬SP_{i+1,j-1})
    for r in range(BOARD_SIZE - 1):  # Vertical placement needs r < 9
        for c in range(BOARD_SIZE):
            pb_v = get_var(4, r, c)
            
            adj_positions = []
            if r - 1 >= 0:  # Above (i-1, j)
                adj_positions.append(get_var(1, r - 1, c))
            if r + 2 < BOARD_SIZE:  # Below second part (i+2, j)
                adj_positions.append(get_var(1, r + 2, c))
            if c + 1 < BOARD_SIZE:  # Right of first part (i, j+1)
                adj_positions.append(get_var(1, r, c + 1))
                # Right of second part (i+1, j+1)
                adj_positions.append(get_var(1, r + 1, c + 1))
            if c - 1 >= 0:  # Left of first part (i, j-1)
                adj_positions.append(get_var(1, r, c - 1))
                # Left of second part (i+1, j-1)
                adj_positions.append(get_var(1, r + 1, c - 1))
            
            for adj_sp in adj_positions:
                cnf.append([-pb_v, -adj_sp])
    
    # Submarine horizontal: SM_{h,i,j} -> (¬SP_{i,j-1} ∧ ¬SP_{i,j+3} ∧ ¬SP_{i+1,j} ∧ ¬SP_{i-1,j} ∧ ¬SP_{i+1,j-1} ∧ ¬SP_{i-1,j-1} ∧ ¬SP_{i+1,j+1} ∧ ¬SP_{i-1,j+1} ∧ ¬SP_{i+1,j+2} ∧ ¬SP_{i-1,j+2})
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE - 2):  # Horizontal placement needs c < 8
            sm_h = get_var(5, r, c)
            
            adj_positions = []
            if c - 1 >= 0:  # Left (i, j-1)
                adj_positions.append(get_var(1, r, c - 1))
            if c + 3 < BOARD_SIZE:  # Right (i, j+3)
                adj_positions.append(get_var(1, r, c + 3))
            if r + 1 < BOARD_SIZE:  # Below row
                adj_positions.append(get_var(1, r + 1, c))      # (i+1, j)
                adj_positions.append(get_var(1, r + 1, c + 1))  # (i+1, j+1)
                adj_positions.append(get_var(1, r + 1, c + 2))  # (i+1, j+2)
                if c - 1 >= 0:
                    adj_positions.append(get_var(1, r + 1, c - 1))  # (i+1, j-1)
            if r - 1 >= 0:  # Above row
                adj_positions.append(get_var(1, r - 1, c))      # (i-1, j)
                adj_positions.append(get_var(1, r - 1, c + 1))  # (i-1, j+1)
                adj_positions.append(get_var(1, r - 1, c + 2))  # (i-1, j+2)
                if c - 1 >= 0:
                    adj_positions.append(get_var(1, r - 1, c - 1))  # (i-1, j-1)
            
            for adj_sp in adj_positions:
                cnf.append([-sm_h, -adj_sp])
    
    # Submarine vertical: SM_{v,i,j} -> (¬SP_{i-1,j} ∧ ¬SP_{i+3,j} ∧ ¬SP_{i,j+1} ∧ ¬SP_{i,j-1} ∧ ¬SP_{i-1,j+1} ∧ ¬SP_{i-1,j-1} ∧ ¬SP_{i+1,j+1} ∧ ¬SP_{i+1,j-1} ∧ ¬SP_{i+2,j+1} ∧ ¬SP_{i+2,j-1})
    for r in range(BOARD_SIZE - 2):  # Vertical placement needs r < 8
        for c in range(BOARD_SIZE):
            sm_v = get_var(6, r, c)
            
            adj_positions = []
            if r - 1 >= 0:  # Above (i-1, j)
                adj_positions.append(get_var(1, r - 1, c))
            if r + 3 < BOARD_SIZE:  # Below (i+3, j)
                adj_positions.append(get_var(1, r + 3, c))
            if c + 1 < BOARD_SIZE:  # Right column
                adj_positions.append(get_var(1, r, c + 1))      # (i, j+1)
                adj_positions.append(get_var(1, r + 1, c + 1))  # (i+1, j+1)
                adj_positions.append(get_var(1, r + 2, c + 1))  # (i+2, j+1)
                if r - 1 >= 0:
                    adj_positions.append(get_var(1, r - 1, c + 1))  # (i-1, j+1)
            if c - 1 >= 0:  # Left column
                adj_positions.append(get_var(1, r, c - 1))      # (i, j-1)
                adj_positions.append(get_var(1, r + 1, c - 1))  # (i+1, j-1)
                adj_positions.append(get_var(1, r + 2, c - 1))  # (i+2, j-1)
                if r - 1 >= 0:
                    adj_positions.append(get_var(1, r - 1, c - 1))  # (i-1, j-1)
            
            for adj_sp in adj_positions:
                cnf.append([-sm_v, -adj_sp])
    
    return cnf

def main():
    print(f"Board Size: {BOARD_SIZE}")
    cnf = init_empty_board()
    occupied = add_patrol_boat_to_board(cnf)
    occupied = add_submarine_to_board(cnf, occupied)
    cnf = add_patrol_boat_constraints(cnf)
    cnf = add_submarine_constraints(cnf)
    cnf = add_non_adjacent_constraints(cnf)
    return cnf
    

if __name__ == "__main__":
    main()
