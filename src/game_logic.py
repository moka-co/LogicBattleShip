"""Game logic, strategies, and simulation classes for the Battleship SAT solver.

Provides:
  - Shot recording and board visualization helpers.
  - Sunk-ship detection and coverage computation.
  - Hunt-target generation (simple, intelligent/SAT-guided, checkerboard).
  - Strategy classes that wrap target generation with random selection.
  - Simulation classes that run a full game loop for each strategy.
"""

import random
from pysat.solvers import Glucose3
from src.ship_types import *
from src.ship_logic import *
from src.utils import *
from src.gui import run_gui


def _get_unprocessed_hits(board_size, cnf):
    """Returns a list of hit cells whose ship has not yet been fully sunk.

    Scans the CNF for asserted ``Hit_{r,c}`` unit clauses and filters out any
    cell that is covered by an asserted Sunk variable.

    Args:
        board_size: The side length of the square board.
        cnf: The agent's CNF knowledge base.

    Returns:
        A list of (row, col) tuples representing open (unsunk) hits.
    """
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
    """Prints a text representation of the board to stdout.

    Legend:
      - ``[H]`` — Hit (the cell was shot and contained a ship part).
      - ``[S]`` — Ship part (not yet shot; only visible on the truth board).
      - ``[0]`` — Miss (the cell was shot and was empty).
      - ``[ ]`` — Unknown / empty.

    Args:
        board_size: The side length of the square board.
        cnf: The CNF whose unit clauses determine cell states.
    """
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
    """Checks whether cell (r, c) contains a ship part on the truth board.

    Looks for the ``SP_{r,c}`` variable as a unit clause in the CNF.

    Args:
        board_size: The side length of the square board.
        cnf: The truth board's CNF (must have ship placements asserted).
        r: Row index.
        c: Column index.

    Returns:
        True if ``SP_{r,c}`` is asserted as a unit clause, False otherwise.
    """
    unit_clauses = {clause[0] for clause in cnf.clauses if len(clause) == 1}
    return get_var(board_size, 1, r, c) in unit_clauses


def _get_unit_clause_set(cnf):
    """Extracts all unit-clause literals from a CNF as a set.

    A unit clause is a clause with exactly one literal. These represent facts
    that are unconditionally asserted in the knowledge base (e.g. shot outcomes,
    ship placements on the truth board, propagated sunk variables).

    Args:
        cnf: A ``pysat.formula.CNF`` object.

    Returns:
        A set of integers, each being the single literal of a unit clause.
    """
    return {clause[0] for clause in cnf.clauses if len(clause) == 1}


def _sunk_covers_cell(board_size, sunk_type, sr, sc, r, c):
    """Checks whether a sunk ship at (sr, sc) of the given type covers cell (r, c).

    Args:
        board_size: The side length of the square board (unused but kept for API consistency).
        sunk_type: The variable type of the Sunk predicate (10–13, 16–17, 19).
        sr: Starting row of the sunk ship.
        sc: Starting column of the sunk ship.
        r: Row of the cell to check.
        c: Column of the cell to check.

    Returns:
        True if the ship at (sr, sc) of the given sunk_type occupies cell (r, c).
    """
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
    """Returns candidate cells adjacent to open hits using simple neighbor enumeration.

    Checks all 8 neighbors (orthogonal + diagonal) of each unprocessed hit.
    Diagonal neighbors are included because the Carrier is 2×2, so a diagonal
    cell can be part of the same ship.

    No SAT reasoning is performed — every unshot, in-bounds neighbor is returned.

    Args:
        board_size: The side length of the square board.
        cnf: The agent's CNF knowledge base.
        shots_taken: Set of (row, col) tuples already shot.

    Returns:
        A list of (row, col) candidate cells to shoot next. Empty if no open hits.
    """
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
    """Returns a dict indicating which ship types have been sunk.

    Scans the CNF unit clauses for any asserted Sunk variable of each ship type.

    Args:
        board_size: The side length of the square board.
        cnf: The agent's CNF knowledge base.

    Returns:
        A dict with keys ``'patrol_boat'``, ``'submarine'``, ``'battleship'``,
        ``'carrier'``, each mapping to a bool indicating whether that ship type
        has at least one asserted Sunk variable.
    """
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
            # Check all 8 neighbors (orthogonal + diagonal) because the Carrier
            # is 2x2, so diagonal cells can be part of the same ship.
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
    """Returns unshot cells in a checkerboard pattern for efficient board coverage.

    Targets cells where ``(r + c) % 2 == 0``, which guarantees that any ship
    occupying 2 or more cells must overlap at least one checkerboard cell.

    Args:
        board_size: The side length of the square board.
        shots_taken: Set of (row, col) tuples already shot.

    Returns:
        A list of (row, col) tuples on the checkerboard that have not been shot.
    """
    candidates = []
    for r in range(board_size):
        for c in range(board_size):
            if (r + c) % 2 == 0 and (r, c) not in shots_taken:
                candidates.append((r, c))
    return candidates


class BattleshipStrategy:
    """Abstract base class for Battleship shooting strategies.

    Subclasses must implement ``get_hunt_candidates`` to return a target cell
    and a boolean indicating whether the game should continue.
    """

    def get_hunt_candidates(self, board_size, cnf, shots_taken):
        """Selects the next cell to shoot.

        Args:
            board_size: The side length of the square board.
            cnf: The agent's CNF knowledge base.
            shots_taken: Set of (row, col) tuples already shot.

        Returns:
            A tuple ``(target, active)`` where ``target`` is a (row, col) tuple
            or None, and ``active`` is False if no moves remain.

        Raises:
            NotImplementedError: Always, unless overridden by a subclass.
        """
        raise NotImplementedError


class BattleshipSimpleRandomStrategy(BattleshipStrategy):
    """Strategy that shoots neighbors of open hits randomly, without SAT reasoning.

    When open hits exist, picks a random neighbor from ``get_simple_hunt_targets``.
    Otherwise falls back to a uniformly random unshot cell.
    """

    def get_hunt_candidates(self, board_size, cnf, shots_taken):
        """Selects a random neighbor of an open hit, or a random unshot cell.

        Args:
            board_size: The side length of the square board.
            cnf: The agent's CNF knowledge base.
            shots_taken: Set of (row, col) tuples already shot.

        Returns:
            A tuple ``(target, active)`` — see ``BattleshipStrategy``.
        """
        hunt_candidates = get_simple_hunt_targets(board_size, cnf, shots_taken)
        target = random.choice(hunt_candidates) if hunt_candidates else None
        
        if not target:
            unshot = [(r, c) for r in range(board_size) for c in range(board_size) if (r, c) not in shots_taken]
            if not unshot: return None, False
            target = random.choice(unshot)
            
        return target, True


class BattleshipIntelligentRandomStrategy(BattleshipStrategy):
    """Strategy that uses SAT reasoning to pick forced or consistent neighbors.

    Calls ``get_intelligent_hunt_targets`` to obtain cells that are logically
    forced or consistent with containing a ship part. Picks randomly among them.
    Falls back to a uniformly random unshot cell when no open hits exist.
    """

    def get_hunt_candidates(self, board_size, cnf, shots_taken):
        """Selects a SAT-guided target near open hits, or a random unshot cell.

        Args:
            board_size: The side length of the square board.
            cnf: The agent's CNF knowledge base.
            shots_taken: Set of (row, col) tuples already shot.

        Returns:
            A tuple ``(target, active)`` — see ``BattleshipStrategy``.
        """
        hunt_candidates = get_intelligent_hunt_targets(board_size, cnf, shots_taken)
        target = random.choice(hunt_candidates) if hunt_candidates else None
        
        if not target:
            unshot = [(r, c) for r in range(board_size) for c in range(board_size) if (r, c) not in shots_taken]
            if not unshot: return None, False
            target = random.choice(unshot)
            
        return target, True


class BattleshipCheckerboardIntelligentStrategy(BattleshipStrategy):
    """Hybrid strategy: checkerboard search for discovery, SAT hunting for kills.

    When there are open (unsunk) hits, delegates to ``get_intelligent_hunt_targets``
    to finish off the damaged ship. Otherwise, picks from a checkerboard pattern
    to efficiently discover new ships. Falls back to any unshot cell if both
    sources are exhausted.
    """

    def get_hunt_candidates(self, board_size, cnf, shots_taken):
        """Selects a SAT-guided target if hunting, else a checkerboard cell.

        Args:
            board_size: The side length of the square board.
            cnf: The agent's CNF knowledge base.
            shots_taken: Set of (row, col) tuples already shot.

        Returns:
            A tuple ``(target, active)`` — see ``BattleshipStrategy``.
        """
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
    """Abstract base class for running a Battleship simulation.

    Manages the game loop scaffolding: shot tracking, hit history, early
    termination detection, and final reporting. Subclasses implement
    ``simulate()`` to wire in a specific ``BattleshipStrategy``.

    Attributes:
        board_size: Side length of the square board.
        truth_board: The ``TruthBoardFactory`` instance (answers hit/miss queries).
        agent_board: The ``AgentBoardFactory`` instance (agent's KB).
        shots: Maximum number of shots allowed.
        use_gui: Whether to launch the Pygame GUI after the game.
        shots_taken: Set of (row, col) cells that have been shot.
        shot_history: Ordered list of ``(row, col, was_hit)`` tuples.
    """

    def __init__(self, board_size, shots, truth_board, agent_board, use_gui=False):
        """Initializes the simulation and immediately runs it.

        Args:
            board_size: The side length of the square board.
            shots: Maximum number of shots to fire.
            truth_board: A ``TruthBoardFactory`` with ships placed.
            agent_board: An ``AgentBoardFactory`` (no ships placed).
            use_gui: If True, launch Pygame visualization after the game.
        """
        self.board_size = board_size
        self.truth_board = truth_board
        self.agent_board = agent_board
        self.shots = shots
        self.use_gui = use_gui
        self.shots_taken = set()
        self.shot_history = []
        self.simulate()

    def _get_unit_clause_set(self, cnf):
        """Extracts all unit-clause literals from a CNF.

        Args:
            cnf: A ``pysat.formula.CNF`` object.

        Returns:
            A set of integers representing asserted unit-clause literals.
        """
        return {clause[0] for clause in cnf.clauses if len(clause) == 1}

    def _get_unprocessed_hits(self, cnf):
        """Returns open hits (hit cells not yet covered by a Sunk variable).

        Args:
            cnf: The agent's CNF knowledge base.

        Returns:
            A list of (row, col) tuples.
        """
        return [(r, c) for r in range(self.board_size) for c in range(self.board_size)
                if get_var(self.board_size, 8, r, c) in self._get_unit_clause_set(cnf) and not _is_cell_in_sunk_ship(self.board_size, cnf, r, c)]

    def simulate(self):
        """Runs the game loop. Must be implemented by subclasses.

        Raises:
            NotImplementedError: Always, unless overridden.
        """
        raise NotImplementedError("Subclasses must implement simulate()")

    def _all_ships_sunk(self, all_ship_cells):
        """Checks whether every ship cell has been hit.

        Args:
            all_ship_cells: Set of (row, col) tuples representing all ship cells.

        Returns:
            True if every cell in ``all_ship_cells`` has been hit.
        """
        hit_cells = {(r, c) for r, c, was_hit in self.shot_history if was_hit}
        return all_ship_cells.issubset(hit_cells)

    def finalize_game(self, all_ship_cells):
        """Prints final game statistics, visualizes the board, and optionally launches the GUI.

        Args:
            all_ship_cells: Set of (row, col) tuples representing all ship cells.
        """
        final_hits = len([h for h in self.shot_history if h[2]])
        print(f"\nGame ended: {final_hits}/{len(all_ship_cells)} ship cells found in {len(self.shot_history)} shots")
        visualize_board(self.board_size, self.truth_board.cnf)
        if self.use_gui:
            run_gui(self.board_size, self.truth_board.cnf, self.shot_history)


class SimulateSimpleGame(BaseSimulateGame):
    """Simulation using the simple random neighbor strategy.

    Shoots random neighbors of open hits; falls back to uniformly random shots.
    """

    def simulate(self):
        """Runs the game loop with ``BattleshipSimpleRandomStrategy``."""
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
    """Simulation using the SAT-guided intelligent strategy.

    Uses the SAT solver to identify forced or consistent ship-part cells near
    open hits; falls back to uniformly random shots.
    """

    def simulate(self):
        """Runs the game loop with ``BattleshipIntelligentRandomStrategy``."""
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
    """Simulation using the checkerboard + SAT-guided hybrid strategy.

    Uses a checkerboard pattern for discovery and SAT reasoning for hunting
    damaged ships.
    """

    def simulate(self):
        """Runs the game loop with ``BattleshipCheckerboardIntelligentStrategy``."""
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
