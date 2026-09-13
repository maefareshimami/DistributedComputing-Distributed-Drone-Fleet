import time
import sys
import windows
from PyQt5.QtWidgets import QApplication, QShortcut
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt
from mpi4py import MPI


COMM = MPI.COMM_WORLD
RANK = COMM.Get_rank()
SIZE = COMM.Get_size()


if RANK == 0:
    t = int(time.time())
    elected_leader = t % SIZE
else:
    elected_leader = None

LEADER = COMM.bcast(elected_leader, root = 0)

app = QApplication(sys.argv)
win = windows.Window(f"Drone {RANK}", RANK, LEADER, SIZE)
win.drones_alive = [i for i in range(0, SIZE)]

data = COMM.gather(win.drone.sendData(), root = LEADER)

if RANK == LEADER:
    win.list_coord = data
    win.addDrones()
    data_coord = data
elif RANK != LEADER:
    data_coord = None

data_coord = COMM.bcast(data_coord, root = LEADER)

if RANK != LEADER:
    win.list_coord = data_coord
    win.addDrones()

left_arrow = QShortcut(QKeySequence(Qt.Key_Left), win)
right_arrow = QShortcut(QKeySequence(Qt.Key_Right), win)
up_arrow = QShortcut(QKeySequence(Qt.Key_Up), win)
down_arrow = QShortcut(QKeySequence(Qt.Key_Down), win)

left_arrow.activated.connect(win.updateLeftDrones)
right_arrow.activated.connect(win.updateRightDrones)
up_arrow.activated.connect(win.updateUpDrones)
down_arrow.activated.connect(win.updateDownDrones)


win.show()

app.exec()