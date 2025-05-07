import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import os
import sys
import traceback
import subprocess
import threading
import ctypes

def es_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def ejecutar_como_admin():
    if not es_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, ' '.join(sys.argv), None, 1)
        sys.exit()

class AppServerSvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "TrackingNS"
    _svc_display_name_ = "App Tracking NS"
    _svc_description_ = "Servicio de seguimiento de pedidos en NS"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.process = None

    def SvcStop(self):
        servicemanager.LogInfoMsg("Stopping service...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        if self.process:
            self.process.terminate()
            self.process.wait()
        servicemanager.LogInfoMsg("Service stopped.")

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def main(self):
        try:
            # Instalar dependencias primero
            install_process = subprocess.run(
                ['C:\\Program Files\\Python311\\python.exe', '-m', 'pip', 'install', 'flask', 'ldap3', 'pyodbc', 'flask-talisman', 'uuid'],
                capture_output=True,
                text=True
            )
            if install_process.returncode != 0:
                servicemanager.LogErrorMsg(f"Error installing dependencies: {install_process.stderr}")
                return

            # Ejecutar el script run.py
            self.process = subprocess.Popen(
                ['C:\\Program Files\\Python311\\python.exe', 'c:\\Users\\jarojas\\Documents\\TRACKING17032025\\run.py'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            stdout, stderr = self.process.communicate()
            servicemanager.LogInfoMsg(f"Output: {stdout}")
            if stderr:
                servicemanager.LogErrorMsg(f"Error: {stderr}")
        except Exception as e:
            servicemanager.LogErrorMsg(f"Exception: {str(e)}")
            traceback.print_exc(file=sys.stdout)

if __name__ == '__main__':
    ejecutar_como_admin()
    win32serviceutil.HandleCommandLine(AppServerSvc)