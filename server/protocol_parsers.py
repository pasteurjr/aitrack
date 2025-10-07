from datetime import datetime

PREFIX_SEPARATOR = '|'

def parse_data(raw_data):
    """Identifica e decodifica os dados brutos."""
    try:
        data_str = raw_data.decode('ascii').strip()
        if not data_str:
            return None

        # Suporte opcional para prefixo "device_id|" em pacotes Maxtrack do simulador
        if PREFIX_SEPARATOR in data_str:
            maybe_id, rest = data_str.split(PREFIX_SEPARATOR, 1)
            if rest.startswith('>REV') and maybe_id:
                parsed = parse_maxtrack(rest)
                if parsed:
                    parsed['device_id'] = maybe_id
                return parsed

        if data_str.startswith('>REV'):
            return parse_maxtrack(data_str)
        elif data_str.startswith('ST'):
            return parse_suntech(data_str)
        elif data_str.startswith('+RESP:GTRIC'):
            return parse_queclink(data_str)
        else:
            print(f"AVISO: Pacote em formato desconhecido: {data_str}")
            return None

    except Exception as e:
        print(f"Erro em parse_data: {e}")
        return None

def parse_maxtrack(data_str):
    parts = data_str.split(';')
    if len(parts) < 10:
        return None
    try:
        timestamp = datetime.strptime(f"{parts[1]}{parts[2]}", "%d%m%y%H%M%S")
        return {
            'protocol': 'maxtrack',
            'device_id': None, # Pacotes Maxtrack são anônimos
            'timestamp': timestamp.isoformat(),
            'gps_status': parts[3] == 'A',
            'latitude': float(parts[4]),
            'longitude': float(parts[5]),
            'speed': float(parts[6]),
            'heading': int(parts[7]),
            'ignition': parts[8] == '1',
            'battery_voltage': float(parts[9]),
            'panic': False,
            'altitude': None
        }
    except (ValueError, IndexError):
        return None

def parse_suntech(data_str):
    parts = data_str.split(';')
    if len(parts) < 13:
        return None
    try:
        timestamp = datetime.strptime(f"{parts[3]}{parts[4]}", "%Y%m%d%H:%M:%S")
        return {
            'protocol': 'suntech',
            'device_id': parts[1],
            'timestamp': timestamp.isoformat(),
            'gps_status': True,
            'latitude': float(parts[5]),
            'longitude': float(parts[6]),
            'speed': float(parts[7]),
            'heading': float(parts[8]),
            'ignition': parts[9] == '1',
            'battery_voltage': float(parts[11]),
            'panic': False,
            'altitude': None
        }
    except (ValueError, IndexError):
        return None

def parse_queclink(data_str):
    parts = data_str.split(',')
    if len(parts) < 15:
        return None
    try:
        timestamp = datetime.strptime(f"{parts[6]}{parts[7]}", "%d%m%y%H%M%S")
        return {
            'protocol': 'queclink',
            'device_id': parts[1],
            'timestamp': timestamp.isoformat(),
            'gps_status': True,
            'latitude': float(parts[8]),
            'longitude': float(parts[9]),
            'speed': float(parts[10]),
            'heading': float(parts[11]),
            'ignition': parts[12] == '1',
            'battery_voltage': float(parts[14]),
            'panic': False,
            'altitude': float(parts[-1])
        }
    except (ValueError, IndexError):
        return None
