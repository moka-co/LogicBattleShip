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


def _get_open_hits(board_size, cnf):
    """Returns a list of (r,c) for all Hit cells that are NOT yet covered by a Sunk variable.
    
    A hit is considered "open" if:
    1. The cell has been hit (Hit_{r,c} is asserted)
    2. The cell is not covered by any asserted Sunk variable
    
    This correctly handles the case where multiple ships are partially hit - 
    only the hits belonging to fully sunk ships are removed from the open hits list.
    """
    unit_clauses = _get_unit_clause_set(cnf)
    open_hits = []
    
    for r in range(board_size):
        for c in range(board_size):
            hit_var = get_var(board_size, 8, r, c)
            
            # Check if this cell has been hit
            if hit_var not in unit_clauses:
                continue
                
            # Check if this hit is covered by any sunk ship
            is_covered = False
            
            # Check all possible sunk ship variables that could cover this cell
            for sunk_type in [10, 11, 12, 13]:  # All sunk ship types
                if sunk_type == 10:  # Sunk PB horizontal
                    # PB_h at (sr,sc) covers (sr,sc) and (sr,sc+1)
                    # So (r,c) could be covered by PB_h at (r,c) or (r,c-1)
                    possible_origins = [(r, c), (r, c-1)]
                    valid_range = lambda sr, sc: 0 <= sr < board_size and 0 <= sc <= board_size - 2
                elif sunk_type == 11:  # Sunk PB vertical  
                    # PB_v at (sr,sc) covers (sr,sc) and (sr+1,sc)
                    # So (r,c) could be covered by PB_v at (r,c) or (r-1,c)
                    possible_origins = [(r, c), (r-1, c)]
                    valid_range = lambda sr, sc: 0 <= sr <= board_size - 2 and 0 <= sc < board_size
                elif sunk_type == 12:  # Sunk SM horizontal
                    # SM_h at (sr,sc) covers (sr,sc), (sr,sc+1), (sr,sc+2)  
                    # So (r,c) could be covered by SM_h at (r,c), (r,c-1), or (r,c-2)
                    possible_origins = [(r, c), (r, c-1), (r, c-2)]
                    valid_range = lambda sr, sc: 0 <= sr < board_size and 0 <= sc <= board_size - 3
                else:  # sunk_type == 13, Sunk SM vertical
                    # SM_v at (sr,sc) covers (sr,sc), (sr+1,sc), (sr+2,sc)
                    # So (r,c) could be covered by SM_v at (r,c), (r-1,c), or (r-2,c)  
                    possible_origins = [(r, c), (r-1, c), (r-2, c)]
                    valid_range = lambda sr, sc: 0 <= sr <= board_size - 3 and 0 <= sc < board_size
                
                # Check if any of these sunk variables are asserted
                for (sr, sc) in possible_origins:
                    if valid_range(sr, sc):
                        sunk_var = get_var(board_size, sunk_type, sr, sc)
                        if sunk_var in unit_clauses:
                            is_covered = True
                            break
                
                if is_covered:
                    break
            
            # If the hit is not covered by any sunk ship, it's an open hit
            if not is_covered:
                open_hits.append((r, c))
    
    return open_hits


def get_hunt_targets(board_size, cnf, shots_taken):
    """Returns a list of candidate (r,c) cells to shoot, prioritized for hunting.

    Algorithm:
      1. Find all "open hits": cells where Hit is asserted but no Sunk variable
         covering the cell has been asserted yet.
      2. For each open hit, enumerate the 4 orthogonal neighbors (N, S, E, W).
      3. For each unshot in-bounds neighbor, query Glucose3 with assumptions:
         - First, check if SP_{nr,nc} is FORCED (i.e. KB ∧ ¬SP_{nr,nc} is UNSAT).
           If so, return that cell immediately as the highest-priority target.
         - Otherwise, check if SP_{nr,nc} is POSSIBLE (i.e. KB ∧ SP_{nr,nc} is SAT).
           If so, add it to the candidate list.
      4. Returns either a single forced cell, the list of possible candidates, or
         an empty list if no logical hunting targets are available.
    """
    open_hits = _get_open_hits(board_size, cnf)
    if not open_hits:
        return []

    candidates = []
    seen = set()

    for (hr, hc) in open_hits:
        neighbors = [(hr - 1, hc), (hr + 1, hc), (hr, hc - 1), (hr, hc + 1)]
        for (nr, nc) in neighbors:
            if not (0 <= nr < board_size and 0 <= nc < board_size):
                continue
            if (nr, nc) in shots_taken or (nr, nc) in seen:
                continue
            seen.add((nr, nc))

            sp_var = get_var(board_size, 1, nr, nc)

            # Priority 1: Is SP_{nr,nc} FORCED? Check if KB ∧ ¬SP is UNSAT.
            with Glucose3(bootstrap_with=cnf.clauses) as solver:
                if not solver.solve(assumptions=[-sp_var]):
                    # Forced ship part: must shoot here.
                    print(f"  Found FORCED target at ({nr}, {nc}) for open hit ({hr}, {hc})")
                    return [(nr, nc)]

            # Priority 2: Is SP_{nr,nc} POSSIBLE? Check if KB ∧ SP is SAT.
            with Glucose3(bootstrap_with=cnf.clauses) as solver:
                if solver.solve(assumptions=[sp_var]):
                    candidates.append((nr, nc))
                    print(f"  Found POSSIBLE target at ({nr}, {nc}) for open hit ({hr}, {hc})")
            # If neither forced nor possible, it's impossible (¬SP entailed); skip.

    print(f"  Hunt targets for open hits {open_hits}: {candidates}")
    return candidates


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

        # Try hunting first if there are open hits (i.e., hits not yet sunk).
        open_hits = _get_open_hits(board_size, agent_board.cnf) # Use agent board 
        if open_hits:
            candidates = get_hunt_targets(board_size, agent_board.cnf, shots_taken)
            if candidates:
                target = candidates[0]
                print(f"Shot {shot_num}: Hunting target: {target} (continuing hunt for open hits: {open_hits})")

        # Fallback to random if no hunting target was found.
        if not target:
            unshot = [(r, c) for r in range(board_size) for c in range(board_size)
                      if (r, c) not in shots_taken]
            if not unshot:
                print("All cells have been shot.")
                break
            target = random.choice(unshot)
            if open_hits:
                print(f"Shot {shot_num}: Random target: {target} (no valid hunt targets found, but open hits remain: {open_hits})")
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
