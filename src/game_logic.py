import random
from pysat.solvers import Glucose3
from src.ship_types import *
from src.ship_logic import *
from src.utils import *
from src.gui import run_gui


def _get_unprocessed_hits(board_size, cnf):
        unit_clauses = _get_unit_clause_set(cnf)
        sunk_covered = _get_sunk_covered_cells(board_size, cnf)
        return [(r, c) for r in range(board_size) for c in range(board_size)
                if get_var(board_size, 8, r, c) in unit_clauses and (r, c) not in sunk_covered]

def record_shot(board_size, cnf, r, c, was_hit):
    """Records a shot outcome by appending unit clauses to the CNF."""
    if not (0 <= r < board_size and 0 <= c < board_size):
        raise ValueError(f"Shot ({r}, {c}) is out of bounds for board size {board_size}")
    shot_var = get_var(board_size, 7, r, c)
    unit_clauses = _get_unit_clause_set(cnf)
    if shot_var in unit_clauses:
        raise ValueError(f"Cell ({r}, {c}) has already been shot")
    cnf.append([shot_var])
    if was_hit:
        cnf.append([get_var(board_size, 8, r, c)])
    else:
        cnf.append([get_var(board_size, 9, r, c)])


def visualize_board(board_size, cnf):
    """Prints a simple text representation of the board."""
    print("Board Visualization:")
    unit_clauses = {c[0] for c in cnf.clauses if len(c) == 1}
    for r in range(board_size):
        row_str = ""
        for c in range(board_size):
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
    unit_clauses = {clause[0] for clause in cnf.clauses if len(clause) == 1}
    return get_var(board_size, 1, r, c) in unit_clauses


def _get_unit_clause_set(cnf):
    return {clause[0] for clause in cnf.clauses if len(clause) == 1}


def _sunk_covers_cell(board_size, sunk_type, sr, sc, r, c):
    if sunk_type == 10:
        return r == sr and (c == sc or c == sc + 1)
    if sunk_type == 11:
        return c == sc and (r == sr or r == sr + 1)
    if sunk_type == 12:
        return r == sr and (c == sc or c == sc + 1 or c == sc + 2)
    if sunk_type == 13:
        return c == sc and (r == sr or r == sr + 1 or r == sr + 2)
    if sunk_type == 16:
        return r == sr and sc <= c <= sc + 3
    if sunk_type == 17:
        return c == sc and sr <= r <= sr + 3
    if sunk_type == 19:
        return sr <= r <= sr + 1 and sc <= c <= sc + 1
    return False


def _get_sunk_covered_cells(board_size, cnf):
    """Precomputes and returns the set of all cells covered by asserted Sunk variables.
    
    This replaces the per-cell _is_cell_in_sunk_ship scan with a single O(sunk_positions)
    pass, after which membership checks are O(1).
    """
    unit_clauses = _get_unit_clause_set(cnf)
    covered = set()
    for sunk_type in (10, 11, 12, 13, 16, 17, 19):
        if sunk_type == 10:
            r_range, c_range = range(board_size), range(board_size - 1)
        elif sunk_type == 11:
            r_range, c_range = range(board_size - 1), range(board_size)
        elif sunk_type == 12:
            r_range, c_range = range(board_size), range(board_size - 2)
        elif sunk_type == 13:
            r_range, c_range = range(board_size - 2), range(board_size)
        elif sunk_type == 16:
            r_range, c_range = range(board_size), range(board_size - 3)
        elif sunk_type == 17:
            r_range, c_range = range(board_size - 3), range(board_size)
        else:
            r_range, c_range = range(board_size - 1), range(board_size - 1)
        for sr in r_range:
            for sc in c_range:
                sunk_var = get_var(board_size, sunk_type, sr, sc)
                if sunk_var in unit_clauses:
                    # Add all cells this sunk ship covers
                    if sunk_type == 10:
                        covered.update([(sr, sc), (sr, sc + 1)])
                    elif sunk_type == 11:
                        covered.update([(sr, sc), (sr + 1, sc)])
                    elif sunk_type == 12:
                        covered.update([(sr, sc), (sr, sc + 1), (sr, sc + 2)])
                    elif sunk_type == 13:
                        covered.update([(sr, sc), (sr + 1, sc), (sr + 2, sc)])
                    elif sunk_type == 16:
                        covered.update([(sr, sc + k) for k in range(4)])
                    elif sunk_type == 17:
                        covered.update([(sr + k, sc) for k in range(4)])
                    elif sunk_type == 19:
                        covered.update([(sr + dr, sc + dc) for dr in range(2) for dc in range(2)])
    return covered


def _is_cell_in_sunk_ship(board_size, cnf, r, c):
    """Legacy wrapper — prefer _get_sunk_covered_cells for batch checks."""
    return (r, c) in _get_sunk_covered_cells(board_size, cnf)


def get_simple_hunt_targets(board_size, cnf, shots_taken):
    unprocessed_hits = _get_unprocessed_hits(board_size, cnf)
    if not unprocessed_hits:
        return []
    candidates = []
    seen = set()
    for (hr, hc) in unprocessed_hits:
        neighbors = [
            (hr - 1, hc), (hr + 1, hc), (hr, hc - 1), (hr, hc + 1),
            (hr - 1, hc - 1), (hr - 1, hc + 1), (hr + 1, hc - 1), (hr + 1, hc + 1)
        ]
        for (nr, nc) in neighbors:
            if not (0 <= nr < board_size and 0 <= nc < board_size):
                continue
            if (nr, nc) in shots_taken or (nr, nc) in seen:
                continue
            seen.add((nr, nc))
            candidates.append((nr, nc))
    return candidates


def _get_sunk_ships_status(board_size, cnf):
    unit_clauses = _get_unit_clause_set(cnf)
    patrol_boat_sunk = any(get_var(board_size, 10, r, c) in unit_clauses for r in range(board_size) for c in range(board_size - 1)) or \
                       any(get_var(board_size, 11, r, c) in unit_clauses for r in range(board_size - 1) for c in range(board_size))
    submarine_sunk = any(get_var(board_size, 12, r, c) in unit_clauses for r in range(board_size) for c in range(board_size - 2)) or \
                     any(get_var(board_size, 13, r, c) in unit_clauses for r in range(board_size - 2) for c in range(board_size))
    battleship_sunk = any(get_var(board_size, 16, r, c) in unit_clauses for r in range(board_size) for c in range(board_size - 3)) or \
                      any(get_var(board_size, 17, r, c) in unit_clauses for r in range(board_size - 3) for c in range(board_size))
    carrier_sunk = any(get_var(board_size, 19, r, c) in unit_clauses for r in range(board_size - 1) for c in range(board_size - 1))
    return {'patrol_boat': patrol_boat_sunk, 'submarine': submarine_sunk, 'battleship': battleship_sunk, 'carrier': carrier_sunk}


def get_intelligent_hunt_targets(board_size, cnf, shots_taken):
    """Uses SAT solver to find logically consistent or forced ship parts near open hits."""
    unprocessed_hits = _get_unprocessed_hits(board_size, cnf)
    if not unprocessed_hits:
        return []

    with Glucose3() as solver:
        for clause in cnf.clauses:
            solver.add_clause(clause)

        candidates = []
        forced_targets = []
        seen = set()

        for (hr, hc) in unprocessed_hits:
            # For Carrier (2x2) and others, check all 8 neighbors
            neighbors = [
                (hr + dr, hc + dc) 
                for dr in [-1, 0, 1] for dc in [-1, 0, 1] 
                if not (dr == 0 and dc == 0)
            ]
            
            for nr, nc in neighbors:
                if not (0 <= nr < board_size and 0 <= nc < board_size):
                    continue
                if (nr, nc) in shots_taken or (nr, nc) in seen:
                    continue
                
                seen.add((nr, nc))
                sp_var = get_var(board_size, 1, nr, nc)
                
                # Priority 1: Is this cell FORCED to be a ship part? (KB |= SP)
                # Check if KB & ~SP is UNSAT
                if not solver.solve(assumptions=[-sp_var]):
                    forced_targets.append((nr, nc))
                # Priority 2: Is this cell CONSISTENT with being a ship part? (KB & SP is SAT)
                elif solver.solve(assumptions=[sp_var]):
                    candidates.append((nr, nc))

    return forced_targets if forced_targets else candidates


def get_checkerboard_targets(board_size, shots_taken):
    """Returns a list of unshot cells in a checkerboard pattern with spacing of 2.
    
    The pattern targets cells where (r + c) is even, ensuring that any ship of
    length >= 2 must overlap at least one of these cells.
    """
    candidates = []
    for r in range(board_size):
        for c in range(board_size):
            if (r + c) % 2 == 0 and (r, c) not in shots_taken:
                candidates.append((r, c))
    return candidates


class BattleshipStrategy:
    def get_hunt_candidates(self, board_size, cnf, shots_taken):
        raise NotImplementedError


class BattleshipSimpleRandomStrategy(BattleshipStrategy):
    def get_hunt_candidates(self, board_size, cnf, shots_taken):
        hunt_candidates = get_simple_hunt_targets(board_size, cnf, shots_taken)
        target = random.choice(hunt_candidates) if hunt_candidates else None
        
        if not target:
            unshot = [(r, c) for r in range(board_size) for c in range(board_size) if (r, c) not in shots_taken]
            if not unshot: return None, False
            target = random.choice(unshot)
            
        return target, True


class BattleshipIntelligentRandomStrategy(BattleshipStrategy):
    def get_hunt_candidates(self, board_size, cnf, shots_taken):
        hunt_candidates = get_intelligent_hunt_targets(board_size, cnf, shots_taken)
        target = random.choice(hunt_candidates) if hunt_candidates else None
        
        if not target:
            unshot = [(r, c) for r in range(board_size) for c in range(board_size) if (r, c) not in shots_taken]
            if not unshot: return None, False
            target = random.choice(unshot)
            
        return target, True


class BattleshipCheckerboardIntelligentStrategy(BattleshipStrategy):
    """Strategy that uses a checkerboard search pattern until a ship part is hit,
    then switches to intelligent hunt targets to finish off the ship.
    """
    def get_hunt_candidates(self, board_size, cnf, shots_taken):
        # If there are unprocessed hits (ship struck but not sunk), use intelligent hunting
        hunt_candidates = get_intelligent_hunt_targets(board_size, cnf, shots_taken)
        if hunt_candidates:
            target = random.choice(hunt_candidates)
            return target, True
        
        # Otherwise, search using a checkerboard pattern
        checkerboard_candidates = get_checkerboard_targets(board_size, shots_taken)
        if checkerboard_candidates:
            target = random.choice(checkerboard_candidates)
            return target, True
        
        # Fallback: pick any unshot cell
        unshot = [(r, c) for r in range(board_size) for c in range(board_size) if (r, c) not in shots_taken]
        if not unshot:
            return None, False
        target = random.choice(unshot)
        return target, True


class BaseSimulateGame:
    def __init__(self, board_size, shots, truth_board, agent_board, use_gui=False):
        self.board_size = board_size
        self.truth_board = truth_board
        self.agent_board = agent_board
        self.shots = shots
        self.use_gui = use_gui
        self.shots_taken = set()
        self.shot_history = []
        self.simulate()

    def _get_unit_clause_set(self, cnf):
        return {clause[0] for clause in cnf.clauses if len(clause) == 1}

    def _get_unprocessed_hits(self, cnf):
        return [(r, c) for r in range(self.board_size) for c in range(self.board_size)
                if get_var(self.board_size, 8, r, c) in self._get_unit_clause_set(cnf) and not _is_cell_in_sunk_ship(self.board_size, cnf, r, c)]

    def simulate(self):
        raise NotImplementedError("Subclasses must implement simulate()")

    def _all_ships_sunk(self, all_ship_cells):
        """Returns True if every ship cell has been hit."""
        hit_cells = {(r, c) for r, c, was_hit in self.shot_history if was_hit}
        return all_ship_cells.issubset(hit_cells)

    def finalize_game(self, all_ship_cells):
        final_hits = len([h for h in self.shot_history if h[2]])
        print(f"\n📊 Game ended: {final_hits}/{len(all_ship_cells)} ship cells found in {len(self.shot_history)} shots")
        visualize_board(self.board_size, self.truth_board.cnf)
        if self.use_gui:
            run_gui(self.board_size, self.truth_board.cnf, self.shot_history)


class SimulateSimpleGame(BaseSimulateGame):
    def simulate(self):
        strategy = BattleshipSimpleRandomStrategy()
        all_ship_cells = {(r, c) for r in range(self.board_size) for c in range(self.board_size)
                          if get_var(self.board_size, 1, r, c) in self._get_unit_clause_set(self.truth_board.cnf)}
        
        for shot_num in range(1, self.shots + 1):
            if self._all_ships_sunk(all_ship_cells):
                print(f"🎉 All ships sunk in {len(self.shot_history)} shots!")
                break
            target, active = strategy.get_hunt_candidates(self.board_size, self.agent_board.cnf, self.shots_taken)
            if not active or target is None: break
            self.shots_taken.add(target)
            r, c = target
            was_hit = is_ship_part(self.board_size, self.truth_board.cnf, r, c)
            record_shot(self.board_size, self.agent_board.cnf, r, c, was_hit)
            self.shot_history.append((r, c, was_hit))
        self.finalize_game(all_ship_cells)


class SimulateIntelligentGame(BaseSimulateGame):
    def simulate(self):
        strategy = BattleshipIntelligentRandomStrategy()
        all_ship_cells = {(r, c) for r in range(self.board_size) for c in range(self.board_size)
                          if get_var(self.board_size, 1, r, c) in self._get_unit_clause_set(self.truth_board.cnf)}
        
        for shot_num in range(1, self.shots + 1):
            if self._all_ships_sunk(all_ship_cells):
                print(f"🎉 All ships sunk in {len(self.shot_history)} shots!")
                break
            target, active = strategy.get_hunt_candidates(self.board_size, self.agent_board.cnf, self.shots_taken)
            if not active or target is None: break
            self.shots_taken.add(target)
            r, c = target
            was_hit = is_ship_part(self.board_size, self.truth_board.cnf, r, c)
            record_shot(self.board_size, self.agent_board.cnf, r, c, was_hit)
            self.shot_history.append((r, c, was_hit))
        self.finalize_game(all_ship_cells)


class SimulateCheckerboardIntelligentGame(BaseSimulateGame):
    def simulate(self):
        strategy = BattleshipCheckerboardIntelligentStrategy()
        all_ship_cells = {(r, c) for r in range(self.board_size) for c in range(self.board_size)
                          if get_var(self.board_size, 1, r, c) in self._get_unit_clause_set(self.truth_board.cnf)}
        
        for shot_num in range(1, self.shots + 1):
            if self._all_ships_sunk(all_ship_cells):
                print(f"🎉 All ships sunk in {len(self.shot_history)} shots!")
                break
            target, active = strategy.get_hunt_candidates(self.board_size, self.agent_board.cnf, self.shots_taken)
            if not active or target is None: break
            self.shots_taken.add(target)
            r, c = target
            was_hit = is_ship_part(self.board_size, self.truth_board.cnf, r, c)
            record_shot(self.board_size, self.agent_board.cnf, r, c, was_hit)
            self.shot_history.append((r, c, was_hit))
        self.finalize_game(all_ship_cells)
