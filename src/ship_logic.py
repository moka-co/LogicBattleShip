from src.utils import get_var, _get_ship_cells, _get_forbidden_cells


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

    # 6. Submarine orientation inference (similar to PatrolBoat):
    # If Hit_{i,j} and both horizontal neighbors are Miss, then the ship at (i,j)
    # cannot be a horizontal submarine, and must be a vertical submarine.
    # Formula: (Hit_{i,j} ∧ Miss_{i,j-1} ∧ Miss_{i,j+1}) ->
    #          (¬SM_{h,i-2,j} ∧ ¬SM_{h,i-1,j} ∧ ¬SM_{h,i,j} ∧ (SM_{v,i-2,j} ∨ SM_{v,i-1,j} ∨ SM_{v,i,j}))
    for r in range(board_size):
        for c in range(board_size):
            # Horizontal-misses pattern requires both j-1 and j+1 to be in bounds
            if c - 1 < 0 or c + 1 >= board_size:
                continue

            hit = get_var(board_size, 8, r, c)
            miss_left = get_var(board_size, 9, r, c - 1)
            miss_right = get_var(board_size, 9, r, c + 1)

            # Conclusion: ¬SM_{h,*,j} for all possible horizontal submarines covering (r,c)
            # SM_{h,r',c'} covers cells (r', c'), (r', c'+1), (r', c'+2)
            # So (r,c) is covered by SM_{h,r,c-2}, SM_{h,r,c-1}, SM_{h,r,c}
            for c_start in [c - 2, c - 1, c]:
                if 0 <= c_start <= board_size - 3:  # SM horizontal needs c_start+2 in bounds
                    sm_h = get_var(board_size, 5, r, c_start)
                    cnf.append([-hit, -miss_left, -miss_right, -sm_h])

            # Conclusion: SM_{v,r',c} for possible vertical submarines
            # SM_{v,r',c} covers cells (r', c), (r'+1, c), (r'+2, c)
            # So (r,c) can be covered by SM_{v,r-2,c}, SM_{v,r-1,c}, SM_{v,r,c}
            disjuncts = [-hit, -miss_left, -miss_right]
            for r_start in [r - 2, r - 1, r]:
                if 0 <= r_start <= board_size - 3:  # SM vertical needs r_start+2 in bounds
                    disjuncts.append(get_var(board_size, 6, r_start, c))
            
            # Only emit if at least one vertical option is feasible
            if len(disjuncts) > 3:
                cnf.append(disjuncts)

    # 7. Vertical orientation inference for submarines:
    # If Hit_{i,j} and both vertical neighbors are Miss, then the ship at (i,j)
    # cannot be a vertical submarine, and must be a horizontal submarine.
    # Formula: (Hit_{i,j} ∧ Miss_{i-1,j} ∧ Miss_{i+1,j}) ->
    #          (¬SM_{v,i-2,j} ∧ ¬SM_{v,i-1,j} ∧ ¬SM_{v,i,j} ∧ (SM_{h,i,j-2} ∨ SM_{h,i,j-1} ∨ SM_{h,i,j}))
    for r in range(board_size):
        for c in range(board_size):
            # Vertical-misses pattern requires both r-1 and r+1 to be in bounds
            if r - 1 < 0 or r + 1 >= board_size:
                continue

            hit = get_var(board_size, 8, r, c)
            miss_up = get_var(board_size, 9, r - 1, c)
            miss_down = get_var(board_size, 9, r + 1, c)

            # Conclusion: ¬SM_{v,*,j} for all possible vertical submarines covering (r,c)
            for r_start in [r - 2, r - 1, r]:
                if 0 <= r_start <= board_size - 3:  # SM vertical needs r_start+2 in bounds
                    sm_v = get_var(board_size, 6, r_start, c)
                    cnf.append([-hit, -miss_up, -miss_down, -sm_v])

            # Conclusion: SM_{h,r,c'} for possible horizontal submarines
            disjuncts = [-hit, -miss_up, -miss_down]
            for c_start in [c - 2, c - 1, c]:
                if 0 <= c_start <= board_size - 3:  # SM horizontal needs c_start+2 in bounds
                    disjuncts.append(get_var(board_size, 5, r, c_start))
            
            # Only emit if at least one horizontal option is feasible
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

    # --- Sunk Battleship horizontal: Sunk_BS_{h,i,j} <=> (Hit_{i,j} ∧ Hit_{i,j+1} ∧ Hit_{i,j+2} ∧ Hit_{i,j+3}) ---
    for r in range(board_size):
        for c in range(board_size - 3):
            sunk = get_var(board_size, 16, r, c)
            hits = [get_var(board_size, 8, r, c + k) for k in range(4)]
            for h in hits:
                cnf.append([-sunk, h])
            cnf.append([-h for h in hits] + [sunk])

    # --- Sunk Battleship vertical: Sunk_BS_{v,i,j} <=> (Hit_{i,j} ∧ Hit_{i+1,j} ∧ Hit_{i+2,j} ∧ Hit_{i+3,j}) ---
    for r in range(board_size - 3):
        for c in range(board_size):
            sunk = get_var(board_size, 17, r, c)
            hits = [get_var(board_size, 8, r + k, c) for k in range(4)]
            for h in hits:
                cnf.append([-sunk, h])
            cnf.append([-h for h in hits] + [sunk])

    # --- Sunk Carrier: Sunk_CR_{i,j} <=> (Hit_{i,j} ∧ Hit_{i,j+1} ∧ Hit_{i+1,j} ∧ Hit_{i+1,j+1}) ---
    for r in range(board_size - 1):
        for c in range(board_size - 1):
            sunk = get_var(board_size, 19, r, c)
            hits = [get_var(board_size, 8, r + dr, c + dc) for dr in range(2) for dc in range(2)]
            for h in hits:
                cnf.append([-sunk, h])
            cnf.append([-h for h in hits] + [sunk])

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

    # --- Sunk BS horizontal: Sunk_BS_{h,i,j} -> 10 surrounding cells are not SP ---
    for r in range(board_size):
        for c in range(board_size - 3):
            sunk = get_var(board_size, 16, r, c)
            cells = _get_ship_cells('h', r, c, 4)
            neighbors = [n for n in _get_forbidden_cells(board_size, cells) if n not in cells]
            _add_neg_sp(sunk, neighbors)

    # --- Sunk BS vertical: Sunk_BS_{v,i,j} -> 10 surrounding cells are not SP ---
    for r in range(board_size - 3):
        for c in range(board_size):
            sunk = get_var(board_size, 17, r, c)
            cells = _get_ship_cells('v', r, c, 4)
            neighbors = [n for n in _get_forbidden_cells(board_size, cells) if n not in cells]
            _add_neg_sp(sunk, neighbors)

    # --- Sunk Carrier: Sunk_CR_{i,j} -> 8 surrounding cells are not SP ---
    for r in range(board_size - 1):
        for c in range(board_size - 1):
            sunk = get_var(board_size, 19, r, c)
            cells = [(r, c), (r, c + 1), (r + 1, c), (r + 1, c + 1)]
            neighbors = [n for n in _get_forbidden_cells(board_size, cells) if n not in cells]
            _add_neg_sp(sunk, neighbors)

    return cnf
