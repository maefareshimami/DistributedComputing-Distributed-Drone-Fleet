from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QBrush
from PyQt5.QtWidgets import QWidget

import constants as cst


class Package(QWidget):
    
    def __init__(self, id, x, y):
        super().__init__()
        self.id = id
        self.x = x
        self.y = y
        self.visible = True
        self.resize(cst.WINDOW_WIDTH, cst.WINDOW_HEIGHT)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.show()

    
    def paintEvent(self, event):
        """Draw the packages"""
        if self.visible:
            pkg = QPainter()
            pkg.begin(self)
            pkg.setRenderHint(QPainter.Antialiasing)
            pkg.setPen(QPen(Qt.black, 2, Qt.SolidLine))
            pkg.setBrush(QBrush(Qt.yellow)) 
            pkg.drawRect(self.x, self.y, cst.DRONE_SIZE, cst.DRONE_SIZE)
            pkg.end()