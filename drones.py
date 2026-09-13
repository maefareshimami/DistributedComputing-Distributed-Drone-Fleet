import random as rd
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

import constants as cst


class Drone(QWidget):

    def __init__(self, rank, x = rd.randint(0, cst.WINDOW_WIDTH - 3 * cst.DRONE_SIZE), y = rd.randint(0, cst.WINDOW_HEIGHT - 3 * cst.DRONE_SIZE), r = rd.randint(0, 256), g = rd.randint(0, 256), b = rd.randint(0, 256)):
        super().__init__()
        self.rank = rank
        self.name = f"Drone {rank}"
        self.x = x
        self.y = y
        self.r = r
        self.g = g
        self.b = b
        self.has_package = False
        self.package_id = -1 
        self.drone_pixmap = QPixmap(cst.DRONE_IMAGE)
        self.raise_()
        self.show()

    def __repr__(self):
        return f"<class Drone: {self.rank} | Color: RGB({self.r}, {self.g}, {self.b})>"


    def paintEvent(self, event):
        """Draw the drone"""
        drn = QPainter()
        drn.begin(self)           
        drn.setRenderHint(QPainter.Antialiasing)
        
        drn.setPen(QPen(Qt.red, 1, Qt.DashLine))
        drn.setBrush(Qt.NoBrush)
        safety_radius = int(cst.DRONE_SIZE * 1.5)
        offset = (safety_radius - cst.DRONE_SIZE) / 2
        drn.drawEllipse(int(self.x - offset), int(self.y - offset), safety_radius, safety_radius)
        
        scaled_pixmap = self.drone_pixmap.scaled(cst.DRONE_SIZE, cst.DRONE_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        drn.drawPixmap(self.x, self.y, scaled_pixmap)

        drn.setPen(QPen(Qt.black, 3, Qt.SolidLine))
        drn.setBrush(QBrush(QColor(self.r, self.g, self.b, 170)))
        drn.drawEllipse(self.x, self.y, cst.DRONE_SIZE, cst.DRONE_SIZE)
        
        if self.has_package:
            drn.setBrush(QBrush(Qt.yellow))
            drn.drawRect(self.x + int(cst.DRONE_SIZE / 4), self.y + int(cst.DRONE_SIZE / 4), int(cst.DRONE_SIZE / 2), int(cst.DRONE_SIZE / 2))

        drn.setPen(QPen(QColor(self.r, self.g, self.b))) 
        drn.drawText(self.x, self.y - 5, self.name) 
        
        drn.end()
    
    def sendData(self):
        """Send coordinates and the drone color to other drones"""
        return self.x, self.y, self.r, self.g, self.b