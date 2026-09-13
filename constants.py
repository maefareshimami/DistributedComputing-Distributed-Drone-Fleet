import sys
from mpi4py import MPI


DRONE_IMAGE = "drone_image.jpg"
COMM = MPI.COMM_WORLD
SIZE = COMM.Get_size()


LIST_PING_MS = [0.0] * SIZE


if len(sys.argv) > 1:
    for arg in sys.argv[1:]:
        if arg.startswith("ping_"):
            try:
                parts = arg.split('=')
                key = parts[0]   
                val = float(parts[1]) 
                node_id = int(key.split('_')[1])
                if 0 <= node_id < SIZE:
                    LIST_PING_MS[node_id] = val
            except (ValueError, IndexError):
                pass

LIST_PING_S = [p / 1000.0 for p in LIST_PING_MS] 

WINDOW_X = 450
WINDOW_Y = 450

WINDOW_WIDTH = 550
WINDOW_HEIGHT = 450

CONTROL_HEIGHT = 225

TOTAL_HEIGHT = WINDOW_HEIGHT + CONTROL_HEIGHT

DRONE_SIZE = 30
NB_PIXELS_MOVE = 10