import time
from pysnmp.hlapi import *
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure




def snmp_get(ip, oid, port=161):
    """
    Fetches SNMP data for a given OID from the target host.
    """
    try:
        iterator = getCmd(SnmpEngine(),
                          CommunityData('public', mpModel=0),
                          UdpTransportTarget((ip, port)),
                          ContextData(),
                          ObjectType(ObjectIdentity(oid)))
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        if errorIndication:
            print(f"SNMP Error: {errorIndication}")
            return None
        elif errorStatus:
            print(f"{errorStatus.prettyPrint()} at {varBinds[int(errorIndex) - 1] if errorIndex else ''}")
            return None
        else:
            for varBind in varBinds:
                return varBind[1]
    except Exception as e:
        print(f"Exception while querying SNMP: {e}")
        return None


def get_supported_interfaces(ip, port=161):
    """
    Query supported interfaces from the device.
    """
    base_oid = '1.3.6.1.2.1.2.2.1.1'  # ifIndex OID
    interfaces = []
    try:
        iterator = nextCmd(SnmpEngine(),
                           CommunityData('public', mpModel=0),
                           UdpTransportTarget((ip, port)),
                           ContextData(),
                           ObjectType(ObjectIdentity(base_oid)),
                           lexicographicMode=False)
        for errorIndication, errorStatus, errorIndex, varBinds in iterator:
            if errorIndication:
                print(f"SNMP Error: {errorIndication}")
                break
            elif errorStatus:
                print(f"{errorStatus.prettyPrint()} at {varBinds[int(errorIndex) - 1] if errorIndex else ''}")
                break
            else:
                for varBind in varBinds:
                    interfaces.append(int(varBind[1]))
    except Exception as e:
        print(f"Exception while fetching interfaces: {e}")
    return interfaces


# PyQt + Matplotlib Visualization
class NetworkTrafficWindow(QMainWindow):
    def __init__(self, target, port):
        super().__init__()
        self.setWindowTitle("Network Traffic Visualization")
        self.setGeometry(100, 100, 800, 600)

        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout for the main widget
        layout = QVBoxLayout(self.central_widget)

        # Status Label
        self.status_label = QLabel(f"Monitoring: {target}:{port}")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: green;")
        layout.addWidget(self.status_label)

        # Matplotlib Figure
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # SNMP Data
        self.target_ip = target
        self.target_port = port
        self.interfaces = get_supported_interfaces(self.target_ip, self.target_port)
        if not self.interfaces:
            self.status_label.setText("No interfaces found. Check SNMP service or OID support.")
            return

        self.status_label.setText(f"Available Interfaces: {', '.join(map(str, self.interfaces))}")
        self.data = {index: {"Time": [], "Received": [], "Sent": []} for index in self.interfaces}
        self.rx_oid_base = '1.3.6.1.2.1.2.2.1.10'  # Base OID for ifInOctets
        self.tx_oid_base = '1.3.6.1.2.1.2.2.1.16'  # Base OID for ifOutOctets

        # Timer for updating data
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(10000)  # Update every 10 second

    def update_data(self):
        timestamp = time.strftime('%H:%M:%S')
        for index in self.interfaces:
            rx_oid = f"{self.rx_oid_base}.{index}"
            tx_oid = f"{self.tx_oid_base}.{index}"
            rx_value = snmp_get(self.target_ip, rx_oid, self.target_port)
            tx_value = snmp_get(self.target_ip, tx_oid, self.target_port)

            if rx_value is not None and tx_value is not None:
                self.data[index]["Time"].append(timestamp)
                self.data[index]["Received"].append(int(rx_value))
                self.data[index]["Sent"].append(int(tx_value))

                if len(self.data[index]["Time"]) > 10:
                    self.data[index]["Time"].pop(0)
                    self.data[index]["Received"].pop(0)
                    self.data[index]["Sent"].pop(0)

                print(f"Interface {index} - Time: {timestamp}, Received: {rx_value}, Sent: {tx_value}")

        self.update_plot()

    def update_plot(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        for index in self.interfaces:
            if self.data[index]["Time"]:
                ax.plot(
                    self.data[index]["Time"],
                    self.data[index]["Received"],
                    label=f"Interface {index} - Received",
                    marker='o',
                    linestyle='-',
                    linewidth=2,
                    color='blue'
                )
                ax.plot(
                    self.data[index]["Time"],
                    self.data[index]["Sent"],
                    label=f"Interface {index} - Sent",
                    marker='x',
                    linestyle='--',
                    linewidth=2,
                    color='green'
                )
        ax.set_title("Network Traffic", fontsize=16, fontweight="bold")
        ax.set_xlabel("Time", fontsize=12)
        ax.set_ylabel("Packets", fontsize=12)
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend(fontsize=10, loc="upper left")
        self.canvas.draw()


def task_3():
    """
    Fetch and display detailed host information for a range of IPs and ports.
    """
    oids = {
        "sysDescr": '1.3.6.1.2.1.1.1.0',
        "sysObjectID": '1.3.6.1.2.1.1.2.0',
        "sysUpTime": '1.3.6.1.2.1.1.3.0',
        "sysContact": '1.3.6.1.2.1.1.4.0',
        "sysName": '1.3.6.1.2.1.1.5.0',
        "sysLocation": '1.3.6.1.2.1.1.6.0',
    }

    for port in range(16101, 16160):  # Loop through ports 16101 to 16110
        ip = "127.0.0.1"
        print(f"\nQuerying device at {ip}:{port}")
        device_info = {}
        for key, oid in oids.items():
            value = snmp_get(ip, oid, port)
            device_info[key] = value

        # Print device information
        print("\nDevice Information:")
        for key, value in device_info.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    import sys
    print("1. Traverse Host Information")
    print("2. Network Data Analysis and Visualization")
    choice = input("Choose an option (1/2): ").strip()
    if choice == '1':
        task_3()
    elif choice == '2':
        target_ip = "127.0.0.1"
        target_port = int(input("Enter port number (e.g., 16101): ").strip())
        app = QApplication(sys.argv)
        window = NetworkTrafficWindow(target_ip, target_port)
        window.show()
        sys.exit(app.exec_())
    else:
        print("Invalid choice.")
