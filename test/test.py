import time
import sqlite3
from pysnmp.hlapi import *
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem,
                             QPushButton, QMessageBox, QHBoxLayout, QLineEdit, QDialog, QLabel)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal


# SNMP Query Function
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
    except Exception:
        return None


# Database Manager
class DatabaseManager:
    def __init__(self, db_name="hosts.db"):
        self.db_name = db_name
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

    def add_host(self, ip, port, sysDescr="", sysName="", sysUpTime="", sysLocation=""):
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            query = """
            INSERT INTO hosts (ip, port, sysDescr, sysName, sysUpTime, sysLocation, lastUpdated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            self.conn.execute(query, (ip, port, sysDescr, sysName, sysUpTime, sysLocation, timestamp))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError("The host with this IP and Port already exists.")

    def update_host(self, host_id, ip, port, sysDescr, sysName, sysUpTime, sysLocation):
        query = """
        UPDATE hosts
        SET ip=?, port=?, sysDescr=?, sysName=?, sysUpTime=?, sysLocation=?
        WHERE id=?
        """
        self.conn.execute(query, (ip, port, sysDescr, sysName, sysUpTime, sysLocation, host_id))
        self.conn.commit()

    def delete_host_by_ip_port(self, ip, port):
        query = "DELETE FROM hosts WHERE ip=? AND port=?"
        self.conn.execute(query, (ip, port))
        self.conn.commit()

    def get_all_hosts(self):
        cursor = self.conn.execute("SELECT * FROM hosts")
        return cursor.fetchall()


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


# Host Editor Dialog
class HostEditorDialog(QDialog):
    def __init__(self, parent=None, host_data=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Host" if host_data else "Add Host")
        self.setGeometry(200, 200, 400, 300)

        layout = QVBoxLayout(self)

        self.host_data = host_data

        self.ip_input = QLineEdit(self)
        self.ip_input.setPlaceholderText("IP Address")
        layout.addWidget(QLabel("IP Address:"))
        layout.addWidget(self.ip_input)

        self.port_input = QLineEdit(self)
        self.port_input.setPlaceholderText("Port")
        layout.addWidget(QLabel("Port:"))
        layout.addWidget(self.port_input)

        self.sysDescr_input = QLineEdit(self)
        self.sysDescr_input.setPlaceholderText("System Description")
        layout.addWidget(QLabel("System Description:"))
        layout.addWidget(self.sysDescr_input)

        self.sysName_input = QLineEdit(self)
        self.sysName_input.setPlaceholderText("System Name")
        layout.addWidget(QLabel("System Name:"))
        layout.addWidget(self.sysName_input)

        self.sysUpTime_input = QLineEdit(self)
        self.sysUpTime_input.setPlaceholderText("System UpTime")
        layout.addWidget(QLabel("System UpTime:"))
        layout.addWidget(self.sysUpTime_input)

        self.sysLocation_input = QLineEdit(self)
        self.sysLocation_input.setPlaceholderText("System Location")
        layout.addWidget(QLabel("System Location:"))
        layout.addWidget(self.sysLocation_input)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_data)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        if host_data:
            self.ip_input.setText(host_data.get("ip", ""))
            self.port_input.setText(str(host_data.get("port", "")))
            self.sysDescr_input.setText(host_data.get("sysDescr", ""))
            self.sysName_input.setText(host_data.get("sysName", ""))
            self.sysUpTime_input.setText(host_data.get("sysUpTime", ""))
            self.sysLocation_input.setText(host_data.get("sysLocation", ""))

    def save_data(self):
        try:
            self.data = {
                "ip": self.ip_input.text(),
                "port": int(self.port_input.text()),
                "sysDescr": self.sysDescr_input.text(),
                "sysName": self.sysName_input.text(),
                "sysUpTime": self.sysUpTime_input.text(),
                "sysLocation": self.sysLocation_input.text(),
            }
            self.accept()
        except ValueError:
            QMessageBox.warning(self, "Error", "Port must be a valid number.")


# GUI Host Information Manager
class HostInfoManager(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.setWindowTitle("SNMP Host Information Manager")
        self.setGeometry(100, 100, 1000, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "IP", "Port", "Description", "Name", "UpTime", "Location", "Custom Data"])
        layout.addWidget(self.table)

        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Enter custom data for the selected row")
        layout.addWidget(self.custom_input)

        button_layout = QHBoxLayout()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_host_data)
        button_layout.addWidget(self.refresh_button)

        self.save_custom_button = QPushButton("Save Custom Data")
        self.save_custom_button.clicked.connect(self.save_custom_data)
        button_layout.addWidget(self.save_custom_button)

        self.delete_button = QPushButton("Delete Selected Host")
        self.delete_button.clicked.connect(self.delete_selected_host)
        button_layout.addWidget(self.delete_button)

        self.add_button = QPushButton("Add Host")
        self.add_button.clicked.connect(self.add_host)
        button_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit Selected Host")
        self.edit_button.clicked.connect(self.edit_host)
        button_layout.addWidget(self.edit_button)

        layout.addLayout(button_layout)

        self.load_host_data()

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_snmp_data)
        self.timer.start(300000)

    def load_host_data(self):
        self.table.setRowCount(0)
        for row_data in self.db_manager.get_all_hosts():
            row_index = self.table.rowCount()
            self.table.insertRow(row_index)
            for col, data in enumerate(row_data):
                self.table.setItem(row_index, col, QTableWidgetItem(str(data)))

    def save_custom_data(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Warning", "Please select a row to update custom data.")
            return

        host_id = self.table.item(selected_row, 0).text()
        custom_data = self.custom_input.text()
        query = "UPDATE hosts SET customData=? WHERE id=?"
        self.db_manager.conn.execute(query, (custom_data, host_id))
        self.db_manager.conn.commit()
        QMessageBox.information(self, "Success", "Custom data saved successfully.")
        self.load_host_data()

    def delete_selected_host(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Warning", "Please select a row to delete.")
            return

        ip = self.table.item(selected_row, 1).text()
        port = self.table.item(selected_row, 2).text()
        self.db_manager.delete_host_by_ip_port(ip, int(port))
        QMessageBox.information(self, "Success", "Host deleted successfully.")
        self.load_host_data()

    def add_host(self):
        dialog = HostEditorDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.data
            try:
                self.db_manager.add_host(data["ip"], data["port"], data["sysDescr"],
                                         data["sysName"], data["sysUpTime"], data["sysLocation"])
                QMessageBox.information(self, "Success", "Host added successfully.")
                self.load_host_data()
            except ValueError as e:
                QMessageBox.warning(self, "Error", str(e))

    def edit_host(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Warning", "Please select a row to edit.")
            return

        host_id = self.table.item(selected_row, 0).text()
        ip = self.table.item(selected_row, 1).text()
        port = self.table.item(selected_row, 2).text()
        sysDescr = self.table.item(selected_row, 3).text()
        sysName = self.table.item(selected_row, 4).text()
        sysUpTime = self.table.item(selected_row, 5).text()
        sysLocation = self.table.item(selected_row, 6).text()

        dialog = HostEditorDialog(self, host_data={
            "id": host_id,
            "ip": ip,
            "port": port,
            "sysDescr": sysDescr,
            "sysName": sysName,
            "sysUpTime": sysUpTime,
            "sysLocation": sysLocation,
        })

        if dialog.exec_() == QDialog.Accepted:
            data = dialog.data
            self.db_manager.update_host(host_id, data["ip"], data["port"], data["sysDescr"],
                                        data["sysName"], data["sysUpTime"], data["sysLocation"])
            QMessageBox.information(self, "Success", "Host updated successfully.")
            self.load_host_data()

    def refresh_snmp_data(self):
        query_thread = SNMPQueryThread(self.db_manager.db_name)
        query_thread.update_signal.connect(self.load_host_data)
        query_thread.start()


# Main Application
def main():
    app = QApplication([])
    db_manager = DatabaseManager()
    manager = HostInfoManager(db_manager)
    manager.show()
    app.exec_()


if __name__ == "__main__":
    main()
