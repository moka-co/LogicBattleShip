from utils import get_var


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
