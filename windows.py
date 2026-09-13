import time
import random as rd
import math
from PyQt5.QtWidgets import (QWidget, QGridLayout, QSlider, QProgressBar, QLabel, QVBoxLayout, QLineEdit, QPushButton, QComboBox, QGroupBox, QHBoxLayout)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QPalette, QBrush
from mpi4py import MPI

import drones
import constants as cst
import packages

COMM = MPI.COMM_WORLD
RANK = COMM.Get_rank()
SIZE = COMM.Get_size()


class Window(QWidget):

    def __init__(self, name, rank, leader, size):
        super().__init__()
        self.name = name
        self.rank = rank
        self.leader = leader
        self.size = size
        
        self.my_ping = cst.LIST_PING_S[self.rank]
        self.drones_alive = [i for i in range(self.size)]
        self.list_drones = []
        self.list_packages = [] 
        self.packages_state = {} 
        self.warnings_registry = {}
        self.my_warnings = 0 
        
        self.updateTitle()

        self.setGeometry(self.rank * cst.WINDOW_X, ((self.rank + 1) % 2) * cst.WINDOW_Y + 40, cst.WINDOW_WIDTH, cst.TOTAL_HEIGHT)
        
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

        self.map_widget = QWidget()
        self.map_widget.setFixedSize(cst.WINDOW_WIDTH, cst.WINDOW_HEIGHT)
        self.map_widget.setAutoFillBackground(True)
        
        palette = self.map_widget.palette()
        try:
            pixmap = QPixmap("background.jpg")
            resized_pixmap = pixmap.scaled(cst.WINDOW_WIDTH, cst.WINDOW_HEIGHT, Qt.KeepAspectRatio)
            palette.setBrush(QPalette.Window, QBrush(resized_pixmap))
        except:
            palette.setColor(QPalette.Window, Qt.lightGray)
        self.map_widget.setPalette(palette)

        self.map_layout = QGridLayout(self.map_widget)
        self.map_layout.setContentsMargins(0, 0, 0, 0)
        
        self.drone = drones.Drone(self.rank)
        self.map_layout.addWidget(self.drone, 0, 0)
        
        self.initPackages()
        self.main_layout.addWidget(self.map_widget)

        self.controls_widget = QWidget()
        self.controls_widget.setFixedHeight(cst.CONTROL_HEIGHT)
        self.controls_widget.setStyleSheet("background-color: white; border-top: 2px solid #333;")
        
        self.controls_layout = QGridLayout(self.controls_widget)
        self.controls_layout.setContentsMargins(10, 20, 10, 0)

        config_group = QGroupBox("Configuration Drone")
        config_group.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 5px; subcontrol-position: top center;")
        config_layout = QVBoxLayout()

        name_layout = QHBoxLayout()
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("New name...")
        self.input_name.setStyleSheet("background-color: white;")
        self.btn_name = QPushButton("OK")
        self.btn_name.setFixedWidth(40)
        self.btn_name.clicked.connect(self.updateName)
        name_layout.addWidget(self.input_name)
        name_layout.addWidget(self.btn_name)

        self.lbl_speed = QLabel("Speed")
        self.jauge = QProgressBar()
        self.jauge.setRange(0, 100)
        self.jauge.setValue(0)
        self.jauge.setTextVisible(True)
        self.jauge.setFixedHeight(25)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(cst.NB_PIXELS_MOVE)
        self.slider.valueChanged.connect(self.jauge.setValue)
        self.slider.valueChanged.connect(self.changeSpeed)

        config_layout.addLayout(name_layout)
        config_layout.addWidget(self.lbl_speed)
        config_layout.addWidget(self.jauge)
        config_layout.addWidget(self.slider)
        config_group.setLayout(config_layout)

        comm_group = QGroupBox("Mailbox")
        comm_group.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 5px;")
        comm_layout = QVBoxLayout()

        self.combo_target = QComboBox()
        self.combo_target.setStyleSheet("background-color: white;")
        self.combo_target.addItem("Recipient...")
        for i in range(self.size):
            if i != self.rank:
                self.combo_target.addItem(f"Drone {i}", userData = i)
        
        self.input_msg = QLineEdit()
        self.input_msg.setPlaceholderText("Message (ending with \".\" )")
        self.input_msg.setStyleSheet("background-color: white;")
        
        self.btn_send_msg = QPushButton("Send")
        self.btn_send_msg.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_send_msg.clicked.connect(self.sendTextMessage)

        comm_layout.addWidget(self.combo_target)
        comm_layout.addWidget(self.input_msg)
        comm_layout.addWidget(self.btn_send_msg)
        comm_group.setLayout(comm_layout)

        self.controls_layout.addWidget(config_group, 0, 0)
        self.controls_layout.addWidget(comm_group, 0, 1)

        self.lbl_warning = QLabel("Warnings: 0/3")
        self.lbl_warning.setStyleSheet("color: red; font-weight: bold; border: none;")
        self.lbl_warning.setAlignment(Qt.AlignCenter)
        self.controls_layout.addWidget(self.lbl_warning, 1, 0, 1, 2)

        self.main_layout.addWidget(self.controls_widget)

        self.msg_display = QLabel("", self)
        self.msg_display.setAlignment(Qt.AlignCenter)
        self.msg_display.setStyleSheet("background-color: rgba(0, 0, 0, 200); color: white; border-radius: 10px; padding: 10px; font-weight: bold;")
        self.msg_display.hide()
        self.msg_display.setGeometry(50, 100, cst.WINDOW_WIDTH - 100, 60)
        self.msg_display.raise_()

        self.setFocusPolicy(Qt.StrongFocus) 
        self.setFocus() 

        self.timer_death = QTimer(self)
        self.timer_death.timeout.connect(self.checkDeath)
        self.timer_death.start(20)
        self.timer_msg = QTimer(self)
        self.timer_msg.timeout.connect(self.checkMessages)
        self.timer_msg.start(10)

        self.timer_names = QTimer(self)
        self.timer_names.timeout.connect(self.checkNames)
        self.timer_names.start(100) 
        
        self.timer_pkg = QTimer(self)
        self.timer_pkg.timeout.connect(self.checkPackageNetwork)
        self.timer_pkg.start(20)
        
        self.timer_txt = QTimer(self)
        self.timer_txt.timeout.connect(self.checkTextMessages)
        self.timer_txt.start(50)

    
    def send_safe(self, data, dest, tag):
        """Help to avoid crashes if the is recipient dead"""
        if dest not in self.drones_alive: 
            return None
        
        try:
            COMM.send(data, dest = dest, tag = tag)
        except Exception:
            if dest in self.drones_alive:
                self.drones_alive.remove(dest)

    def simulatePing(self):
        """Stop the program to simulate the ping"""
        if self.my_ping > 0:
            time.sleep(self.my_ping)

    def updateTitle(self):
        """Update the window's title to display the leader"""
        role = " (LEADER)" if self.rank == self.leader else f" (Leader: {self.leader})"
        ping_info = f" | Ping: {self.my_ping * 1000:.0f}ms" if self.my_ping > 0 else ""
        self.setWindowTitle(f"{self.name} | Rank {self.rank}{role}{ping_info}")

    def changeSpeed(self, value):
        """Change the drone's speed"""
        cst.NB_PIXELS_MOVE = value
    
    def updateName(self):
        """The leader updates the name of other drones"""
        new_name = self.input_name.text()
        if new_name: 
            self.drone.name = new_name
            self.drone.update() 
            self.updateTitle()
            data_name = [self.rank, new_name]
            if self.rank == self.leader:
                for i in self.drones_alive:
                    if i != self.leader:
                        self.send_safe(data_name, dest = i, tag = 7) 
            else:
                self.send_safe(data_name, dest = self.leader, tag = 6) 
            self.setFocus()
    
    def updateComboName(self, rank, new_name):
        """Update the list of recipients in the drop-down menu"""
        for i in range(self.combo_target.count()):
            if self.combo_target.itemData(i) == rank:
                self.combo_target.setItemText(i, new_name)
                break

    def sendTextMessage(self):
        """Prepare the message et send it to the leader"""
        target_idx = self.combo_target.currentIndex()
        text = self.input_msg.text()
        if target_idx > 0 and text: 
            target_rank = self.combo_target.itemData(target_idx)
            req = [self.rank, target_rank, text]
            if self.rank == self.leader:
                self.processTextRequest(req)
            else:
                self.send_safe(req, dest = self.leader, tag = 10)
            self.input_msg.clear()
        self.setFocus() 

    def processTextRequest(self, req):
        """Get and check the message received by the leader"""
        sender, target, text = req
        is_valid = len(text.strip()) > 0 and text.strip().endswith('.')
        if is_valid:
            msg_data = [sender, text]
            if target == self.leader:
                self.displayReceivedMessage(sender, text)
            else:
                if target in self.drones_alive:
                    self.send_safe(msg_data, dest = target, tag = 11)
        else:
            current_warn = self.warnings_registry.get(sender, 0) + 1
            self.warnings_registry[sender] = current_warn
            kill_order = False
            if current_warn >= 3:
                kill_order = True
                print(f"Leader: Killing Drone {sender} due to 3 warnings.")
                for i in self.drones_alive:
                    if i != self.leader:
                        self.send_safe(sender, dest = i, tag = 4)
                if sender < len(self.list_drones):
                    self.list_drones[sender].hide()
                if sender in self.drones_alive:
                    self.drones_alive.remove(sender)
            warn_data = [current_warn, kill_order]
            if sender == self.leader:
                self.handleWarning(warn_data)
            else:
                if sender in self.drones_alive:
                    self.send_safe(warn_data, dest = sender, tag = 12)

    def displayReceivedMessage(self, sender_rank, text):
        """Display the message when it is verified and received"""
        sender_name = "Unkwnow"
        if sender_rank < len(self.list_drones):
            sender_name = self.list_drones[sender_rank].name
        self.msg_display.setText(f"Message from {sender_name}:\n{text}")
        self.msg_display.adjustSize()
        self.msg_display.show()
        QTimer.singleShot(5000, self.msg_display.hide)

    def handleWarning(self, data):
        """Update the number of warnings et kill on the order of the leader"""
        count, is_killed = data
        self.my_warnings = count
        self.lbl_warning.setText(f"Warnings : {self.my_warnings}/3")
        if is_killed:
            self.msg_display.setText("Killed by the leader")
            self.msg_display.setStyleSheet("background-color: red; color: white; padding: 20px;")
            self.msg_display.show()
            self.drone.hide()
            self.setDisabled(True) 
            QTimer.singleShot(2000, self.close)

    def checkTextMessages(self):
        """Check if a message is coming in"""
        try:
            if self.rank == self.leader:
                while COMM.Iprobe(source = MPI.ANY_SOURCE, tag = 10):
                    self.simulatePing() 
                    req = COMM.recv(source = MPI.ANY_SOURCE, tag = 10)
                    self.processTextRequest(req)
            if self.rank != self.leader:
                if self.leader not in self.drones_alive: return
                while COMM.Iprobe(source = self.leader, tag = 11):
                    self.simulatePing()
                    data = COMM.recv(source = self.leader, tag = 11)
                    self.displayReceivedMessage(data[0], data[1])
                while COMM.Iprobe(source = self.leader, tag = 12):
                    self.simulatePing()
                    data = COMM.recv(source = self.leader, tag = 12)
                    self.handleWarning(data)
        except Exception:
            pass

    def initPackages(self):
        """Put randomly packages on the map"""
        rd.seed(42) 
        for i in range(3): 
            px = rd.randint(50, cst.WINDOW_WIDTH - 100)
            py = rd.randint(50, cst.WINDOW_HEIGHT - 100)
            p = packages.Package(i, px, py)
            self.list_packages.append(p)
            self.packages_state[i] = False 
            self.map_layout.addWidget(p, 0, 0) 
        rd.seed() 

    def keyPressEvent(self, event):
        """Catch or drop a package is the drone is in the right place when the space bar is pressed"""
        if event.key() == Qt.Key_Space:
            my_drone = self.list_drones[self.rank]
            if my_drone.has_package:
                pkg_id_to_drop = my_drone.package_id
                req = [self.rank, pkg_id_to_drop, 0, my_drone.x, my_drone.y] 
                if self.rank == self.leader:
                    self.processPackageRequest(req) 
                else:
                    self.send_safe(req, dest = self.leader, tag = 8)
            else:
                for pkg in self.list_packages:
                    dist = math.sqrt((my_drone.x - pkg.x)**2 + (my_drone.y - pkg.y)**2)
                    if dist < cst.DRONE_SIZE * 1.5 and pkg.visible: 
                        req = [self.rank, pkg.id, 1, 0, 0]
                        if self.rank == self.leader:
                            self.processPackageRequest(req)
                        else:
                            self.send_safe(req, dest = self.leader, tag = 8)
                        break 

    def processPackageRequest(self, req):
        """Catch or drop a package of a drone by the leader"""
        sender_rank, pkg_id, action, d_x, d_y = req
        if action == 1:
            if not self.packages_state.get(pkg_id, True): 
                self.packages_state[pkg_id] = True 
                msg = [sender_rank, pkg_id, True, 0, 0]
                self.broadcastPackageUpdate(msg)
        elif action == 0:
            if pkg_id != -1:
                self.packages_state[pkg_id] = False 
                msg = [sender_rank, pkg_id, False, d_x, d_y]
                self.broadcastPackageUpdate(msg)

    def broadcastPackageUpdate(self, msg):
        """Synchronize packages across all windows"""
        for i in self.drones_alive:
            if i != self.leader:
                self.send_safe(msg, dest = i, tag = 9)
        self.applyPackageUpdate(msg)

    def applyPackageUpdate(self, data):
        """Display correctly packages across all windows"""
        drone_rank, pkg_id, is_taken, x, y = data
        if drone_rank < len(self.list_drones):
            d = self.list_drones[drone_rank]
            d.has_package = is_taken
            d.package_id = pkg_id if is_taken else -1
            d.update()
        if pkg_id < len(self.list_packages) and pkg_id >= 0:
            p = self.list_packages[pkg_id]
            if is_taken:
                p.visible = False
            else:
                p.x = x
                p.y = y
                p.visible = True
            p.update()
            if self.rank == self.leader: self.packages_state[pkg_id] = is_taken

    def checkPackageNetwork(self):
        """Infinite loop for the function 'applyPackageUpdate'"""
        try:
            if self.rank == self.leader:
                while COMM.Iprobe(source = MPI.ANY_SOURCE, tag = 8):
                    self.simulatePing()
                    req = COMM.recv(source = MPI.ANY_SOURCE, tag = 8)
                    self.processPackageRequest(req)
            if self.rank != self.leader:
                if self.leader not in self.drones_alive: 
                    return None
                while COMM.Iprobe(source = self.leader, tag = 9):
                    self.simulatePing()
                    data = COMM.recv(source = self.leader, tag = 9)
                    self.applyPackageUpdate(data)
        except Exception:
            pass

    def checkNames(self):
        """Update the names of the drones across all windows"""
        try:
            source_recv = MPI.ANY_SOURCE if self.rank == self.leader else self.leader
            tag_recv = 6 if self.rank == self.leader else 7 
            if self.rank != self.leader and self.leader not in self.drones_alive: 
                return None
            while COMM.Iprobe(source = source_recv, tag = tag_recv):
                self.simulatePing()
                data = COMM.recv(source = source_recv, tag = tag_recv)
                sender_rank = data[0]
                name_str = data[1]
                if sender_rank < len(self.list_drones):
                    self.list_drones[sender_rank].name = name_str
                    self.list_drones[sender_rank].update() 
                    self.updateComboName(sender_rank, name_str)
                if self.rank == self.leader:
                    for i in self.drones_alive:
                        if i != self.leader and i != sender_rank: 
                            self.send_safe(data, dest = i, tag = 7)
        except Exception:
            pass

    def closeEvent(self, event):
        """Handle the closure of the windows"""
        print(f"Closing Window. Rank {self.rank} is out.")
        for i in range(self.size):
            if i != self.rank:

                try:
                    COMM.send(self.rank, dest = i, tag = 4)
                except:
                    pass

        time.sleep(0.5)
        event.accept()

    def checkDeath(self):
        """Detect the death of a drone, clean the windows and handle the election of the new leader"""
        try:
            while COMM.Iprobe(source = MPI.ANY_SOURCE, tag = 5):
                self.simulatePing()
                new_leader = COMM.recv(source = MPI.ANY_SOURCE, tag = 5)
                self.leader = new_leader
                print(f"New Elected Leader (via time) : Drone {self.leader}")
                self.updateTitle()
        except Exception:
            pass

        try:
            while COMM.Iprobe(source = MPI.ANY_SOURCE, tag = 4):
                self.simulatePing()
                drone_dead = COMM.recv(source = MPI.ANY_SOURCE, tag = 4)
                if drone_dead < len(self.list_drones):
                    self.list_drones[drone_dead].hide()
                if drone_dead in self.drones_alive:
                    self.drones_alive.remove(drone_dead)
                idx_to_remove = -1                           
                for i in range(self.combo_target.count()):
                    if self.combo_target.itemData(i) == drone_dead:
                        idx_to_remove = i
                        break
                if idx_to_remove != -1:
                    self.combo_target.removeItem(idx_to_remove)
                if drone_dead == self.leader:
                    if self.drones_alive:
                        coordinator = min(self.drones_alive)
                        if self.rank == coordinator:
                            t = int(time.time())
                            idx = t % len(self.drones_alive)
                            new_leader = self.drones_alive[idx]
                            self.leader = new_leader
                            print(f"Coordinator ({self.rank}) : Election by time ({t}). New Leader : {self.leader}")
                            self.updateTitle()
                            for i in self.drones_alive:
                                if i != self.rank:

                                    try:
                                        COMM.send(new_leader, dest = i, tag = 5)
                                    except:
                                        pass

                        else:
                            pass
                    else:
                        print("Last surviving drone.")
        except Exception:
            pass

    def addDrones(self):
        """Display the drones when the program starts"""
        for i in range(self.size):
             if i < len(self.list_coord):
                coords = self.list_coord[i]
                x, y, r, g, b = coords
                if i == self.rank:
                    self.list_drones.append(self.drone)
                else:
                    new_drone = drones.Drone(i, x, y, r, g, b)
                    self.list_drones.append(new_drone)
                    self.map_layout.addWidget(new_drone, 0, 0)

    def processMovementRequest(self, req):
        """Verified is the movements of drones are allowed"""
        sender, f_x, f_y = req
        valid_boundaries = (0 <= f_x <= cst.WINDOW_WIDTH - cst.DRONE_SIZE) and (0 <= f_y <= cst.WINDOW_HEIGHT - cst.DRONE_SIZE)
        if not valid_boundaries: 
            return None
        collision = False
        for d in self.list_drones:
            if d.rank != sender and d.isVisible() and (d.rank in self.drones_alive):
                dist = math.sqrt((f_x - d.x)**2 + (f_y - d.y)**2)
                if dist < cst.DRONE_SIZE * 1.5:
                    collision = True
                    break
        if collision: 
            return None 
        official_data = [sender, f_x, f_y]
        self.applyMovementUpdate(official_data)
        for i in self.drones_alive:
            if i != self.leader:
                self.send_safe(official_data, dest = i, tag = 2)

    def applyMovementUpdate(self, data):
        """Update the psotion of a drone"""
        sender_rank, new_x, new_y = data
        if sender_rank < len(self.list_drones):
            d = self.list_drones[sender_rank]
            d.x = new_x
            d.y = new_y
            d.update()

    def checkMessages(self):
        """Check if there messages about movements are coming in"""
        try:
            if self.rank == self.leader:
                while COMM.Iprobe(source = MPI.ANY_SOURCE, tag = 1):
                    self.simulatePing() 
                    req = COMM.recv(source = MPI.ANY_SOURCE, tag = 1)
                    self.processMovementRequest(req)
            if self.rank != self.leader:
                if self.leader not in self.drones_alive: 
                    return None
                while COMM.Iprobe(source = self.leader, tag = 2):
                    self.simulatePing() 
                    data = COMM.recv(source = self.leader, tag = 2)
                    self.applyMovementUpdate(data)
        except Exception:
            pass

    def updateLeftDrones(self):
        """Move the drone to the left"""
        future_x = self.list_drones[self.rank].x - cst.NB_PIXELS_MOVE
        future_y = self.list_drones[self.rank].y
        req = [self.rank, future_x, future_y]
        if self.rank == self.leader:
            self.processMovementRequest(req)
        else:
            self.send_safe(req, dest = self.leader, tag = 1)

    def updateRightDrones(self):
        """Move the drone to the right"""
        future_x = self.list_drones[self.rank].x + cst.NB_PIXELS_MOVE
        future_y = self.list_drones[self.rank].y
        req = [self.rank, future_x, future_y]
        if self.rank == self.leader:
            self.processMovementRequest(req)
        else:
            self.send_safe(req, dest = self.leader, tag = 1)
    
    def updateUpDrones(self):
        """Move the drone up"""
        future_x = self.list_drones[self.rank].x
        future_y = self.list_drones[self.rank].y - cst.NB_PIXELS_MOVE
        req = [self.rank, future_x, future_y]
        if self.rank == self.leader:
            self.processMovementRequest(req)
        else:
            self.send_safe(req, dest = self.leader, tag = 1)

    def updateDownDrones(self):
        """Move the drone down"""
        future_x = self.list_drones[self.rank].x
        future_y = self.list_drones[self.rank].y + cst.NB_PIXELS_MOVE
        req = [self.rank, future_x, future_y]
        if self.rank == self.leader:
            self.processMovementRequest(req)
        else:
            self.send_safe(req, dest = self.leader, tag = 1)