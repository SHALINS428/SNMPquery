import time
import sqlite3
from pysnmp.hlapi import *
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem,QPushButton, QMessageBox, QHBoxLayout, QLineEdit)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal



def snmp_get(ip, oid, port=161):
    try:
        iterator = getCmd(SnmpEngine(),
                          CommunityData('public', mpModel=0),
                          UdpTransportTarget((ip, port)),
                          ContextData(),
                          ObjectType(ObjectIdentity(oid)))
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        if errorIndication or errorStatus:
            return None
        else:
            for varBind in varBinds:
                return varBind[1]
    except Exception as e:
        return None



class DatabaseManager:
    def __init__(self, db_name="hosts.db"):
        self.db_name = db_name  # 保存数据库文件名
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS hosts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            port INTEGER NOT NULL,
            sysDescr TEXT,
            sysName TEXT,
            sysUpTime TEXT,
            sysLocation TEXT,
            customData TEXT DEFAULT '',
            lastUpdated TEXT,
            UNIQUE(ip, port) ON CONFLICT REPLACE
        )
        """
        self.conn.execute(query)
        self.conn.commit()

    def add_or_update_host(self, ip, port, sysDescr, sysName, sysUpTime, sysLocation):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        query = """
        INSERT INTO hosts (ip, port, sysDescr, sysName, sysUpTime, sysLocation, lastUpdated)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ip, port) DO UPDATE SET
            sysDescr=excluded.sysDescr,
            sysName=excluded.sysName,
            sysUpTime=excluded.sysUpTime,
            sysLocation=excluded.sysLocation,
            lastUpdated=excluded.lastUpdated
        """
        self.conn.execute(query, (ip, port, sysDescr or "N/A", sysName or "N/A", sysUpTime or "N/A",
                                  sysLocation or "N/A", timestamp))
        self.conn.commit()

    def get_all_hosts(self):
        cursor = self.conn.execute("SELECT * FROM hosts")
        return cursor.fetchall()

    def update_custom_data(self, host_id, custom_data):
        query = "UPDATE hosts SET customData=? WHERE id=?"
        self.conn.execute(query, (custom_data, host_id))
        self.conn.commit()

    def delete_host(self, host_id):
        query = "DELETE FROM hosts WHERE id=?"
        self.conn.execute(query, (host_id,))
        self.conn.commit()


# SNMP Query Thread
class SNMPQueryThread(QThread):
    update_signal = pyqtSignal()

    def __init__(self, db_name):
        super().__init__()
        self.db_name = db_name

    def run(self):
        oids = {
            "sysDescr": '1.3.6.1.2.1.1.1.0',
            "sysName": '1.3.6.1.2.1.1.5.0',
            "sysUpTime": '1.3.6.1.2.1.1.3.0',
            "sysLocation": '1.3.6.1.2.1.1.6.0',
        }
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        try:
            for port in range(16101, 16160):
                ip = "127.0.0.1"
                sysDescr = snmp_get(ip, oids["sysDescr"], port)
                sysName = snmp_get(ip, oids["sysName"], port)
                sysUpTime = snmp_get(ip, oids["sysUpTime"], port)
                sysLocation = snmp_get(ip, oids["sysLocation"], port)

                if sysDescr or sysName:
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("""
                    INSERT INTO hosts (ip, port, sysDescr, sysName, sysUpTime, sysLocation, lastUpdated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(ip, port) DO UPDATE SET
                    sysDescr=excluded.sysDescr,
                    sysName=excluded.sysName,
                    sysUpTime=excluded.sysUpTime,
                    sysLocation=excluded.sysLocation,
                    lastUpdated=excluded.lastUpdated
                    """, (ip, port, str(sysDescr or "N/A"), str(sysName or "N/A"), 
                    str(sysUpTime or "N/A"), str(sysLocation or "N/A"), timestamp))
            conn.commit()
        finally:
            conn.close()
        self.update_signal.emit()


# GUI Host Information Manager
class HostInfoManager(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.setWindowTitle("SNMP Host Information Manager")
        self.setGeometry(100, 100, 1000, 600)

        # Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "IP", "Port", "Description", "Name", "UpTime", "Location"])
        layout.addWidget(self.table)


        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_host_data)
        button_layout.addWidget(self.refresh_button)


        self.delete_button = QPushButton("Delete Selected Host")
        self.delete_button.clicked.connect(self.delete_selected_host)
        button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)

        # SNMP Thread
        self.snmp_thread = SNMPQueryThread(self.db_manager.db_name)
        self.snmp_thread.update_signal.connect(self.load_host_data)

        # Auto Refresh Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.snmp_thread.start)
        self.timer.start(10000)

        self.load_host_data()

    def load_host_data(self):
        self.table.setRowCount(0)
        for row, host in enumerate(self.db_manager.get_all_hosts()):
            self.table.insertRow(row)
            for col, value in enumerate(host):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

    def save_custom_data(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Warning", "Please select a row to save custom data.")
            return

        host_id = self.table.item(selected_row, 0).text()  # 获取 ID
        custom_data = self.custom_input.text()  # 获取输入的数据
        if not custom_data.strip():
            QMessageBox.warning(self, "Warning", "Custom data cannot be empty.")
            return

        # 更新数据库
        self.db_manager.update_custom_data(int(host_id), custom_data)
        QMessageBox.information(self, "Success", "Custom data saved successfully.")
        self.load_host_data()

    def delete_selected_host(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Warning", "Please select a row to delete.")
            return

        host_id = self.table.item(selected_row, 0).text()
        self.db_manager.delete_host(int(host_id))
        QMessageBox.information(self, "Info", "Selected host deleted successfully.")
        self.load_host_data()



if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    db_manager = DatabaseManager()
    window = HostInfoManager(db_manager)
    window.show()
    sys.exit(app.exec_())
