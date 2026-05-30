import random
from pysat.formula import CNF

BOARD_SIZE=10

# Map a unique integer to each cell for each of the three types 
# (0 = hidden, 1=shippiece, 2=empty, 3=patrol_boat_horizontal, 4=patrol_boat_vertical, 5=submarine_horizontal, 6=submarine_vertical)
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
    cnf.append(all_placements)
    
    # 3. Exactly one placement: At most one (Pairwise negation)
    for i in range(len(all_placements)):
        for j in range(i + 1, len(all_placements)):
            cnf.append([-all_placements[i], -all_placements[j]])
            
    # 4. XOR Orientation Constraint: For each position where both orientations are possible,
    # exactly one orientation must be chosen
    for r in range(BOARD_SIZE - 1):
        for c in range(BOARD_SIZE - 1):
            h = get_var(3, r, c)
            v = get_var(4, r, c)
            # Exactly one of horizontal or vertical can be true at each position
            cnf.append([-h, -v])  # Not both can be true
            # Note: The "at least one" is handled by the global exactly-one constraint above
    
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
    cnf.append(all_placements)
    
    # 3. Exactly one placement: At most one (Pairwise negation)
    for i in range(len(all_placements)):
        for j in range(i + 1, len(all_placements)):
            cnf.append([-all_placements[i], -all_placements[j]])
            
    # 4. XOR Orientation Constraint: For each position where both orientations are possible,
    # exactly one orientation must be chosen
    for r in range(BOARD_SIZE - 2):
        for c in range(BOARD_SIZE - 2):
            h = get_var(5, r, c)
            v = get_var(6, r, c)
            # Exactly one of horizontal or vertical can be true at each position
            cnf.append([-h, -v])  # Not both can be true
            # Note: The "at least one" is handled by the global exactly-one constraint above
    
    return cnf

def add_non_adjacent_constraints(cnf):
    # Cannot place any ships adjacently
    
    # PatrolBoat horizontal: PB_{h,i,j} -> (¬SP_{i,j-1} ∧ ¬SP_{i,j+2} ∧ ¬SP_{i+1,j} ∧ ¬SP_{i-1,j} ∧ ¬SP_{i+1,j+1} ∧ ¬SP_{i-1,j+1})
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE - 1):  # Horizontal placement needs c < 9
            pb_h = get_var(3, r, c)
            
            # Adjacent positions that must be empty
            adj_positions = []
            if c > 0:  # Left
                adj_positions.append(get_var(1, r, c - 1))
            if c < BOARD_SIZE - 2:  # Right
                adj_positions.append(get_var(1, r, c + 2))
            if r < BOARD_SIZE - 1:  # Below
                adj_positions.append(get_var(1, r + 1, c))
                if c < BOARD_SIZE - 1:  # Below right
                    adj_positions.append(get_var(1, r + 1, c + 1))
            if r > 0:  # Above
                adj_positions.append(get_var(1, r - 1, c))
                if c < BOARD_SIZE - 1:  # Above right
                    adj_positions.append(get_var(1, r - 1, c + 1))
            
            # Add constraints
            for adj_sp in adj_positions:
                cnf.append([-pb_h, -adj_sp])
    
    # PatrolBoat vertical: PB_{v,i,j} -> (¬SP_{i-1,j} ∧ ¬SP_{i+2,j} ∧ ¬SP_{i,j+1} ∧ ¬SP_{i,j-1} ∧ ¬SP_{i+1,j+1} ∧ ¬SP_{i+1,j-1})
    for r in range(BOARD_SIZE - 1):  # Vertical placement needs r < 9
        for c in range(BOARD_SIZE):
            pb_v = get_var(4, r, c)
            
            # Adjacent positions that must be empty
            adj_positions = []
            if r > 0:  # Above
                adj_positions.append(get_var(1, r - 1, c))
            if r < BOARD_SIZE - 2:  # Below
                adj_positions.append(get_var(1, r + 2, c))
            if c < BOARD_SIZE - 1:  # Right
                adj_positions.append(get_var(1, r, c + 1))
            if c > 0:  # Left
                adj_positions.append(get_var(1, r, c - 1))
            if r < BOARD_SIZE - 1:  # Below right
                if c < BOARD_SIZE - 1:
                    adj_positions.append(get_var(1, r + 1, c + 1))
                if c > 0:  # Below left
                    adj_positions.append(get_var(1, r + 1, c - 1))
            
            # Add constraints
            for adj_sp in adj_positions:
                cnf.append([-pb_v, -adj_sp])
    
    # Submarine horizontal: SM_{h,i,j} -> (¬SP_{i,j-1} ∧ ¬SP_{i,j+3} ∧ ¬SP_{i+1,j} ∧ ¬SP_{i-1,j} ∧ ¬SP_{i+1,j-1} ∧ ¬SP_{i-1,j-1} ∧ ¬SP_{i+1,j+1} ∧ ¬SP_{i-1,j+1} ∧ ¬SP_{i+1,j+2} ∧ ¬SP_{i-1,j+2})
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE - 2):  # Horizontal placement needs c < 8
            sm_h = get_var(5, r, c)
            
            # Adjacent positions that must be empty
            adj_positions = []
            if c > 0:  # Left
                adj_positions.append(get_var(1, r, c - 1))
            if c < BOARD_SIZE - 3:  # Right
                adj_positions.append(get_var(1, r, c + 3))
            if r < BOARD_SIZE - 1:  # Below
                adj_positions.append(get_var(1, r + 1, c))
                if c > 0:  # Below left
                    adj_positions.append(get_var(1, r + 1, c - 1))
                if c < BOARD_SIZE - 1:  # Below right
                    adj_positions.append(get_var(1, r + 1, c + 1))
                if c < BOARD_SIZE - 2:  # Below middle right
                    adj_positions.append(get_var(1, r + 1, c + 2))
            if r > 0:  # Above
                adj_positions.append(get_var(1, r - 1, c))
                if c > 0:  # Above left
                    adj_positions.append(get_var(1, r - 1, c - 1))
                if c < BOARD_SIZE - 1:  # Above right
                    adj_positions.append(get_var(1, r - 1, c + 1))
                if c < BOARD_SIZE - 2:  # Above middle right
                    adj_positions.append(get_var(1, r - 1, c + 2))
            
            # Add constraints
            for adj_sp in adj_positions:
                cnf.append([-sm_h, -adj_sp])
    
    # Submarine vertical: SM_{v,i,j} -> (¬SP_{i-1,j} ∧ ¬SP_{i+3,j} ∧ ¬SP_{i,j+1} ∧ ¬SP_{i,j-1} ∧ ¬SP_{i-1,j+1} ∧ ¬SP_{i-1,j-1} ∧ ¬SP_{i+1,j+1} ∧ ¬SP_{i+1,j-1} ∧ ¬SP_{i+2,j+1} ∧ ¬SP_{i+2,j-1})
    for r in range(BOARD_SIZE - 2):  # Vertical placement needs r < 8
        for c in range(BOARD_SIZE):
            sm_v = get_var(6, r, c)
            
            # Adjacent positions that must be empty
            adj_positions = []
            if r > 0:  # Above
                adj_positions.append(get_var(1, r - 1, c))
            if r < BOARD_SIZE - 3:  # Below
                adj_positions.append(get_var(1, r + 3, c))
            if c < BOARD_SIZE - 1:  # Right
                adj_positions.append(get_var(1, r, c + 1))
            if c > 0:  # Left
                adj_positions.append(get_var(1, r, c - 1))
            if r > 0:  # Above right
                if c < BOARD_SIZE - 1:
                    adj_positions.append(get_var(1, r - 1, c + 1))
                if c > 0:  # Above left
                    adj_positions.append(get_var(1, r - 1, c - 1))
            if r < BOARD_SIZE - 1:  # Below right
                if c < BOARD_SIZE - 1:
                    adj_positions.append(get_var(1, r + 1, c + 1))
                if c > 0:  # Below left
                    adj_positions.append(get_var(1, r + 1, c - 1))
            if r < BOARD_SIZE - 2:  # Middle below right
                if c < BOARD_SIZE - 1:
                    adj_positions.append(get_var(1, r + 2, c + 1))
                if c > 0:  # Middle below left
                    adj_positions.append(get_var(1, r + 2, c - 1))
            
            # Add constraints
            for adj_sp in adj_positions:
                cnf.append([-sm_v, -adj_sp])
    
    return cnf

def main():
    print(f"Board Size: {BOARD_SIZE}")
    cnf = init_empty_board()
    # Note: add_random_boat creates conflicts with patrol boat constraints
    # cells = add_random_boat(cnf)
    cnf = add_patrol_boat_constraints(cnf)
    cnf = add_submarine_constraints(cnf)
    cnf = add_non_adjacent_constraints(cnf)
    return cnf




if __name__ == "__main__":
    main()
