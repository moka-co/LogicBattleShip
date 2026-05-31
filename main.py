import random
from pysat.formula import CNF

BOARD_SIZE=10

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


def add_shot_hit_miss_constraints(cnf):
    """Adds the static (non-dynamic) constraints for Shot, Hit, and Miss variables.

    These constraints are added once at KB initialization. The actual Shot/Hit/Miss
    unit clauses are added dynamically during gameplay via `record_shot`.

    Variable types used:
      - Type 7 = Shot_{i,j}
      - Type 8 = Hit_{i,j}
      - Type 9 = Miss_{i,j}

    Constraints encoded (per the README):
      1. Shot_{i,j} <=> (Hit_{i,j} OR Miss_{i,j})
      2. Hit_{i,j} and Miss_{i,j} are mutually exclusive
      3. Miss_{i,j} -> ¬SP_{i,j}
      4. Hit_{i,j}  ->  SP_{i,j}
      5. PatrolBoat orientation inference from hit/miss patterns.
    """

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            shot = get_var(7, r, c)
            hit = get_var(8, r, c)
            miss = get_var(9, r, c)
            sp = get_var(1, r, c)

            # 1. Shot <=> (Hit OR Miss), decomposed into three CNF clauses:
            #    Shot -> (Hit OR Miss)
            cnf.append([-shot, hit, miss])
            #    Hit -> Shot
            cnf.append([-hit, shot])
            #    Miss -> Shot
            cnf.append([-miss, shot])

            # 2. Hit and Miss are mutually exclusive: ¬(Hit AND Miss)
            cnf.append([-hit, -miss])

            # 3. Miss -> ¬SP (a missed tile cannot contain a ship part)
            cnf.append([-miss, -sp])

            # 4. Hit -> SP (a hit tile must contain a ship part)
            cnf.append([-hit, sp])

    # 5. PatrolBoat orientation inference (per README):
    # If Hit_{i,j} and both horizontal neighbors are Miss, then the ship at (i,j)
    # cannot be a horizontal patrol boat, and must be a vertical patrol boat with
    # the other part either above (i-1) or below (i+1).
    # Formula: (Hit_{i,j} ∧ Miss_{i,j-1} ∧ Miss_{i,j+1}) ->
    #          (¬PB_{h,i,j} ∧ (PB_{v,i+1,j} ∨ PB_{v,i-1,j}))
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            # Horizontal-misses pattern requires both j-1 and j+1 to be in bounds
            if c - 1 < 0 or c + 1 >= BOARD_SIZE:
                continue

            hit = get_var(8, r, c)
            miss_left = get_var(9, r, c - 1)
            miss_right = get_var(9, r, c + 1)

            # Conclusion clause 1: ¬PB_{h,i,j}
            # PB_{h,i,j} is only defined for c <= BOARD_SIZE - 2 (i.e. fits horizontally).
            # If c == BOARD_SIZE - 1, the horizontal PB at (i,c) doesn't exist anyway,
            # but emitting the clause is still harmless if the var is unused.
            if c + 1 < BOARD_SIZE:
                pb_h = get_var(3, r, c)
                cnf.append([-hit, -miss_left, -miss_right, -pb_h])

            # Conclusion clause 2: PB_{v,i-1,j} OR PB_{v,i+1,j}
            # PB_{v,r',c} is defined only for r' <= BOARD_SIZE - 2.
            disjuncts = [-hit, -miss_left, -miss_right]
            if r - 1 >= 0:
                # PB_{v,i-1,j}: places ship at (r-1, c)-(r, c). Valid since r-1 in [0, BOARD_SIZE-2].
                disjuncts.append(get_var(4, r - 1, c))
            if r + 1 < BOARD_SIZE and r <= BOARD_SIZE - 2:
                # PB_{v,i+1,j}: places ship at (r+1, c)-(r+2, c). Need r+1 <= BOARD_SIZE-2.
                if r + 1 <= BOARD_SIZE - 2:
                    disjuncts.append(get_var(4, r + 1, c))
            # Only emit the clause if at least one vertical option is feasible;
            # otherwise the implication would be contradictory and we'd encode unsat
            # for an impossible hit pattern (which is fine but we skip for clarity).
            if len(disjuncts) > 3:
                cnf.append(disjuncts)

    return cnf


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
    cnf = add_non_adjacent_constraints(cnf)
    # Add Shot/Hit/Miss static constraints (dynamic unit clauses are added later
    # via `record_shot` during gameplay).
    cnf = add_shot_hit_miss_constraints(cnf)
    # Add Sinking Ships biconditionals and AllPartsSunk consequences.
    cnf = add_sinking_constraints(cnf)
    cnf = add_all_parts_sunk_consequences(cnf)
    return cnf
    

if __name__ == "__main__":
    main()
