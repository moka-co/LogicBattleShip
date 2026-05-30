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


Once you've hit all parts of a ship, you know the surrounding area is empty:
- $AllPartsSunk_{PatrolBoat} \implies \bigwedge_{tiles\ adjacent\ to\ PatrolBoat} \neg SP_{tile}$

