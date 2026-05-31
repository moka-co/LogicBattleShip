import random
from pysat.solvers import Glucose3
from src.board import init_empty_board
from src.ship_types import *
from src.ship_logic import *
from src.utils import *
from src.gui import run_gui


class GameFactory:
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


def solve_game(cnf):
    """Uses Glucose3 to check if the current CNF is satisfiable."""
    with Glucose3(bootstrap_with=cnf.clauses) as solver:
        if solver.solve():
            return solver.get_model()
        else:
            return None


def simulate_game(board_size, shots, game_factory, use_gui=False):
    """Run a simulation: visualize board before and after random shots."""
    # Visualize board before shots
    visualize_board(board_size, game_factory.cnf)

    # Track shots to avoid duplicates
    shots_taken = set()
    shot_history = []
    
    # Simulate random shots
    for _ in range(shots):
        # Find a coordinate that hasn't been shot yet
        while True:
            r = random.randint(0, board_size - 1)
            c = random.randint(0, board_size - 1)
            if (r, c) not in shots_taken:
                shots_taken.add((r, c))
                break
            if len(shots_taken) == board_size * board_size:
                print("All cells have been shot.")
                break

        # Determine hit/miss based on actual ship placement
        was_hit = is_ship_part(board_size, game_factory.cnf, r, c)
        record_shot(board_size, game_factory.cnf, r, c, was_hit)
        shot_history.append((r, c, was_hit))
        print(f"Shot at ({r}, {c}) - Hit: {was_hit}")

    # Visualize board after shots
    visualize_board(board_size, game_factory.cnf)
    
    if use_gui:
        run_gui(board_size, game_factory.cnf, shot_history)
        
    return game_factory.cnf
