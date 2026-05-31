from src.utils import get_var


def add_shot_hit_miss_constraints(board_size, cnf):
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

    for r in range(board_size):
        for c in range(board_size):
            shot = get_var(board_size, 7, r, c)
            hit = get_var(board_size, 8, r, c)
            miss = get_var(board_size, 9, r, c)
            sp = get_var(board_size, 1, r, c)

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
    for r in range(board_size):
        for c in range(board_size):
            # Horizontal-misses pattern requires both j-1 and j+1 to be in bounds
            if c - 1 < 0 or c + 1 >= board_size:
                continue

            hit = get_var(board_size, 8, r, c)
            miss_left = get_var(board_size, 9, r, c - 1)
            miss_right = get_var(board_size, 9, r, c + 1)

            # Conclusion clause 1: ¬PB_{h,i,j}
            # PB_{h,i,j} is only defined for c <= board_size - 2 (i.e. fits horizontally).
            # If c == board_size - 1, the horizontal PB at (i,c) doesn't exist anyway,
            # but emitting the clause is still harmless if the var is unused.
            if c + 1 < board_size:
                pb_h = get_var(board_size, 3, r, c)
                cnf.append([-hit, -miss_left, -miss_right, -pb_h])

            # Conclusion clause 2: PB_{v,i-1,j} OR PB_{v,i+1,j}
            # PB_{v,r',c} is defined only for r' <= board_size - 2.
            disjuncts = [-hit, -miss_left, -miss_right]
            if r - 1 >= 0:
                # PB_{v,i-1,j}: places ship at (r-1, c)-(r, c). Valid since r-1 in [0, board_size-2].
                disjuncts.append(get_var(board_size, 4, r - 1, c))
            if r + 1 < board_size and r <= board_size - 2:
                # PB_{v,i+1,j}: places ship at (r+1, c)-(r+2, c). Need r+1 <= board_size-2.
                if r + 1 <= board_size - 2:
                    disjuncts.append(get_var(board_size, 4, r + 1, c))
            # Only emit the clause if at least one vertical option is feasible;
            # otherwise the implication would be contradictory and we'd encode unsat
            # for an impossible hit pattern (which is fine but we skip for clarity).
            if len(disjuncts) > 3:
                cnf.append(disjuncts)

    return cnf


def add_sinking_constraints(board_size, cnf):
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
    for r in range(board_size):
        for c in range(board_size - 1):  # needs c+1 in bounds
            sunk = get_var(board_size, 10, r, c)
            h1 = get_var(board_size, 8, r, c)
            h2 = get_var(board_size, 8, r, c + 1)
            # Sunk -> Hit_k
            cnf.append([-sunk, h1])
            cnf.append([-sunk, h2])
            # (Hit_1 ∧ Hit_2) -> Sunk
            cnf.append([-h1, -h2, sunk])

    # --- Sunk PatrolBoat vertical: Sunk_PB_{v,i,j} <=> (Hit_{i,j} ∧ Hit_{i+1,j}) ---
    for r in range(board_size - 1):  # needs r+1 in bounds
        for c in range(board_size):
            sunk = get_var(board_size, 11, r, c)
            h1 = get_var(board_size, 8, r, c)
            h2 = get_var(board_size, 8, r + 1, c)
            cnf.append([-sunk, h1])
            cnf.append([-sunk, h2])
            cnf.append([-h1, -h2, sunk])

    # --- Sunk Submarine horizontal: Sunk_SM_{h,i,j} <=> (Hit_{i,j} ∧ Hit_{i,j+1} ∧ Hit_{i,j+2}) ---
    for r in range(board_size):
        for c in range(board_size - 2):  # needs c+2 in bounds
            sunk = get_var(board_size, 12, r, c)
            h1 = get_var(board_size, 8, r, c)
            h2 = get_var(board_size, 8, r, c + 1)
            h3 = get_var(board_size, 8, r, c + 2)
            cnf.append([-sunk, h1])
            cnf.append([-sunk, h2])
            cnf.append([-sunk, h3])
            cnf.append([-h1, -h2, -h3, sunk])

    # --- Sunk Submarine vertical: Sunk_SM_{v,i,j} <=> (Hit_{i,j} ∧ Hit_{i+1,j} ∧ Hit_{i+2,j}) ---
    for r in range(board_size - 2):  # needs r+2 in bounds
        for c in range(board_size):
            sunk = get_var(board_size, 13, r, c)
            h1 = get_var(board_size, 8, r, c)
            h2 = get_var(board_size, 8, r + 1, c)
            h3 = get_var(board_size, 8, r + 2, c)
            cnf.append([-sunk, h1])
            cnf.append([-sunk, h2])
            cnf.append([-sunk, h3])
            cnf.append([-h1, -h2, -h3, sunk])

    return cnf


def add_all_parts_sunk_consequences(board_size, cnf):
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
            if 0 <= nr < board_size and 0 <= nc < board_size:
                cnf.append([-sunk_var, -get_var(board_size, 1, nr, nc)])

    # --- Sunk PB horizontal: Sunk_PB_{h,i,j} -> 6 surrounding cells are not SP ---
    for r in range(board_size):
        for c in range(board_size - 1):
            sunk = get_var(board_size, 10, r, c)
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
    for r in range(board_size - 1):
        for c in range(board_size):
            sunk = get_var(board_size, 11, r, c)
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
    for r in range(board_size):
        for c in range(board_size - 2):
            sunk = get_var(board_size, 12, r, c)
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
    for r in range(board_size - 2):
        for c in range(board_size):
            sunk = get_var(board_size, 13, r, c)
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
