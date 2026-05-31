from pysat.formula import CNF
from utils import get_var


def init_empty_board(board_size = 10):
    board_cnf = CNF()

    for r in range(board_size):
        for c in range(board_size):
            sp = get_var(board_size,1, r, c)
            e = get_var(board_size, 2, r, c)

            # A tile either contains a ShipPart or is Empty (exclusive)
            board_cnf.append([sp, e])
            board_cnf.append([-sp, -e])
    
    return board_cnf