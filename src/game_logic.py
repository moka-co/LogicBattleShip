import random
from pysat.solvers import Glucose3
from src.board import init_empty_board
from src.ship_types import *
from src.ship_logic import *
from src.utils import *
from src.gui import run_gui


class TruthBoardFactory:
    """
    A factory class responsible for initializing the Battleship game state.

    This class sets up the initial CNF formula by placing ships on the board,
    applying static game rules (shot/hit/miss constraints), and configuring
    the logic for sinking ships and their consequences.
    """
    def __init__(self, board_size):
        self.board_size = board_size
        self.occupied = set()
        self.cnf = init_empty_board(self.board_size)
        
        # Place ships physically on the board and add their constraints
        pb_factory = PatrolBoatFactory(self.board_size)
        sm_factory = SubmarineFactory(self.board_size)
        self.occupied = pb_factory.build(self.cnf, self.occupied)
        self.occupied = sm_factory.build(self.cnf, self.occupied)
        
        # Add Shot/Hit/Miss static constraints (dynamic unit clauses are added later
        # via `record_shot` during gameplay).
        self.cnf = add_shot_hit_miss_constraints(self.board_size, self.cnf)
        
        # Add Sinking Ships biconditionals and AllPartsSunk consequences
        self.cnf = add_sinking_constraints(self.board_size, self.cnf)
        self.cnf = add_all_parts_sunk_consequences(self.board_size, self.cnf)

class AgentBoardFactory:
    def __init__(self, board_size):
        self.board_size = board_size
        self.cnf = init_empty_board(self.board_size)
        
        # Add ship constraints (but don't place actual ships - agent must deduce locations)
        from src.ship_types import add_patrol_boat_constraints, add_patrol_boat_non_adjacent_constraints
        from src.ship_types import add_submarine_constraints, add_submarine_non_adjacent_constraints
        
        add_patrol_boat_constraints(self.board_size, self.cnf)
        add_patrol_boat_non_adjacent_constraints(self.board_size, self.cnf)
        add_submarine_constraints(self.board_size, self.cnf)
        add_submarine_non_adjacent_constraints(self.board_size, self.cnf)
        
        # Add Shot/Hit/Miss static constraints (dynamic unit clauses are added later
        # via `record_shot` during gameplay).
        self.cnf = add_shot_hit_miss_constraints(self.board_size, self.cnf)
        
        # Add Sinking Ships biconditionals and AllPartsSunk consequences
        self.cnf = add_sinking_constraints(self.board_size, self.cnf)
        self.cnf = add_all_parts_sunk_consequences(self.board_size, self.cnf)

def record_shot(board_size, cnf, r, c, was_hit):
    """Records a shot outcome by appending unit clauses to the CNF.

    This function is called dynamically during gameplay after each shot.
    The static constraints in `add_shot_hit_miss_constraints` will then
    propagate the consequences (e.g., Hit -> SP, Miss -> ¬SP) via the SAT solver.

    Args:
        board_size: the size of the board.
        cnf: the CNF knowledge base to update (mutated in place).
        r, c: the row and column of the shot tile.
        was_hit: True if the shot hit a ship part, False if it missed.
    """
    # Assert Shot_{r,c} (the tile has been shot)
    cnf.append([get_var(board_size, 7, r, c)])

    if was_hit:
        # Assert Hit_{r,c}
        cnf.append([get_var(board_size, 8, r, c)])
    else:
        # Assert Miss_{r,c}
        cnf.append([get_var(board_size, 9, r, c)])


def visualize_board(board_size, cnf):
    """Prints a simple text representation of the board."""
    print("Board Visualization:")
    # Create a set of unit clauses for faster lookup
    unit_clauses = {c[0] for c in cnf.clauses if len(c) == 1}
    
    for r in range(board_size):
        row_str = ""
        for c in range(board_size):
            # Check for Hit (8), Ship Part (1), or Miss (9)
            if get_var(board_size, 8, r, c) in unit_clauses:
                row_str += "[H]"
            elif get_var(board_size, 1, r, c) in unit_clauses:
                row_str += "[S]"
            elif get_var(board_size, 9, r, c) in unit_clauses:
                row_str += "[0]"
            else:
                row_str += "[ ]"
        print(row_str)


def is_ship_part(board_size, cnf, r, c):
    """Checks if a cell contains a ship part by inspecting the unit clauses."""
    unit_clauses = {clause[0] for clause in cnf.clauses if len(clause) == 1}
    return get_var(board_size, 1, r, c) in unit_clauses


def _get_unit_clause_set(cnf):
    """Returns the set of asserted literals (unit clauses) in the CNF."""
    return {clause[0] for clause in cnf.clauses if len(clause) == 1}


def _sunk_covers_cell(board_size, sunk_type, sr, sc, r, c):
    """Returns True if the Sunk variable of given type and origin (sr,sc) covers
    the cell (r,c).

    Sunk variable types:
      - 10: Sunk_PB_h at (sr,sc) covers (sr,sc) and (sr, sc+1)
      - 11: Sunk_PB_v at (sr,sc) covers (sr,sc) and (sr+1, sc)
      - 12: Sunk_SM_h at (sr,sc) covers (sr,sc), (sr, sc+1), (sr, sc+2)
      - 13: Sunk_SM_v at (sr,sc) covers (sr,sc), (sr+1, sc), (sr+2, sc)
    """
    if sunk_type == 10:
        return r == sr and (c == sc or c == sc + 1)
    if sunk_type == 11:
        return c == sc and (r == sr or r == sr + 1)
    if sunk_type == 12:
        return r == sr and (c == sc or c == sc + 1 or c == sc + 2)
    if sunk_type == 13:
        return c == sc and (r == sr or r == sr + 1 or r == sr + 2)
    return False


def _is_cell_in_sunk_ship(board_size, cnf, r, c):
    """Returns True if (r,c) is covered by any asserted Sunk variable."""
    unit_clauses = _get_unit_clause_set(cnf)
    # Iterate over every possible Sunk variable; if it is asserted and covers (r,c), return True.
    for sunk_type in (10, 11, 12, 13):
        # Determine valid ranges for the origin (sr, sc) of this Sunk variable.
        if sunk_type == 10:  # PB horizontal: needs sc+1 in bounds
            r_range = range(board_size)
            c_range = range(board_size - 1)
        elif sunk_type == 11:  # PB vertical: needs sr+1 in bounds
            r_range = range(board_size - 1)
            c_range = range(board_size)
        elif sunk_type == 12:  # SM horizontal: needs sc+2 in bounds
            r_range = range(board_size)
            c_range = range(board_size - 2)
        else:  # 13: SM vertical: needs sr+2 in bounds
            r_range = range(board_size - 2)
            c_range = range(board_size)

        for sr in r_range:
            for sc in c_range:
                sunk_var = get_var(board_size, sunk_type, sr, sc)
                if sunk_var in unit_clauses and _sunk_covers_cell(board_size, sunk_type, sr, sc, r, c):
                    return True
    return False


def _get_unprocessed_hits(board_size, cnf):
    """Returns a list of (r,c) for all Hit cells that are NOT yet covered by a Sunk variable.
    
    Simple logic: a hit is unprocessed if the cell has been hit but is not covered 
    by any asserted Sunk variable (meaning the ship is not fully sunk yet).
    """
    unit_clauses = _get_unit_clause_set(cnf)
    unprocessed_hits = []
    
    for r in range(board_size):
        for c in range(board_size):
            hit_var = get_var(board_size, 8, r, c)
            
            # Check if this cell has been hit
            if hit_var not in unit_clauses:
                continue
                
            # Check if this hit is covered by any sunk ship using the existing helper
            if not _is_cell_in_sunk_ship(board_size, cnf, r, c):
                unprocessed_hits.append((r, c))
    
    return unprocessed_hits


def get_simple_hunt_targets(board_size, cnf, shots_taken):
    """Returns a list of candidate (r,c) cells to shoot using simple neighbor enumeration.

    Simple Algorithm:
      1. Find all unprocessed hits (hits not covered by sunk ships)
      2. For each unprocessed hit, get its 4 orthogonal neighbors (N, S, E, W)
      3. Return all unshot, in-bounds neighbors as candidates
      4. No SAT solver queries - just simple neighbor enumeration
    """
    unprocessed_hits = _get_unprocessed_hits(board_size, cnf)
    if not unprocessed_hits:
        return []

    candidates = []
    seen = set()

    for (hr, hc) in unprocessed_hits:
        neighbors = [(hr - 1, hc), (hr + 1, hc), (hr, hc - 1), (hr, hc + 1)]
        for (nr, nc) in neighbors:
            # Check bounds
            if not (0 <= nr < board_size and 0 <= nc < board_size):
                continue
            # Skip if already shot or already added to candidates
            if (nr, nc) in shots_taken or (nr, nc) in seen:
                continue
            
            seen.add((nr, nc))
            candidates.append((nr, nc))

    print(f"  Simple hunt targets for unprocessed hits {unprocessed_hits}: {candidates}")
    return candidates


def _get_sunk_ships_status(board_size, cnf):
    """Returns a dictionary indicating which ship types have been sunk.
    
    Returns:
        dict: {'patrol_boat': bool, 'submarine': bool}
    """
    unit_clauses = _get_unit_clause_set(cnf)
    
    # Check if any patrol boat sunk variable is asserted
    patrol_boat_sunk = False
    for r in range(board_size):
        for c in range(board_size - 1):  # PB horizontal
            if get_var(board_size, 10, r, c) in unit_clauses:
                patrol_boat_sunk = True
                break
        if patrol_boat_sunk:
            break
        for c in range(board_size):
            if r < board_size - 1:  # PB vertical
                if get_var(board_size, 11, r, c) in unit_clauses:
                    patrol_boat_sunk = True
                    break
        if patrol_boat_sunk:
            break
    
    # Check if any submarine sunk variable is asserted
    submarine_sunk = False
    for r in range(board_size):
        for c in range(board_size - 2):  # SM horizontal
            if get_var(board_size, 12, r, c) in unit_clauses:
                submarine_sunk = True
                break
        if submarine_sunk:
            break
        for c in range(board_size):
            if r < board_size - 2:  # SM vertical
                if get_var(board_size, 13, r, c) in unit_clauses:
                    submarine_sunk = True
                    break
        if submarine_sunk:
            break
    
    return {'patrol_boat': patrol_boat_sunk, 'submarine': submarine_sunk}


def get_intelligent_hunt_targets(board_size, cnf, shots_taken):
    """Returns a list of candidate (r,c) cells using intelligent directional hunting.

    Semi-Omniscient Algorithm:
      1. Find all unprocessed hits (hits not covered by sunk ships)
      2. Check which ship types have been sunk (observable game state)
      3. For each unprocessed hit, analyze hit patterns and infer likely ship types
      4. Prioritize shots based on:
         - Adjacent hits that form lines (indicating orientation)
         - Misses that constrain ship placement
         - Known sunk ships to determine remaining ship types
    """
    unprocessed_hits = _get_unprocessed_hits(board_size, cnf)
    if not unprocessed_hits:
        return []

    unit_clauses = _get_unit_clause_set(cnf)
    sunk_status = _get_sunk_ships_status(board_size, cnf)
    
    # Get all current hits and misses for pattern analysis
    all_hits = {(r, c) for r in range(board_size) for c in range(board_size)
                if get_var(board_size, 8, r, c) in unit_clauses}
    all_misses = {(r, c) for r in range(board_size) for c in range(board_size)
                  if get_var(board_size, 9, r, c) in unit_clauses}
    
    candidates = []
    seen = set()

    print(f"  Analyzing {len(unprocessed_hits)} unprocessed hits using observable patterns")
    print(f"  Known sunk ships: Patrol Boat={sunk_status['patrol_boat']}, Submarine={sunk_status['submarine']}")
    
    for (hr, hc) in unprocessed_hits:
        # Find adjacent hits to determine orientation
        adjacent_horizontal = []
        adjacent_vertical = [] 
        
        # Check for immediately adjacent hits (distance 1)
        for dc in [-1, 1]:
            if 0 <= hc + dc < board_size and (hr, hc + dc) in all_hits:
                adjacent_horizontal.append((hr, hc + dc))
        
        for dr in [-1, 1]:
            if 0 <= hr + dr < board_size and (hr + dr, hc) in all_hits:
                adjacent_vertical.append((hr + dr, hc))
        
        print(f"    Hit at ({hr}, {hc}): adjacent_horizontal={adjacent_horizontal}, adjacent_vertical={adjacent_vertical}")
        
        # Determine what ship types we're still looking for
        possible_ship_lengths = []
        if not sunk_status['patrol_boat']:
            possible_ship_lengths.append(2)  # Still need to find patrol boat (length 2)
        if not sunk_status['submarine']:
            possible_ship_lengths.append(3)  # Still need to find submarine (length 3)
        
        # If all ships are sunk, this shouldn't happen but fallback
        if not possible_ship_lengths:
            possible_ship_lengths = [2, 3]
        
        print(f"      Looking for ships of lengths: {possible_ship_lengths}")
        
        # Determine orientation based on adjacent hits
        if adjacent_horizontal and not adjacent_vertical:
            # Clear horizontal pattern - extend horizontally
            all_horizontal = [(hr, hc)] + adjacent_horizontal
            min_c = min(c for r, c in all_horizontal)
            max_c = max(c for r, c in all_horizontal)
            current_length = max_c - min_c + 1
            
            # Try to extend the horizontal line, but only if we need longer ships
            candidates_to_add = []
            for target_length in possible_ship_lengths:
                if current_length < target_length:
                    if min_c - 1 >= 0 and (hr, min_c - 1) not in shots_taken:
                        candidates_to_add.append((hr, min_c - 1))
                    if max_c + 1 < board_size and (hr, max_c + 1) not in shots_taken:
                        candidates_to_add.append((hr, max_c + 1))
            
            print(f"      Horizontal pattern (length {current_length}), extending: {candidates_to_add}")
            
        elif adjacent_vertical and not adjacent_horizontal:
            # Clear vertical pattern - extend vertically
            all_vertical = [(hr, hc)] + adjacent_vertical
            min_r = min(r for r, c in all_vertical)
            max_r = max(r for r, c in all_vertical)
            current_length = max_r - min_r + 1
            
            # Try to extend the vertical line, but only if we need longer ships
            candidates_to_add = []
            for target_length in possible_ship_lengths:
                if current_length < target_length:
                    if min_r - 1 >= 0 and (min_r - 1, hc) not in shots_taken:
                        candidates_to_add.append((min_r - 1, hc))
                    if max_r + 1 < board_size and (max_r + 1, hc) not in shots_taken:
                        candidates_to_add.append((max_r + 1, hc))
            
            print(f"      Vertical pattern (length {current_length}), extending: {candidates_to_add}")
            
        else:
            # No clear pattern or conflicting patterns - try all 4 directions
            # But use miss information to constrain choices and prioritize by ship length needs
            candidates_to_add = []
            
            # Check each direction, avoiding areas blocked by misses
            directions = [
                (hr - 1, hc, 'up'),
                (hr + 1, hc, 'down'), 
                (hr, hc - 1, 'left'),
                (hr, hc + 1, 'right')
            ]
            
            for nr, nc, direction_name in directions:
                if not (0 <= nr < board_size and 0 <= nc < board_size):
                    continue
                if (nr, nc) in shots_taken:
                    continue
                
                # For horizontal directions, check if vertical neighbors are misses
                if direction_name in ['left', 'right']:
                    if ((hr - 1, hc) in all_misses and (hr + 1, hc) in all_misses):
                        # Vertical neighbors are misses, so this must be horizontal ship
                        candidates_to_add.append((nr, nc))
                        print(f"      Direction {direction_name} prioritized due to vertical misses")
                    elif (hr - 1, hc) not in all_misses and (hr + 1, hc) not in all_misses:
                        # No vertical constraints, add as possibility
                        candidates_to_add.append((nr, nc))
                
                # For vertical directions, check if horizontal neighbors are misses  
                elif direction_name in ['up', 'down']:
                    if ((hr, hc - 1) in all_misses and (hr, hc + 1) in all_misses):
                        # Horizontal neighbors are misses, so this must be vertical ship
                        candidates_to_add.append((nr, nc))
                        print(f"      Direction {direction_name} prioritized due to horizontal misses")
                    elif (hr, hc - 1) not in all_misses and (hr, hc + 1) not in all_misses:
                        # No horizontal constraints, add as possibility
                        candidates_to_add.append((nr, nc))
            
            print(f"      No clear pattern, trying constrained directions: {candidates_to_add}")
        
        # Add candidates, avoiding duplicates
        for nr, nc in candidates_to_add:
            if (nr, nc) not in seen:
                seen.add((nr, nc))
                candidates.append((nr, nc))

    print(f"  Intelligent hunt targets for unprocessed hits {unprocessed_hits}: {candidates}")
    return candidates


def simulate_game_intelligent(board_size, shots, truth_board, agent_board, use_gui=False):
    """Run a simulation using intelligent directional hunting strategy.

    Behavior:
      - Default mode: pick a random unshot cell.
      - After a hit, switch to "intelligent hunting" mode and keep shooting from
        intelligent candidates until no more candidates exist or all ships are sunk.
      - Only revert to random shooting when no hunt targets are available.
      - Game ends early if all ships are sunk.
    """
    # Visualize board before shots
    print("Board from the POV of the Truth")
    visualize_board(board_size, truth_board.cnf)

    shots_taken = set()
    shot_history = []
    hunt_candidates = []  # Persistent list of intelligent hunting candidates
    
    # Get all ship positions from truth board for win condition check
    truth_unit_clauses = _get_unit_clause_set(truth_board.cnf)
    all_ship_cells = {(r, c) for r in range(board_size) for c in range(board_size)
                      if get_var(board_size, 1, r, c) in truth_unit_clauses}
    
    print(f"Total ship cells to find: {len(all_ship_cells)}")

    for shot_num in range(1, shots + 1):
        target = None

        # Check win condition - all ships sunk
        agent_unit_clauses = _get_unit_clause_set(agent_board.cnf)
        hit_cells = {(r, c) for r in range(board_size) for c in range(board_size)
                     if get_var(board_size, 8, r, c) in agent_unit_clauses}
        
        if all_ship_cells.issubset(hit_cells):
            print(f"\n🎉 VICTORY! All ships sunk in {len(shot_history)} shots!")
            break

        # Update hunt candidates based on current unprocessed hits
        unprocessed_hits = _get_unprocessed_hits(board_size, agent_board.cnf)
        if unprocessed_hits:
            # Get fresh intelligent candidates and merge with existing ones
            new_candidates = get_intelligent_hunt_targets(board_size, agent_board.cnf, shots_taken)
            # Remove already shot candidates and add new ones
            hunt_candidates = [c for c in hunt_candidates if c not in shots_taken]
            for candidate in new_candidates:
                if candidate not in hunt_candidates and candidate not in shots_taken:
                    hunt_candidates.append(candidate)
        else:
            # No unprocessed hits, clear hunt candidates
            hunt_candidates = []

        # Try intelligent hunting first if we have hunt candidates
        if hunt_candidates:
            target = random.choice(hunt_candidates)
            hunt_candidates.remove(target)  # Remove from candidates after selection
            print(f"Shot {shot_num}: Intelligent hunting target: {target} (from candidates, {len(hunt_candidates)} remaining)")

        # Fallback to random if no hunting target was found
        if not target:
            unshot = [(r, c) for r in range(board_size) for c in range(board_size)
                      if (r, c) not in shots_taken]
            if not unshot:
                print("All cells have been shot.")
                break
            target = random.choice(unshot)
            if unprocessed_hits:
                print(f"Shot {shot_num}: Random target: {target} (no hunt candidates available, but unprocessed hits remain: {unprocessed_hits})")
            else:
                print(f"Shot {shot_num}: Random target: {target}")

        r, c = target
        shots_taken.add((r, c))

        was_hit = is_ship_part(board_size, truth_board.cnf, r, c)
        record_shot(board_size, agent_board.cnf, r, c, was_hit)
        shot_history.append((r, c, was_hit))
        
        hit_status = "HIT! 🎯" if was_hit else "Miss"
        print(f"  Result: ({r}, {c}) - {hit_status}")
        
        # Show progress
        current_hits = len([h for h in shot_history if h[2]])
        print(f"  Progress: {current_hits}/{len(all_ship_cells)} ship cells found")

    # Final status
    final_hits = len([h for h in shot_history if h[2]])
    if final_hits == len(all_ship_cells):
        print(f"\n🏆 GAME WON! All {len(all_ship_cells)} ship cells destroyed in {len(shot_history)} shots!")
    else:
        print(f"\n📊 Game ended: {final_hits}/{len(all_ship_cells)} ship cells found in {len(shot_history)} shots")

    # Visualize board after shots
    print("\n" + "="*50)
    print("FINAL BOARDS:")
    print("="*50)
    print("Truth board (actual ship positions):")
    visualize_board(board_size, truth_board.cnf)
    print("\nAgent board (discovered information):")
    visualize_board(board_size, agent_board.cnf)

    if use_gui:
        run_gui(board_size, truth_board.cnf, shot_history)

    return truth_board.cnf


def simulate_game(board_size, shots, truth_board, agent_board, use_gui=False):
    """Run a simulation: random by default, switching to SAT-based hunting after a hit.

    Behavior:
      - Default mode: pick a random unshot cell.
      - After a hit, switch to "hunting" mode and keep shooting from hunt candidates
        until no more candidates exist or all ships are sunk.
      - Only revert to random shooting when no hunt targets are available.
      - Game ends early if all ships are sunk.
    """
    # Visualize board before shots
    print("Board from the POV of the Truth")
    visualize_board(board_size, truth_board.cnf)

    shots_taken = set()
    shot_history = []
    hunt_candidates = []  # Persistent list of hunting candidates
    
    # Get all ship positions from truth board for win condition check
    truth_unit_clauses = _get_unit_clause_set(truth_board.cnf)
    all_ship_cells = {(r, c) for r in range(board_size) for c in range(board_size)
                      if get_var(board_size, 1, r, c) in truth_unit_clauses}
    
    print(f"Total ship cells to find: {len(all_ship_cells)}")

    for shot_num in range(1, shots + 1):
        target = None

        # Check win condition - all ships sunk
        agent_unit_clauses = _get_unit_clause_set(agent_board.cnf)
        hit_cells = {(r, c) for r in range(board_size) for c in range(board_size)
                     if get_var(board_size, 8, r, c) in agent_unit_clauses}
        
        if all_ship_cells.issubset(hit_cells):
            print(f"\n🎉 VICTORY! All ships sunk in {len(shot_history)} shots!")
            break

        # Update hunt candidates based on current unprocessed hits
        unprocessed_hits = _get_unprocessed_hits(board_size, agent_board.cnf)
        if unprocessed_hits:
            # Get fresh candidates and merge with existing ones
            new_candidates = get_simple_hunt_targets(board_size, agent_board.cnf, shots_taken)
            # Remove already shot candidates and add new ones
            hunt_candidates = [c for c in hunt_candidates if c not in shots_taken]
            for candidate in new_candidates:
                if candidate not in hunt_candidates and candidate not in shots_taken:
                    hunt_candidates.append(candidate)
        else:
            # No unprocessed hits, clear hunt candidates
            hunt_candidates = []

        # Try hunting first if we have hunt candidates
        if hunt_candidates:
            target = random.choice(hunt_candidates)
            hunt_candidates.remove(target)  # Remove from candidates after selection
            print(f"Shot {shot_num}: Hunting target: {target} (from candidates, {len(hunt_candidates)} remaining)")

        # Fallback to random if no hunting target was found
        if not target:
            unshot = [(r, c) for r in range(board_size) for c in range(board_size)
                      if (r, c) not in shots_taken]
            if not unshot:
                print("All cells have been shot.")
                break
            target = random.choice(unshot)
            if unprocessed_hits:
                print(f"Shot {shot_num}: Random target: {target} (no hunt candidates available, but unprocessed hits remain: {unprocessed_hits})")
            else:
                print(f"Shot {shot_num}: Random target: {target}")

        r, c = target
        shots_taken.add((r, c))

        was_hit = is_ship_part(board_size, truth_board.cnf, r, c)
        record_shot(board_size, agent_board.cnf, r, c, was_hit)
        shot_history.append((r, c, was_hit))
        
        hit_status = "HIT! 🎯" if was_hit else "Miss"
        print(f"  Result: ({r}, {c}) - {hit_status}")
        
        # Show progress
        current_hits = len([h for h in shot_history if h[2]])
        print(f"  Progress: {current_hits}/{len(all_ship_cells)} ship cells found")

    # Final status
    final_hits = len([h for h in shot_history if h[2]])
    if final_hits == len(all_ship_cells):
        print(f"\n🏆 GAME WON! All {len(all_ship_cells)} ship cells destroyed in {len(shot_history)} shots!")
    else:
        print(f"\n📊 Game ended: {final_hits}/{len(all_ship_cells)} ship cells found in {len(shot_history)} shots")

    # Visualize board after shots
    print("\n" + "="*50)
    print("FINAL BOARDS:")
    print("="*50)
    print("Truth board (actual ship positions):")
    visualize_board(board_size, truth_board.cnf)
    print("\nAgent board (discovered information):")
    visualize_board(board_size, agent_board.cnf)

    if use_gui:
        run_gui(board_size, truth_board.cnf, shot_history)

    return truth_board.cnf
