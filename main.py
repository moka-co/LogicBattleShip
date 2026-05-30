import random
from pysat.formula import CNF

BOARD_SIZE=10

# Map a unique integer to each cell for each of the three types 
# (0 = hidden, 1=shippiece, 2=empty)
def get_var(v_type, r, c):
    return (v_type *100) + (r*10) + c + 1

def init_empty_board():
    board_cnf = CNF()

    for r in range(10):
        for c in range(10):
            h = get_var(0, r, c)
            sp = get_var(1, r, c)
            e = get_var(2, r, c)

            # A tile either contains a ShipPart or is Empty
            board_cnf.append([sp, e])
            board_cnf.append([-sp, -e])
    
    return board_cnf


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
        
    # Optional: Add non-overlapping rule if you add more boats later
    # (e.g., if this is SP, the neighbor MUST be SP)
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
            
            # Vertical (fits if r < 9)
            if r < BOARD_SIZE - 1:
                var_v = get_var(4, r, c)
                all_placements.append(var_v)
                
    # 2. Exactly one placement: At least one
    cnf.append(all_placements)
    
    # 3. Exactly one placement: At most one (Pairwise negation)
    for i in range(len(all_placements)):
        for j in range(i + 1, len(all_placements)):
            cnf.append([-all_placements[i], -all_placements[j]])
            
    # 4. XOR Orientation Constraint: Only one orientation allowed at positions 
    # where both orientations are possible
    for r in range(BOARD_SIZE - 1):
        for c in range(BOARD_SIZE - 1):
            h = get_var(3, r, c)
            v = get_var(4, r, c)
            # If both placements are chosen, that's invalid (XOR)
            cnf.append([-h, -v])
    
    return cnf 

def main():
    print(f"Board Size: {BOARD_SIZE}")
    cnf = init_empty_board()
    cells = add_random_boat(cnf)
    cnf = add_patrol_boat_constraints(cnf)




if __name__ == "__main__":
    main()
