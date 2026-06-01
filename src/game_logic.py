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

    Intelligent Algorithm:
      1. Check which ships have been sunk (patrol boat vs submarine)
      2. Find all unprocessed hits (hits not covered by sunk ships)
      3. For each unprocessed hit, determine likely ship orientation and length
      4. Prioritize shots in the most likely direction based on:
         - Which ships are still alive (1x2 patrol boat vs 1x3 submarine)
         - Hit patterns that suggest horizontal vs vertical orientation
         - Adjacent hits that form lines
    """
    unprocessed_hits = _get_unprocessed_hits(board_size, cnf)
    if not unprocessed_hits:
        return []

    sunk_status = _get_sunk_ships_status(board_size, cnf)
    unit_clauses = _get_unit_clause_set(cnf)
    
    # Get all current hits for pattern analysis
    all_hits = {(r, c) for r in range(board_size) for c in range(board_size)
                if get_var(board_size, 8, r, c) in unit_clauses}
    
    candidates = []
    seen = set()

    print(f"  Ship status: Patrol Boat sunk={sunk_status['patrol_boat']}, Submarine sunk={sunk_status['submarine']}")
    
    for (hr, hc) in unprocessed_hits:
        # Analyze hit patterns around this hit to determine likely orientation
        horizontal_hits = []
        vertical_hits = []
        
        # Check for adjacent hits in horizontal direction
        for dc in [-2, -1, 1, 2]:
            if 0 <= hc + dc < board_size and (hr, hc + dc) in all_hits:
                horizontal_hits.append((hr, hc + dc))
        
        # Check for adjacent hits in vertical direction  
        for dr in [-2, -1, 1, 2]:
            if 0 <= hr + dr < board_size and (hr + dr, hc) in all_hits:
                vertical_hits.append((hr + dr, hc))
        
        # Determine target ship length based on what's still alive
        target_lengths = []
        if not sunk_status['patrol_boat']:
            target_lengths.append(2)  # Looking for 1x2 patrol boat
        if not sunk_status['submarine']:
            target_lengths.append(3)  # Looking for 1x3 submarine
        
        # If no ships left to find, shouldn't happen but fallback
        if not target_lengths:
            target_lengths = [2, 3]
        
        print(f"    Analyzing hit at ({hr}, {hc}): horizontal_hits={horizontal_hits}, vertical_hits={vertical_hits}")
        print(f"    Target lengths: {target_lengths}")
        
        # Prioritize directions based on existing hit patterns and target ship lengths
        direction_priorities = []
        
        # If we have horizontal hits, prioritize horizontal expansion
        if horizontal_hits:
            # Find the extent of horizontal hits
            min_c = min(hc, min(c for r, c in horizontal_hits))
            max_c = max(hc, max(c for r, c in horizontal_hits))
            current_length = max_c - min_c + 1
            
            # Add horizontal neighbors if we haven't reached target length
            for target_len in target_lengths:
                if current_length < target_len:
                    # Try to extend left
                    if min_c - 1 >= 0:
                        direction_priorities.append(('horizontal', hr, min_c - 1, target_len))
                    # Try to extend right
                    if max_c + 1 < board_size:
                        direction_priorities.append(('horizontal', hr, max_c + 1, target_len))
        
        # If we have vertical hits, prioritize vertical expansion
        if vertical_hits:
            # Find the extent of vertical hits
            min_r = min(hr, min(r for r, c in vertical_hits))
            max_r = max(hr, max(r for r, c in vertical_hits))
            current_length = max_r - min_r + 1
            
            # Add vertical neighbors if we haven't reached target length
            for target_len in target_lengths:
                if current_length < target_len:
                    # Try to extend up
                    if min_r - 1 >= 0:
                        direction_priorities.append(('vertical', min_r - 1, hc, target_len))
                    # Try to extend down
                    if max_r + 1 < board_size:
                        direction_priorities.append(('vertical', max_r + 1, hc, target_len))
        
        # If no clear pattern yet, try all 4 directions with preference for longer ships first
        if not horizontal_hits and not vertical_hits:
            for target_len in sorted(target_lengths, reverse=True):  # Longer ships first
                # Horizontal directions
                direction_priorities.append(('horizontal', hr, hc - 1, target_len))
                direction_priorities.append(('horizontal', hr, hc + 1, target_len))
                # Vertical directions  
                direction_priorities.append(('vertical', hr - 1, hc, target_len))
                direction_priorities.append(('vertical', hr + 1, hc, target_len))
        
        # Add candidates based on priorities
        for direction, nr, nc, target_len in direction_priorities:
            # Check bounds
            if not (0 <= nr < board_size and 0 <= nc < board_size):
                continue
            # Skip if already shot or already added to candidates
            if (nr, nc) in shots_taken or (nr, nc) in seen:
                continue
            
            seen.add((nr, nc))
            candidates.append((nr, nc))
            print(f"      Added {direction} target at ({nr}, {nc}) for length {target_len}")

    print(f"  Intelligent hunt targets for unprocessed hits {unprocessed_hits}: {candidates}")
    return candidates


def simulate_game_intelligent(board_size, shots, truth_board, agent_board, use_gui=False):
    """Run a simulation using intelligent directional hunting strategy.

    Behavior:
      - Default mode: pick a random unshot cell.
      - After a hit, switch to "intelligent hunting" mode that:
        * Tracks which ships have been sunk (patrol boat vs submarine)
        * Analyzes hit patterns to determine likely ship orientation
        * Prioritizes shots based on remaining ship types and lengths
        * Uses directional shooting along likely ship axes
      - Game ends early if all ships are sunk.
    """
    # Visualize board before shots
    print("Board from the POV of the Truth")
    visualize_board(board_size, truth_board.cnf)

    shots_taken = set()
    shot_history = []
    
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

        # Try intelligent hunting first if there are unprocessed hits
        unprocessed_hits = _get_unprocessed_hits(board_size, agent_board.cnf)
        if unprocessed_hits:
            candidates = get_intelligent_hunt_targets(board_size, agent_board.cnf, shots_taken)
            if candidates:
                target = candidates[0]  # Take highest priority target
                print(f"Shot {shot_num}: Intelligent hunting target: {target} (hunting around unprocessed hits: {unprocessed_hits})")

        # Fallback to random if no hunting target was found.
        if not target:
            unshot = [(r, c) for r in range(board_size) for c in range(board_size)
                      if (r, c) not in shots_taken]
            if not unshot:
                print("All cells have been shot.")
                break
            target = random.choice(unshot)
            if unprocessed_hits:
                print(f"Shot {shot_num}: Random target: {target} (no valid hunt targets found, but unprocessed hits remain: {unprocessed_hits})")
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
      - After a hit, switch to "hunting" mode and use `get_hunt_targets` to find
        the next shot. If the SAT solver returns no candidates, fall back to random.
      - Once the ship covering the most recent hit is sunk (detected by the
        AllPartsSunk consequences propagating in the CNF, i.e. a Sunk variable
        becomes asserted), revert to random shooting.
      - Game ends early if all ships are sunk.
    """
    # Visualize board before shots
    print("Board from the POV of the Truth")
    visualize_board(board_size, truth_board.cnf)

    shots_taken = set()
    shot_history = []
    
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

        # Try hunting first if there are unprocessed hits (i.e., hits not yet sunk).
        unprocessed_hits = _get_unprocessed_hits(board_size, agent_board.cnf)
        if unprocessed_hits:
            candidates = get_simple_hunt_targets(board_size, agent_board.cnf, shots_taken)
            if candidates:
                target = random.choice(candidates)  # Randomly pick from available neighbors
                print(f"Shot {shot_num}: Hunting target: {target} (hunting around unprocessed hits: {unprocessed_hits})")

        # Fallback to random if no hunting target was found.
        if not target:
            unshot = [(r, c) for r in range(board_size) for c in range(board_size)
                      if (r, c) not in shots_taken]
            if not unshot:
                print("All cells have been shot.")
                break
            target = random.choice(unshot)
            if unprocessed_hits:
                print(f"Shot {shot_num}: Random target: {target} (no valid hunt targets found, but unprocessed hits remain: {unprocessed_hits})")
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
