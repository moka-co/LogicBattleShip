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


