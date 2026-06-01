# Logic Battle Ship

This project aims to create a logic agent (propositional logic) for solving the battleship game.

We refer to both the agent and the human that plays against the agent as player(s).

## Battleship Game - Knowledge Engineering
Battleship game is a 1v1 game where each player has a board composed of $N \times N$ tiles. Before the start of the game, the players can position a number $m$ of ships. (In this case we consider $2 \le m \le 4$ ships).
Ships are of different kinds and sizes. We distinguish an easier version of the game with a 5x5 board and two kinds of ships: $1\times 2$ and $1\times 4$. Ships must be placed inside the grid. Two ships cannot be placed adjacently and must be separated by a one‑tile distance.

In the 10x10 board we have the following kind of ships: $1\times 2, 1\times 3, 1\times 4, 2\times 2$. 

The opponent's board is hidden. Each turn a player can shoot one of the hidden opponent's tiles, hoping to hit a part of a ship. A player cannot shoot an already shot tile (it would be illogical).

The first player who destroys the entire opponent's fleet wins. 

---

**PEAS**
- **Performance Measure**: +1 point for each part of a ship hit, wins the first player who reaches the maximum.
- **Environment**: $10 \times 10$ hidden grid to the opponent. The location of the ships is chosen randomly respecting the 1‑tile distance constraint. 
- **Actuators**: Each turn, a player can shoot a tile (chosen randomly or with a heuristic). Upon shooting, the tile is shown; it may be empty if there is no opponent's ship or it may contain a destroyed part of a ship. 
- **Sensors**: The agent can see its grid (all shown tiles) and the opponent's grid. The opponent's grid shows either hidden tiles or non‑hidden tiles. Non‑hidden tiles contain a shot piece of an enemy ship or empty sea.

---

**Task Environment** - the environment is:
- **Partially observable**: you can observe only what you already "explored" i.e. shoot.
- **Deterministic**: since rewards come only after a board is shot.
- **Multiagent**: in particular bi-agent because it's a 1v1 game
- **Nondeterministic**: the next state could be either random or a strategy could be applied if a tile is shown (i.e. once an opponent part of ship is shown, shooting the nearby tiles)
- **Sequential**
- **Discrete**: everything is discrete
- **Dynamic**: because while it's the opponent's turn, the player's ship may be destroyed or shot.
- **Known**: the agent knows exactly what to do and what happens.

---

The main challenges for an agent are:
- initial ignorance
- opponent

Sinking an opponent ship may be advantageous because sinking it not only advances towards the conditional victory, but also shows the tiles around the ship that logically cannot contain a ship.

---

**Multiplayer**

The agent maintains two separate boards:
- Their own board, fully observable that contains the ship placements and which tiles the opponent has shot
- The opponent's board: partially observable, contains only the tiles the agent has shot, labeled as $Hit$ or $Miss$; all other tiles remain hidden ($H_{i,j}$ is true)

The KB reasoning and SAT queries operate exclusively on the opponent's board.

## Propositional Vocabulary

### Ships and Environment

**Ships**:
- PatrolBoat is the $1 \times 2$ boat
- Submarine is the $1 \times 3$ boat
- Battleship is the $1 \times 4$ boat
- Carrier is the $2 \times 2$ boat

Each part i.e. 1 tile of a boat is a ShipPart.

**Environment**:
- $H_{i,j}$ is true if tile (i,j) is hidden to the opponent (not explored yet)
- $SP_{i,j}$ SP=ShipPart, is true if tile (i,j) contains a ship piece
- $E_{i,j}$ is true if the tile (i,j) is empty

From the rule of the game we know that:
- $(SP_{i,j} \land \neg E_{i,j}) \lor (\neg SP_{i,j} \land E_{i,j})$ : a tile either contains a ShipPart or is empty

### Ship definitions and constraints

**PatrolBoat**: patrol boat at position (i,j) horizontal:
- $PatrolBoat_{h,i,j} \implies (SP_{i,j} \land SP_{i,j+1})$

**PatrolBoat**: patrol boat at position (i,j) vertical:
- $PatrolBoat_{v,i,j} \implies (SP_{i,j} \land SP_{i+1,j})$

**There can be only one horizontal or vertical PatrolBoat ship**:
- $(\neg PatrolBoat_{v,i,j} \land PatrolBoat_{h,i,j}) \lor (PatrolBoat_{v,i,j} \land \neg PatrolBoat_{h,i,j})$

**Exactly one PatrolBoat placement**:
- $(PatrolBoat_{h,0,0} \lor PatrolBoat_{h,0,1} \lor \ldots \lor PatrolBoat_{v,9,8}) \land \neg(PatrolBoat_{h,i,j} \land PatrolBoat_{h,i',j'})$ for all $(i,j) \neq (i',j')$

**Horizontal Submarine**: at position (i,j) horizontal:
- $Submarine_{h,i,j} \implies (SP_{i,j} \land SP_{i,j+1} \land SP_{i,j+2})$

**Vertical Submarine** at position (i,j) vertical:
- $Submarine_{v,i,j} \implies (SP_{i,j} \land SP_{i,+1,j} \land SP_{i+2,j})$

**There can be only one horizontal or vertical Submarine**:
- $(\neg Submarine_{v,i,j} \land Submarine_{h,i,j}) \lor (Submarine_{v,i,j} \land \neg Submarine_{h,i,j})$

**Exactly one Submarine placement**:
- $(Submarine_{h,0,0} \lor Submarine_{h,0,1} \lor \ldots \lor Submarine_{v,9,7}) \land \neg (Submarine_{h,i,j} \land Submarine_{h,i',j'})$ for all $(i,j) \neq (i',j')$

**Horizontal Battleship**: at position (i,j) horizontal:
- $Battleship_{h,i,j} \implies (SP_{i,j} \land SP_{i,j+1} \land SP_{i,j+2} \land SP_{i,j+3})$

**Vertical Battleship** at position (i,j) vertical:
- $Battleship_{v,i,j} \implies (SP_{i,j} \land SP_{i+1,j} \land SP_{i+2,j} \land SP_{i+3,j})$

**There can be only one horizontal or vertical Battleship**:
- $(\neg Battleship_{v,i,j} \land Battleship_{h,i,j}) \lor (Battleship_{v,i,j} \land \neg Battleship_{h,i,j})$

**Exactly one Battleship placement**:
- $(Battleship_{h,0,0} \lor Battleship_{h,0,1} \lor \ldots \lor Battleship_{v,9,6}) \land \neg (Battleship_{h,i,j} \land Battleship_{h,i',j'})$ for all $(i,j) \neq (i',j')$

**Carrier**: carrier at position (i,j):
- $Carrier_{i,j} \implies (SP_{i,j} \land SP_{i,j+1} \land SP_{i+1,j} \land SP_{i+1,j+1})$

**Exactly one Carrier placement**:
- $(Carrier_{0,0} \lor Carrier_{0,1} \lor \ldots \lor Carrier_{8,8}) \land \neg (Carrier_{i,j} \land Carrier_{i',j'})$ for all $(i,j) \neq (i',j')$

**Cannot place any ships e.g. Submarine and PatrolBoat adjacently**
- **PatrolBoat horizontal**: $PB_{h,i,j} \implies (\neg SP_{i,j-1} \land \neg SP_{i,j+2} \land \neg SP_{i+1,j} \land \neg SP_{i-1,j} \land \neg SP_{i+1,j+1} \land \neg SP_{i-1,j+1})$
- **PatrolBoat vertical**: $PB_{v,i,j} \implies (\neg SP_{i-1,j} \land \neg SP_{i+2,j} \land \neg SP_{i,j+1} \land \neg SP_{i,j-1} \land \neg SP_{i+1,j+1} \land \neg SP_{i+1,j-1})$
- **Submarine horizontal**: $SM_{h,i,j} \implies (\neg SP_{i,j-1} \land \neg SP_{i,j+3} \land \neg SP_{i+1,j} \land \neg SP_{i-1,j} \land \neg SP_{i+1,j-1} \land \neg SP_{i-1,j-1} \land \neg SP_{i+1,j+1} \land \neg SP_{i-1,j+1} \land \neg SP_{i+1,j+2} \land \neg SP_{i-1,j+2})$
- **Submarine vertical**: $SM_{v,i,j} \implies (\neg SP_{i-1,j} \land \neg SP_{i+3,j} \land \neg SP_{i,j+1} \land \neg SP_{i,j-1} \land \neg SP_{i-1,j+1} \land \neg SP_{i-1,j-1} \land \neg SP_{i+1,j+1} \land \neg SP_{i+1,j-1} \land \neg SP_{i+2,j+1} \land \neg SP_{i+2,j-1})$
- **Battleship horizontal**: $BS_{h,i,j} \implies (\neg SP_{i,j-1} \land \neg SP_{i,j+4} \land \neg SP_{i+1,j} \land \neg SP_{i-1,j} \land \neg SP_{i+1,j-1} \land \neg SP_{i-1,j-1} \land \neg SP_{i+1,j+1} \land \neg SP_{i-1,j+1} \land \neg SP_{i+1,j+2} \land \neg SP_{i-1,j+2} \land \neg SP_{i+1,j+3} \land \neg SP_{i-1,j+3})$
- **Battleship vertical**: $BS_{v,i,j} \implies (\neg SP_{i-1,j} \land \neg SP_{i+4,j} \land \neg SP_{i,j+1} \land \neg SP_{i,j-1} \land \neg SP_{i-1,j+1} \land \neg SP_{i-1,j-1} \land \neg SP_{i+1,j+1} \land \neg SP_{i+1,j-1} \land \neg SP_{i+2,j+1} \land \neg SP_{i+2,j-1} \land \neg SP_{i+3,j+1} \land \neg SP_{i+3,j-1})$
- **Carrier**: $CR_{i,j} \implies (\neg SP_{i-1,j} \land \neg SP_{i-1,j+1} \land \neg SP_{i,j-1} \land \neg SP_{i,j+2} \land \neg SP_{i+1,j-1} \land \neg SP_{i+1,j+2} \land \neg SP_{i+2,j} \land \neg SP_{i+2,j+1} \land \neg SP_{i-1,j-1} \land \neg SP_{i-1,j+2} \land \neg SP_{i+2,j-1} \land \neg SP_{i+2,j+2})$

### Shot, Hit and Miss tiles
- $Shot_{i,j}$ true if a tile has been shoot
- $Hit_{i,j}$ true if a tile that has been shoot contains ShipPart
- $Miss_{i,j}$ true if a tile that has been shoot doesn't contains any ShipParts 
- $Shot_{i,j} \iff (Hit_{i,j} \lor Miss_{i,j})$

From these:
- $Miss_{i,j} \implies \neg SP_{i,j}$ so that tile must be empty
- $Hit_{i,j} \implies SP_{i,j}$ so that tile must contains a ship

If the agent shot and horizontal neighbours are misses, then the ship must be vertical, not horizontal:
- **PatrolBoat**: $(Hit_{i,j} \land Miss_{i,j-1} \land Miss_{i,j+1}) \implies \neg PatrolBoat_{h,i,j} \land (PB_{v,i+1,j} \lor PB_{v,i-1,j})$


### Sinking Ships

Sinking biconditionals are **conditioned on the placement variable** to prevent false sinking triggers. Without this, hitting 2 adjacent cells of a Submarine would falsely trigger a PatrolBoat sunk, causing the agent to stop hunting near those cells.

**Sunk Patrol Boat (both directions)**:
- $Sunk_{PatrolBoat_{h,i,j}} \iff (PB_{h,i,j} \land Hit_{i,j} \land Hit_{i,j+1})$
- $Sunk_{PatrolBoat_{v,i,j}} \iff (PB_{v,i,j} \land Hit_{i,j} \land Hit_{i+1,j})$

**Sunk Submarine (both directions)**
- $Sunk_{Submarine_{h,i,j}} \iff (SM_{h,i,j} \land Hit_{i,j} \land Hit_{i,j+1} \land Hit_{i,j+2})$ 
- $Sunk_{Submarine_{v,i,j}} \iff (SM_{v,i,j} \land Hit_{i,j} \land Hit_{i+1,j} \land Hit_{i+2,j})$

**Sunk Battleship (both directions)**
- $Sunk_{Battleship_{h,i,j}} \iff (BS_{h,i,j} \land Hit_{i,j} \land Hit_{i,j+1} \land Hit_{i,j+2} \land Hit_{i,j+3})$ 
- $Sunk_{Battleship_{v,i,j}} \iff (BS_{v,i,j} \land Hit_{i,j} \land Hit_{i+1,j} \land Hit_{i+2,j} \land Hit_{i+3,j})$

**Sunk Carrier**
- $Sunk_{Carrier_{i,j}} \iff (CR_{i,j} \land Hit_{i,j} \land Hit_{i,j+1} \land Hit_{i+1,j} \land Hit_{i+1,j+1})$


**AllPartsSunk Consequences**
Once you've hit all parts of a ship, you know the surrounding area is empty:
- PatrolBoat horizontal at (i,j):
$SunkPB_{h,i,j}  ⟹  ¬SP_{i,j−1}∧¬SP_{i,j+2}∧¬SP_{i−1,j}∧¬SP_{i−1,j+1}∧¬SP_{i+1,j}∧¬SP_{i+1,j+1}$
- PatrolBoat vertical at (i,j):
$Sunk_{PB_{v,i,j}} \implies \neg SP_{i-1,j} \land \neg SP_{i+2,j} \land \neg SP_{i,j-1} \land \neg SP_{i+1,j-1} \land \neg SP_{i,j+1} \land \neg SP_{i+1,j+1}$
- Submarine horizontal at (i,j): $Sunk_{SM_{h,i,j}} \implies \neg SP_{i,j-1} \land \neg SP_{i,j+3} \land \neg SP_{i-1,j} \land \neg SP_{i-1,j+1} \land \neg SP_{i-1,j+2} \land \neg SP_{i+1,j} \land \neg SP_{i+1,j+1} \land \neg SP_{i+1,j+2}$
- Submarine vertical at (i,j):
$Sunk_{SM_{v,i,j}} \implies \neg SP_{i-1,j} \land \neg SP_{i+3,j} \land \neg SP_{i,j-1} \land \neg SP_{i+1,j-1} \land \neg SP_{i+2,j-1} \land \neg SP_{i,j+1} \land \neg SP_{i+1,j+1} \land \neg SP_{i+2,j+1}$
- Battleship horizontal at (i,j):
$Sunk_{BS_{h,i,j}} \implies \neg SP_{i,j-1} \land \neg SP_{i,j+4} \land \neg SP_{i-1,j} \land \neg SP_{i-1,j+1} \land \neg SP_{i-1,j+2} \land \neg SP_{i-1,j+3} \land \neg SP_{i+1,j} \land \neg SP_{i+1,j+1} \land \neg SP_{i+1,j+2} \land \neg SP_{i+1,j+3}$
- Battleship vertical at (i,j):
$Sunk_{BS_{v,i,j}} \implies \neg SP_{i-1,j} \land \neg SP_{i+4,j} \land \neg SP_{i,j-1} \land \neg SP_{i+1,j-1} \land \neg SP_{i+2,j-1} \land \neg SP_{i+3,j-1} \land \neg SP_{i,j+1} \land \neg SP_{i+1,j+1} \land \neg SP_{i+2,j+1} \land \neg SP_{i+3,j+1}$
- Carrier at (i,j):
$Sunk_{CR_{i,j}} \implies \neg SP_{i-1,j} \land \neg SP_{i-1,j+1} \land \neg SP_{i,j-1} \land \neg SP_{i,j+2} \land \neg SP_{i+1,j-1} \land \neg SP_{i+1,j+2} \land \neg SP_{i+2,j} \land \neg SP_{i+2,j+1} \land \neg SP_{i-1,j-1} \land \neg SP_{i-1,j+2} \land \neg SP_{i+2,j-1} \land \neg SP_{i+2,j+2}$


---

## Knowledge Base
- Constraint: propositional logic with PySAT as logic 
- The agent uses a SAT solver to look for tiles that are shot, if that it tries to shoot adjacent tiles using logic. Otherwise it shot at random.
- At each turn the KB is updated and the new information is added to the Knowledge Base

**KB update after each shot**:
- On a miss: $\text{Assert: } Miss_{i,j}$ which immediately entails: $¬SP_{i,j}$
- On a hit: $\text{Assert: } Hit_{i,j}$ which immediately entails: $SP_{i,j}$
- Additionally, after every shot: $\text{Assert: } Shot_{i,j}$

**Input validation**: `record_shot` validates that the cell is within bounds and has not already been shot, raising `ValueError` otherwise.

**Sunk variable propagation**: After each hit, the agent explicitly checks whether any Sunk variables covering the hit cell are now entailed by the KB (via `_propagate_sunk_variables`). This is necessary because sunk variables are defined via biconditionals — the SAT solver can derive their truth internally, but does not add unit clauses to the CNF. The propagation function uses the solver to check $KB \land \neg Sunk_{X}$ for each candidate sunk variable; if UNSAT, the sunk variable is asserted as a unit clause. Only sunk variables whose ship footprint includes the just-hit cell are checked, for efficiency.

The KB grows monotonically, facts are only added never retracted since observations in Battleship are permanent.

**Early termination**: The simulation loop checks after each shot whether all ship cells have been hit. If so, the game ends immediately rather than continuing to fire shots.

## Agent Strategy
Formally, at each turn the agent must select a tile $(i,j)$ such that $\neg Shot_{i,j}$ (not yet shot).
- If exists at least one $Hit_{i,j}$ whose ship is not sunk yet, the agent queries the SAT solver to find tiles that could contain a ship given the current KB: $KB \models SP_{i,j}$ 
    - This is check via entailment: a tile is entailed to contain a ship if and only if $KB \land \neg SP_{i,j}$ is UNSATISFIABLE. If the solver returns UNSAT (e.g. () ), then $(i,j)$ must be a ship part and is the next shot
    - Note: technically you can't really know until you hit, for instance the solver could still choose an empty tile, however that is still a good candidate so we can assume that this entailment logically find a tile that must contain a ship part.
- If no such tile exists, use an heuristic to shot the next tile. The baseline is randomly uniform, see Heuristics section.

### Strategy 1: Simple Random (`--strategy simple`)

The simplest baseline strategy. When open hits exist, the agent enumerates all 8 neighbors (orthogonal + diagonal) of each open hit and picks one uniformly at random. No SAT reasoning is performed — every unshot, in-bounds neighbor is a candidate.

When no open hits exist, the agent falls back to a uniformly random unshot cell:

$$Choose(i,j) \text{ uniformly from } \{(i,j) \mid \neg Shot_{i,j}\}$$

### Strategy 2: Intelligent (`--strategy intelligent`)

When open hits exist, the agent uses the SAT solver to classify each neighbor of an open hit into one of three categories:

1. **Forced** ($KB \land \neg SP_{nr,nc}$ is UNSAT): the cell is logically guaranteed to contain a ship part. These are returned with highest priority.
2. **Consistent** ($KB \land SP_{nr,nc}$ is SAT): the cell *could* contain a ship part. These are returned only if no forced targets exist.
3. **Impossible** ($KB \land SP_{nr,nc}$ is UNSAT): the cell is guaranteed empty. Skipped.

The agent picks randomly among the forced targets (if any), otherwise among the consistent targets. When no open hits exist, falls back to a uniformly random unshot cell.

This strategy is implemented in `get_intelligent_hunt_targets()` and wrapped by `BattleshipIntelligentRandomStrategy`.

### Strategy 3: Checkerboard + Intelligent (`--strategy checkerboard`)

A hybrid two-phase strategy:

**Phase 1 — Discovery (checkerboard pattern)**: when no open hits exist, the agent picks from cells where $(r + c) \bmod 2 = 0$. This checkerboard pattern guarantees that any ship occupying $\geq 2$ cells must overlap at least one checkerboard cell, providing efficient board coverage without wasting shots on adjacent cells.

**Phase 2 — Hunting (SAT-guided)**: as soon as an open hit is detected, the agent switches to the same SAT-guided intelligent hunting as Strategy 2 (forced targets first, then consistent targets). Once the damaged ship is fully sunk (all its cells are covered by an asserted Sunk variable), the agent returns to Phase 1.

This strategy is implemented in `BattleshipCheckerboardIntelligentStrategy` and combines `get_checkerboard_targets()` with `get_intelligent_hunt_targets()`.

### Heuristic comparison

| Strategy | Discovery mode | Hunting mode | SAT queries per turn |
|----------|---------------|--------------|---------------------|
| Simple | Uniform random | Random neighbors | 0 |
| Intelligent | Uniform random | SAT-guided (forced/consistent) | Up to 2 per neighbor |
| Checkerboard + Intelligent | Checkerboard pattern | SAT-guided (forced/consistent) | Up to 2 per neighbor |


### SAT Query (used by Intelligent and Checkerboard strategies)

For each candidate neighbor $(nr, nc)$ of an open hit, the agent submits two queries using Glucose3's `solve(assumptions=[...])`:

1. **Forced check**: $SOLVE(KB \cup \{\neg SP_{nr,nc}\})$
   - If $UNSAT$: $KB \models SP_{nr,nc}$ — the cell **must** contain a ship part → shoot immediately
2. **Consistency check**: $SOLVE(KB \cup \{SP_{nr,nc}\})$
   - If $SAT$: the cell **could** contain a ship part → add to candidates
   - If $UNSAT$: $KB \models \neg SP_{nr,nc}$ — the cell is guaranteed empty → skip

The `assumptions` parameter is key: it temporarily assumes a literal for a single solve call without mutating the CNF, allowing the agent to probe many hypotheses without polluting the KB.

## Tech Stack
- PySAT for logic solver 
- PyGame for the game interface and multiplayer (agent vs agent and local player vs agent)

## Evaluation
- Baseline: pure random (simple strategy)
- Compare baseline vs intelligent (SAT-guided) vs checkerboard + intelligent
- Metrics: average turns to win and hit rate over 1000 games


## Conversion to CNF
- A a tile either contains a ShipPart or is empty: $(SP_{i,j} \land \neg E_{i,j}) \lor (\neg SP_{i,j} \land E_{i,j})$ applying distributed property (distribute the outer OR over inner conunctions) becomes $(SP_{i,j} \lor E_{i,j}) \land (\neg SP_{i,j} \lor \neg E_{i,j}))$

---

## Hunting Strategy with SAT

The agent uses a two-mode strategy implemented in `src/game_logic.py`:

1. **Random mode (default)**: when there are no "open hits" on the board, the agent picks a uniformly random unshot tile.
2. **Hunting mode**: as soon as the agent has at least one *open hit* — a tile where $Hit_{i,j}$ is asserted but no Sunk variable covering that tile is yet asserted — the agent uses the SAT solver to choose the next shot from cells adjacent to the open hit(s).

### Definitions

- **Open hit**: a cell $(r,c)$ such that the unit clause $Hit_{r,c}$ is in the KB, but no Sunk variable (types 10–13) covering $(r,c)$ is asserted. In other words, the agent knows it hit a ship part there, but the corresponding ship has not yet been fully destroyed.
- **Hunt candidate**: an unshot, in-bounds neighbor (all 8 directions: N, S, E, W, and diagonals) of an open hit. Diagonal neighbors are included because the Carrier is 2×2, so a diagonal cell can be part of the same ship.

### Algorithm: `get_hunt_targets`

The function `get_hunt_targets(board_size, cnf, shots_taken)` returns the next set of cells to shoot:

1. Collect all **open hits** by scanning the unit clauses of the CNF for asserted $Hit_{r,c}$ variables, excluding those covered by an asserted Sunk variable.
2. If no open hits exist, return an empty list (caller falls back to random).
3. For each open hit $(hr, hc)$, enumerate all 8 neighbors (orthogonal + diagonal). Diagonals are necessary because the Carrier occupies a 2×2 block, so a diagonal neighbor of a hit cell can be part of the same Carrier.
4. For each unshot, in-bounds neighbor $(nr, nc)$, query Glucose3 twice using `solver.solve(assumptions=[...])`:
   - **Priority 1 — Forced ship part**: ask whether $KB \cup \{\neg SP_{nr,nc}\}$ is UNSAT. If it is, then $KB \models SP_{nr,nc}$ and the cell is logically guaranteed to contain a ship part. Return this cell immediately.
   - **Priority 2 — Possible ship part**: ask whether $KB \cup \{SP_{nr,nc}\}$ is SAT. If it is, the cell is *consistent* with containing a ship part and is added to the candidate list.
   - **Otherwise** (i.e. $KB \cup \{SP_{nr,nc}\}$ is UNSAT), the cell is logically guaranteed to be empty; skip it.
5. Return the list of possible candidates.

### Key implementation detail: assumptions, not assertions

Glucose3's `solve(assumptions=[...])` method temporarily assumes the given literals are true **only for that single solve call**. This means the CNF itself is never mutated by the hunting logic — we can probe many hypotheses without polluting the KB. This is essential: we only want to *test* whether $SP_{nr,nc}$ is consistent, not commit to it.

### Switching modes

The agent switches modes automatically based on the state of the KB:

- After every shot, `record_shot` appends the appropriate unit clauses.
- After hits, `_propagate_sunk_variables` explicitly checks whether any Sunk variables covering the hit cell are now entailed, and asserts them as unit clauses. This is necessary because the SAT solver derives sunk truth internally but does not add unit clauses to the CNF.
- When a Sunk variable is asserted, `add_all_parts_sunk_consequences` clauses propagate $\neg SP$ to surrounding cells, which removes those open hits from the open-hit set.
- Therefore, the agent transitions from hunting back to random simply by checking on each turn whether `_get_open_hits` returns an empty list.

### Why this works

This strategy implements the agent strategy from the previous section precisely:

- The "forced" check (Priority 1) is the entailment query $KB \models SP_{i,j}$ — exactly the rule "if $KB \land \neg SP_{i,j}$ is UNSAT, shoot $(i,j)$."
- The "possible" check (Priority 2) is a relaxed version that picks logically consistent candidates when no cell is strictly forced. This handles the realistic case where the agent has one hit but does not yet know the ship's orientation.
- Restricting candidates to the 8 neighbors of open hits avoids wasteful solver queries on distant tiles. Diagonals are included to handle the 2×2 Carrier, while the SAT solver automatically eliminates diagonal candidates that are inconsistent with any ship placement.
