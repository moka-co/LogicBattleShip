# Logic Battle Ship

This project aims to create a logic agent (propositional logic) for solving the battleship game.

We refer to both the agent and the human that plays against the agent as player(s).

## Battleship Game - Knowledge Engineering
Battleship game is a 1v1 game where each player has a board composed of $N \times N$ tiles. Before the start of the game, the players can position a number $m$ of ships. (In this case we consider $2 \le m \le 4$ ships).
Ships are of different kinds and sizes. We distinguish an easier version of the game with a 5x5 board and two kinds of ships: $1\times 2$ and $1\times 4$. Ships must be placed inside the grid. Two ships cannot be placed adjacently and must be separated by a one‑tile distance.

In the 10x10 board we have the following kind of ships: $1\times 2, 1\times 3, 1\times 5, 4\times 4$. 

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

**Cannot place any ships e.g. Submarine and PatrolBoat adjacently**
- **PatrolBoat horizontal**: $PB_{h,i,j} \implies (\neg SP_{i,j-1} \land \neg SP_{i,j+2} \land \neg SP_{i+1,j} \land \neg SP_{i-1,j} \land \neg SP_{i+1,j+1} \land \neg SP_{i-1,j+1})$
- **PatrolBoat vertical**: $PB_{v,i,j} \implies (\neg SP_{i-1,j} \land \neg SP_{i+2,j} \land \neg SP_{i,j+1} \land \neg SP_{i,j-1} \land \neg SP_{i+1,j+1} \land \neg SP_{i+1,j-1})$
- **Submarine horizontal**: $SM_{h,i,j} \implies (\neg SP_{i,j-1} \land \neg SP_{i,j+3} \land \neg SP_{i+1,j} \land \neg SP_{i-1,j} \land \neg SP_{i+1,j-1} \land \neg SP_{i-1,j-1} \land \neg SP_{i+1,j+1} \land \neg SP_{i-1,j+1} \land \neg SP_{i+1,j+2} \land \neg SP_{i-1,j+2})$
- **Submarine vertical**: $SM_{v,i,j} \implies (\neg SP_{i-1,j} \land \neg SP_{i+3,j} \land \neg SP_{i,j+1} \land \neg SP_{i,j-1} \land \neg SP_{i-1,j+1} \land \neg SP_{i-1,j-1} \land \neg SP_{i+1,j+1} \land \neg SP_{i+1,j-1} \land \neg SP_{i+2,j+1} \land \neg SP_{i+2,j-1})$

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

**Sunk Patrol Boat (both directions)**:
- $Sunk_{PatrolBoat_{h,i,j}} \iff (Hit_{i,j} \land Hit_{i,j+1})$
- $Sunk_{PatrolBoat_{v,i,j}} \iff Hit_{i,j} \land Hit_{i+1,j}$

**Sunk Submarine (both directions)**
- $Sunk_{Submarine_{h,i,j}} \iff (Hit_{i,j} \land Hit_{i,j+1} \land Hit_{i,j+2})$ 
- $Sunk_{Submarine_{v,i,j}} \iff (Hit_{i,j} \land Hit_{i+1,j} \land Hit_{i+2,j})$

**Sunk Battleship (both directions)**
- $Sunk_{Battleship_{h,i,j}} \iff (Hit_{i,j} \land Hit_{i,j+1} \land Hit_{i,j+2} \land Hit_{i,j+3})$ 
- $Sunk_{Battleship_{v,i,j}} \iff (Hit_{i,j} \land Hit_{i+1,j} \land Hit_{i+2,j} \land Hit_{i+3,j})$


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


---

## Knowledge Base
- Constraint: propositional logic with PySAT as logic 
- The agent uses a SAT solver to look for tiles that are shot, if that it tries to shoot adjacent tiles using logic. Otherwise it shot at random.
- At each turn the KB is updated and the new information is added to the Knowledge Base

**KB update after each shot**:
- On a miss: $\text{Assert: } Miss_{i,j}$ which immediately entails: $¬SP_{i,j}$
- On a hit: $\text{Assert: } Hit_{i,j}$ which immediately entails: $SP_{i,j}$
- Additionally, after every shot: $\text{Assert: } Shot_{i,j}$

The KB grows monotonically, facts are only added never retracted since observations in Battleship are permanent.

## Agent Strategy
Formally, at each turn the agent must select a tile $(i,j)$ such that $\neg Shot_{i,j}$ (not yet shot).
- If exists at least one $Hit_{i,j}$ whose ship is not sunk yet, the agent queries the SAT solver to find tiles that could contain a ship given the current KB: $KB \models SP_{i,j}$ 
    - This is check via entailment: a tile is entailed to contain a ship if and only if $KB \land \neg SP_{i,j}$ is UNSATISFIABLE. If the solver returns UNSAT (e.g. () ), then $(i,j)$ must be a ship part and is the next shot
    - Note: technically you can't really know until you hit, for instance the solver could still choose an empty tile, however that is still a good candidate so we can assume that this entailment logically find a tile that must contain a ship part.
- If no such tile exists, use an heuristic to shot the next tile. The baseline is randomly uniform, see Heuristics section.

**Heuristics**:
- Randomly uniform: $Choose(i,j) \text{ uniformly from } \{(i,j)| \neg Shot_{i,j}\}$
- Every Other Two: at each step, if $Hit(i,j)$ and $\neg SP(i,j)$ then choose either $Choose(i+2,j)$ or $Choose(i,j+2)$ if the choosen coordinates are inside the grid. If there is not previously hitten tiles, start from $(0,0)$. 


**SAT Query**:

At each turn, for every unshot tile $(i,j)$, the agents submits: $SOLVE(KB \cup \{\neg SP_{i,j}\})$
- If $UNSAT \to SP_{i,j}$ is entailed $\to$ shoot(i,j)
- If $SAT \to SP_{i,j}$ is not guaranteed $\to$ skip (use heuristic)

## Tech Stack
- PySAT for logic solver 
- PyGame for the game interface and multiplayer (agent vs agent and local player vs agent)

## Evaluation
- Baseline: pure random
- Compare baseline vs every other two
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
- **Hunt candidate**: an unshot, in-bounds neighbor (N, S, E, W only — never diagonals, since ships are linear) of an open hit.

### Algorithm: `get_hunt_targets`

The function `get_hunt_targets(board_size, cnf, shots_taken)` returns the next set of cells to shoot:

1. Collect all **open hits** by scanning the unit clauses of the CNF for asserted $Hit_{r,c}$ variables, excluding those covered by an asserted Sunk variable.
2. If no open hits exist, return an empty list (caller falls back to random).
3. For each open hit $(hr, hc)$, enumerate the 4 orthogonal neighbors $(hr \pm 1, hc)$ and $(hr, hc \pm 1)$.
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
- After hits, the `add_sinking_constraints` biconditionals automatically cause a Sunk variable to be propagated to true (the SAT solver implicitly handles this).
- When all parts of a ship are sunk, `add_all_parts_sunk_consequences` clauses propagate $\neg SP$ to surrounding cells, which removes those open hits from the open-hit set.
- Therefore, the agent transitions from hunting back to random simply by checking on each turn whether `_get_open_hits` returns an empty list.

### Why this works

This strategy implements the agent strategy from the previous section precisely:

- The "forced" check (Priority 1) is the entailment query $KB \models SP_{i,j}$ — exactly the rule "if $KB \land \neg SP_{i,j}$ is UNSAT, shoot $(i,j)$."
- The "possible" check (Priority 2) is a relaxed version that picks logically consistent candidates when no cell is strictly forced. This handles the realistic case where the agent has one hit but does not yet know the ship's orientation.
- Restricting candidates to the orthogonal neighbors of open hits avoids wasteful solver queries on tiles that are physically impossible ship continuations.
