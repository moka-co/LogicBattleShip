import random
from pysat.solvers import Glucose3
from src.ship_types import *
from src.ship_logic import *
from src.utils import *
from src.gui import run_gui


def _get_unprocessed_hits(board_size, cnf):
        return [(r, c) for r in range(board_size) for c in range(board_size)
                if get_var(board_size, 8, r, c) in _get_unit_clause_set(cnf) and not _is_cell_in_sunk_ship(board_size, cnf, r, c)]

def record_shot(board_size, cnf, r, c, was_hit):
    """Records a shot outcome by appending unit clauses to the CNF."""
    cnf.append([get_var(board_size, 7, r, c)])
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
    return False


def _is_cell_in_sunk_ship(board_size, cnf, r, c):
    unit_clauses = _get_unit_clause_set(cnf)
    for sunk_type in (10, 11, 12, 13):
        if sunk_type == 10:
            r_range, c_range = range(board_size), range(board_size - 1)
        elif sunk_type == 11:
            r_range, c_range = range(board_size - 1), range(board_size)
        elif sunk_type == 12:
            r_range, c_range = range(board_size), range(board_size - 2)
        else:
            r_range, c_range = range(board_size - 2), range(board_size)
        for sr in r_range:
            for sc in c_range:
                sunk_var = get_var(board_size, sunk_type, sr, sc)
                if sunk_var in unit_clauses and _sunk_covers_cell(board_size, sunk_type, sr, sc, r, c):
                    return True
    return False


def get_simple_hunt_targets(board_size, cnf, shots_taken):
    unprocessed_hits = _get_unprocessed_hits(board_size, cnf)
    if not unprocessed_hits:
        return []
    candidates = []
    seen = set()
    for (hr, hc) in unprocessed_hits:
        neighbors = [(hr - 1, hc), (hr + 1, hc), (hr, hc - 1), (hr, hc + 1)]
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
    return {'patrol_boat': patrol_boat_sunk, 'submarine': submarine_sunk}


def get_intelligent_hunt_targets(board_size, cnf, shots_taken):
    unprocessed_hits = _get_unprocessed_hits(board_size, cnf)
    if not unprocessed_hits:
        return []
    unit_clauses = _get_unit_clause_set(cnf)
    sunk_status = _get_sunk_ships_status(board_size, cnf)
    all_hits = {(r, c) for r in range(board_size) for c in range(board_size) if get_var(board_size, 8, r, c) in unit_clauses}
    all_misses = {(r, c) for r in range(board_size) for c in range(board_size) if get_var(board_size, 9, r, c) in unit_clauses}
    candidates = []
    seen = set()
    for (hr, hc) in unprocessed_hits:
        adjacent_horizontal = [(hr, hc + dc) for dc in [-1, 1] if 0 <= hc + dc < board_size and (hr, hc + dc) in all_hits]
        adjacent_vertical = [(hr + dr, hc) for dr in [-1, 1] if 0 <= hr + dr < board_size and (hr + dr, hc) in all_hits]
        possible_ship_lengths = [2, 3]
        if adjacent_horizontal and not adjacent_vertical:
            all_h = [(hr, hc)] + adjacent_horizontal
            min_c, max_c = min(c for r, c in all_h), max(c for r, c in all_h)
            current_len = max_c - min_c + 1
            for target_len in possible_ship_lengths:
                if current_len < target_len:
                    if min_c - 1 >= 0 and (hr, min_c - 1) not in shots_taken: candidates.append((hr, min_c - 1))
                    if max_c + 1 < board_size and (hr, max_c + 1) not in shots_taken: candidates.append((hr, max_c + 1))
        elif adjacent_vertical and not adjacent_horizontal:
            all_v = [(hr, hc)] + adjacent_vertical
            min_r, max_r = min(r for r, c in all_v), max(r for r, c in all_v)
            current_len = max_r - min_r + 1
            for target_len in possible_ship_lengths:
                if current_len < target_len:
                    if min_r - 1 >= 0 and (min_r - 1, hc) not in shots_taken: candidates.append((min_r - 1, hc))
                    if max_r + 1 < board_size and (max_r + 1, hc) not in shots_taken: candidates.append((max_r + 1, hc))
        else:
            for nr, nc, d in [(hr - 1, hc, 'up'), (hr + 1, hc, 'down'), (hr, hc - 1, 'left'), (hr, hc + 1, 'right')]:
                if 0 <= nr < board_size and 0 <= nc < board_size and (nr, nc) not in shots_taken:
                    candidates.append((nr, nc))
        for nr, nc in candidates:
            if (nr, nc) not in seen:
                seen.add((nr, nc))
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
        all_ship_cells = {(r, c) for r in range(self.board_size) for c in range(self.board_size)
                          if get_var(self.board_size, 1, r, c) in self._get_unit_clause_set(self.truth_board.cnf)}
        for shot_num in range(1, self.shots + 1):
            candidates = get_intelligent_hunt_targets(self.board_size, self.agent_board.cnf, self.shots_taken)
            target = random.choice(candidates) if candidates else None
            if not target:
                unshot = [(r, c) for r in range(self.board_size) for c in range(self.board_size) if (r, c) not in self.shots_taken]
                if not unshot: break
                target = random.choice(unshot)
            if target is None: break
            self.shots_taken.add(target)
            r, c = target
            was_hit = is_ship_part(self.board_size, self.truth_board.cnf, r, c)
            record_shot(self.board_size, self.agent_board.cnf, r, c, was_hit)
            self.shot_history.append((r, c, was_hit))
        self.finalize_game(all_ship_cells)
