#!/usr/bin/env python3
"""
Dirijabem Continuous Simulator
Simula múltiplos motoristas gerando viagens sintéticas continuamente em tempo real
Similar ao simulator.py mas para o banco dirijabem
"""

import time
import random
import mysql.connector
from datetime import datetime, timedelta
from threading import Thread, Lock
from dirijabem_simulator import (
    DriverProfile,
    SyntheticRouteGenerator,
    BehavioralMetricsCalculator,
    DB_CONFIG
)


class VirtualDriver:
    """Representa um motorista virtual gerando viagens sintéticas continuamente"""

    def __init__(self, driver_id, codusu, profile=None):
        self.driver_id = driver_id
        self.codusu = codusu
        self.profile = profile or DriverProfile.get_random_profile()

        # Estado da viagem atual
        self.current_trip = None
        self.current_codvia = None
        self.current_points = []
        self.current_point_index = 0
        self.trip_start_time = None

        # Geradores
        self.route_generator = SyntheticRouteGenerator()
        self.metrics_calculator = BehavioralMetricsCalculator()

        # Database
        self.db_pool = None

        print(f"[DRIVER-{driver_id}] Criado | Perfil: {DriverProfile.PROFILES[self.profile]['name']} | CODUSU: {codusu}")

    def _get_db_connection(self):
        """Get database connection from pool"""
        if self.db_pool is None:
            self.db_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)
        return self.db_pool.get_connection()

    def start_new_trip(self):
        """Inicia uma nova viagem sintética"""
        # Duração aleatória entre 5-20 minutos
        duration = random.randint(5, 20)

        # Gerar rota sintética
        self.current_points = self.route_generator.generate_route(
            duration_minutes=duration,
            driver_profile=self.profile
        )

        # Injetar eventos comportamentais
        self.current_points = self.route_generator.inject_realistic_events(
            self.current_points,
            driver_profile=self.profile
        )

        # Calcular métricas
        metrics = self.metrics_calculator.calculate_metrics(self.current_points)

        # Criar registro de viagem no banco
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO viagem (CODUSU, DATAHORINI, DATAHORFIN, PLACA)
                VALUES (%s, NOW(), '1900-01-01 00:00:00', %s)
            """, (self.codusu, f'SIM-D{self.driver_id}'))

            self.current_codvia = cursor.lastrowid
            conn.commit()

            # Armazenar métricas para uso posterior
            self.current_trip = {
                'codvia': self.current_codvia,
                'metrics': metrics,
                'duration': duration,
                'total_points': len(self.current_points)
            }

            self.current_point_index = 0
            self.trip_start_time = datetime.now()

            profile_name = DriverProfile.PROFILES[self.profile]['name']
            print(f"[DRIVER-{self.driver_id}] 🆕 Nova viagem CODVIA={self.current_codvia} | "
                  f"Perfil: {profile_name} | Duração: {duration}min | "
                  f"Score: {metrics['SCORE']:.1f}")

        except Exception as e:
            print(f"[DRIVER-{self.driver_id}] ❌ Erro ao criar viagem: {e}")
            conn.rollback()
            self.current_codvia = None
        finally:
            cursor.close()
            conn.close()

    def emit_next_point(self):
        """Emite próximo ponto GPS da viagem atual"""
        if not self.current_trip or self.current_point_index >= len(self.current_points):
            return False

        point = self.current_points[self.current_point_index]

        # Salvar ponto no banco
        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO localizacaodados (CODVIA, DATAHORA, coords, VELATU, ACELLINATU, VARDIRATU)
                VALUES (%s, NOW(), ST_PointFromText('POINT(%s %s)'), %s, %s, %s)
            """, (
                self.current_codvia,
                point['coords'][0],  # lon
                point['coords'][1],  # lat
                point['VELATU'],
                point['ACELLINATU'],
                point['VARDIRATU']
            ))

            conn.commit()

            # Debug a cada 60 pontos (1 minuto)
            if self.current_point_index % 60 == 0:
                elapsed_min = self.current_point_index // 60
                total_min = len(self.current_points) // 60
                progress = (self.current_point_index / len(self.current_points)) * 100
                print(f"[DRIVER-{self.driver_id}] 📍 CODVIA={self.current_codvia} | "
                      f"{elapsed_min}/{total_min}min | {progress:.0f}% | "
                      f"Vel: {point['VELATU']:.1f} km/h")

        except Exception as e:
            print(f"[DRIVER-{self.driver_id}] ❌ Erro ao salvar ponto: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

        self.current_point_index += 1
        return True

    def finalize_trip(self):
        """Finaliza viagem atual calculando métricas finais"""
        if not self.current_trip:
            return

        metrics = self.current_trip['metrics']

        conn = self._get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE viagem SET
                    DATAHORFIN = NOW(),
                    OST = %s, OSA = %s, OSP = %s,
                    SAM = %s, SAA = %s,
                    BRP = %s, BRM = %s, BRA = %s,
                    GAM = %s, GAA = %s, GAP = %s, GAN = %s,
                    SCORE = %s
                WHERE CODVIA = %s
            """, (
                metrics['OST'], metrics['OSA'], metrics['OSP'],
                metrics['SAM'], metrics['SAA'],
                metrics['BRP'], metrics['BRM'], metrics['BRA'],
                metrics['GAM'], metrics['GAA'], metrics['GAP'], metrics['GAN'],
                metrics['SCORE'],
                self.current_codvia
            ))

            conn.commit()

            profile_name = DriverProfile.PROFILES[self.profile]['name']
            print(f"[DRIVER-{self.driver_id}] ✅ Viagem CODVIA={self.current_codvia} COMPLETA | "
                  f"Perfil: {profile_name} | Score: {metrics['SCORE']:.1f} | "
                  f"Pontos: {self.current_trip['total_points']}")

        except Exception as e:
            print(f"[DRIVER-{self.driver_id}] ❌ Erro ao finalizar viagem: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

        # Limpar estado
        self.current_trip = None
        self.current_codvia = None
        self.current_points = []
        self.current_point_index = 0

    def is_in_trip(self):
        """Verifica se está em uma viagem ativa"""
        return self.current_trip is not None

    def has_more_points(self):
        """Verifica se há mais pontos para emitir"""
        return self.current_point_index < len(self.current_points)


class DirijabemContinuousSimulator:
    """Simulador contínuo de múltiplos motoristas"""

    # Usuários reais do banco dirijabem (existem na tabela usuario)
    REAL_USERS = [1, 614, 17, 411, 21, 239, 617, 608, 36, 70]

    def __init__(self, num_drivers=10, speed_multiplier=1):
        """
        Args:
            num_drivers: Número de motoristas virtuais simultâneos
            speed_multiplier: Velocidade de simulação (1=tempo real, 10=10x mais rápido)
        """
        self.num_drivers = num_drivers
        self.speed_multiplier = speed_multiplier
        self.drivers = []
        self.running = False
        self.lock = Lock()

        # Criar motoristas virtuais
        print(f"\n{'='*70}")
        print(f"🚗 SIMULADOR CONTÍNUO DIRIJABEM")
        print(f"{'='*70}")
        print(f"Motoristas: {num_drivers}")
        print(f"Velocidade: {speed_multiplier}x")
        print(f"{'='*70}\n")

        for i in range(num_drivers):
            # Usar CODUSU de usuários REAIS que existem no banco
            codusu = self.REAL_USERS[i % len(self.REAL_USERS)]

            # Perfil aleatório com distribuição realista
            profile = DriverProfile.get_random_profile()

            driver = VirtualDriver(
                driver_id=i + 1,
                codusu=codusu,
                profile=profile
            )

            self.drivers.append(driver)

        print(f"\n✅ {num_drivers} motoristas virtuais criados!\n")

    def run(self):
        """Loop principal do simulador"""
        self.running = True

        print(f"{'='*70}")
        print(f"🏁 INICIANDO SIMULAÇÃO CONTÍNUA")
        print(f"{'='*70}\n")
        print("Pressione Ctrl+C para parar\n")

        try:
            while self.running:
                start_time = time.time()

                with self.lock:
                    for driver in self.drivers:
                        # Se não está em viagem, iniciar nova
                        if not driver.is_in_trip():
                            driver.start_new_trip()

                        # Se está em viagem e tem mais pontos, emitir próximo
                        elif driver.has_more_points():
                            driver.emit_next_point()

                        # Se acabou os pontos, finalizar viagem
                        else:
                            driver.finalize_trip()

                # Controle de velocidade (1 ponto por segundo no tempo real)
                elapsed = time.time() - start_time
                sleep_time = max(0, (1.0 / self.speed_multiplier) - elapsed)
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            print(f"\n\n{'='*70}")
            print(f"⏹️  PARANDO SIMULADOR...")
            print(f"{'='*70}\n")
            self.stop()

    def stop(self):
        """Para o simulador"""
        self.running = False

        # Finalizar todas as viagens em andamento
        with self.lock:
            for driver in self.drivers:
                if driver.is_in_trip():
                    print(f"[DRIVER-{driver.driver_id}] Finalizando viagem em andamento...")
                    driver.finalize_trip()

        print(f"\n✅ Simulador parado!\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Simulador contínuo de viagens sintéticas para Dirijabem'
    )
    parser.add_argument('--drivers', type=int, default=10,
                       help='Número de motoristas virtuais simultâneos (padrão: 10)')
    parser.add_argument('--speed', type=int, default=1,
                       help='Multiplicador de velocidade (1=tempo real, 10=10x mais rápido)')

    args = parser.parse_args()

    # Criar e iniciar simulador
    simulator = DirijabemContinuousSimulator(
        num_drivers=args.drivers,
        speed_multiplier=args.speed
    )

    simulator.run()


if __name__ == "__main__":
    main()
