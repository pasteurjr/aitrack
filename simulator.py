import socket
import time
import random
from threading import Thread
import hashlib
from server.routes_loader import load_routes

N_VEHICLES = 10
SEND_INTERVAL = 5
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 9000

ROUTES = load_routes(min_points=30)
STEPS_PER_SEGMENT = 1  # já densificado pelo loader

def get_maxtrack_packet(lat, lon, speed, heading, ignition, battery_voltage):
    now = time.strftime("%d%m%y;%H%M%S", time.gmtime())
    return f">REV01;{now};A;{lat:.5f};{lon:.5f};{speed:.1f};{int(heading)};{ignition};{battery_voltage:.2f};0;3<".encode('ascii')

def get_suntech_packet(device_id, lat, lon, speed, heading, ignition, battery_voltage):
    now_date = time.strftime("%Y%m%d", time.gmtime())
    now_time = time.strftime("%H:%M:%S", time.gmtime())
    return f"ST310U;{device_id};01;{now_date};{now_time};{lat:.5f};{lon:.5f};{speed:.1f};{heading:.1f};{ignition};1;{battery_voltage:.2f};3.7;0;1;BR;724;31;1234;5678".encode('ascii')

def get_queclink_packet(device_id, lat, lon, speed, heading, ignition, battery_voltage, altitude):
    now_date = time.strftime("%d%m%y", time.gmtime())
    now_time = time.strftime("%H%M%S", time.gmtime())
    return f"+RESP:GTRIC,{device_id},1,1,0,7,{now_date},{now_time},{lat:.5f},{lon:.5f},{speed:.1f},{int(heading)},{ignition},100,{battery_voltage:.2f},98765,1234,5678,724,31,1,{altitude:.1f}\r\n".encode('ascii')

class Vehicle(Thread):
    def __init__(self, device_id, protocol, route_coords):
        super().__init__()
        self.device_id = device_id
        self.protocol = protocol
        self.route = route_coords
        # Distribui veículos ao longo da rota: offset inicial estável baseado no device_id (hash md5)
        h = int(hashlib.md5(self.device_id.encode('utf-8')).hexdigest(), 16)
        self.current_point_index = (h % len(self.route))
        self.daemon = True

    def run(self):
        while True:
            try:
                point = self.route[self.current_point_index]
                self.current_point_index = (self.current_point_index + 1) % len(self.route)

                lat, lon = point  # sem jitter: usa exatamente o ponto da rota

                speed = random.uniform(20, 60)
                heading = random.uniform(0, 359)
                ignition = 1
                battery_voltage = random.uniform(12.0, 14.5)

                if self.protocol == 'maxtrack':
                    packet = get_maxtrack_packet(lat, lon, speed, heading, ignition, battery_voltage)
                elif self.protocol == 'suntech':
                    packet = get_suntech_packet(self.device_id, lat, lon, speed, heading, ignition, battery_voltage)
                else:  # queclink
                    altitude = random.uniform(700, 850)
                    packet = get_queclink_packet(self.device_id, lat, lon, speed, heading, ignition, battery_voltage, altitude)

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((SERVER_HOST, SERVER_PORT))
                    s.sendall(packet)

                print(f"Enviado pacote {self.protocol.upper()} do veículo {self.device_id} (Vel: {speed:.1f} km/h)")

            except Exception as e:
                print(f"[Simulador ERRO] Veículo {self.device_id}: {e}")
            
            time.sleep(SEND_INTERVAL)

if __name__ == "__main__":
    route_names = list(ROUTES.keys())
    for i in range(N_VEHICLES):
        # Desativar Maxtrack no simulador para evitar pacotes sem ID quebrarem o fluxo
        protocol = ['suntech', 'queclink'][i % 2]
        device_id = f"SIM-{1000 + i}"
        route_coords = ROUTES[route_names[i % len(route_names)]]
        Vehicle(device_id, protocol, route_coords).start()
        time.sleep(0.1)
    
    print(f"{N_VEHICLES} veículos simulados iniciados, seguindo rotas realistas.")
    print("Pressione Ctrl+C para parar.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSimulador parado.")
