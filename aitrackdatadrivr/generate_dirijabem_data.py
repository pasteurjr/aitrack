#!/usr/bin/env python3
"""
Script CLI para gerar dados sintéticos REALISTAS em massa no banco Dirijabem
"""

import argparse
import time
import sys
import os

# Adicionar diretório pai ao path para importar dirijabem_simulator
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dirijabem_simulator import DirijabemReplayManager, DriverProfile


def main():
    parser = argparse.ArgumentParser(
        description='Gera dados sintéticos realistas para Dirijabem',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Gerar 50 viagens com perfis aleatórios
  python generate_dirijabem_data.py --users 10 --trips-per-user 5

  # Gerar apenas motoristas ruins/agressivos (para testar alertas)
  python generate_dirijabem_data.py --users 5 --trips-per-user 10 --profile poor,aggressive

  # Gerar viagens curtas e rápidas
  python generate_dirijabem_data.py --users 20 --trips 5 --duration-min 3 --duration-max 10 --fast

  # Distribuição realista (15%% excellent, 20%% good, 30%% average, 25%% poor, 10%% aggressive)
  python generate_dirijabem_data.py --users 20 --trips 5 --realistic
        """
    )

    parser.add_argument('--users', type=int, default=10, help='Número de usuários')
    parser.add_argument('--trips-per-user', '--trips', type=int, default=5,
                       help='Viagens por usuário')
    parser.add_argument('--duration-min', type=int, default=5,
                       help='Duração mínima (minutos)')
    parser.add_argument('--duration-max', type=int, default=20,
                       help='Duração máxima (minutos)')
    parser.add_argument('--profile', type=str, default=None,
                       help='Perfil(s) de motorista: excellent, good, average, poor, aggressive '
                            '(separar por vírgula para múltiplos)')
    parser.add_argument('--realistic', action='store_true',
                       help='Usar distribuição realista de perfis')
    parser.add_argument('--fast', action='store_true',
                       help='Modo rápido (não aguarda conclusão em tempo real)')

    args = parser.parse_args()

    # Processar perfis
    profiles = None
    if args.profile:
        profiles = [p.strip() for p in args.profile.split(',')]
        # Validar perfis
        valid_profiles = list(DriverProfile.PROFILES.keys())
        for p in profiles:
            if p not in valid_profiles:
                print(f"❌ Perfil inválido: {p}")
                print(f"   Perfis válidos: {', '.join(valid_profiles)}")
                return

    manager = DirijabemReplayManager()

    total_trips = args.users * args.trips_per_user
    print(f"\n{'='*70}")
    print(f"🚗 GERADOR DE DADOS SINTÉTICOS DIRIJABEM")
    print(f"{'='*70}")
    print(f"Usuários: {args.users}")
    print(f"Viagens por usuário: {args.trips_per_user}")
    print(f"Total de viagens: {total_trips}")
    print(f"Duração: {args.duration_min}-{args.duration_max} minutos")
    if profiles:
        print(f"Perfis: {', '.join(profiles)}")
    elif args.realistic:
        print(f"Perfis: Distribuição realista")
    else:
        print(f"Perfis: Aleatório")
    print(f"{'='*70}\n")

    # Estatísticas
    stats = {
        'excellent': 0,
        'good': 0,
        'average': 0,
        'poor': 0,
        'aggressive': 0
    }

    # Gerar viagens
    for codusu in range(1, args.users + 1):
        print(f"\n👤 Usuário {codusu}:")

        for trip_num in range(args.trips_per_user):
            # Escolher perfil
            if profiles:
                profile = profiles[trip_num % len(profiles)]
            elif args.realistic:
                profile = DriverProfile.get_random_profile()
            else:
                import random
                profile = random.choice(list(DriverProfile.PROFILES.keys()))

            # Gerar viagem
            codvia, actual_profile = manager.start_synthetic_trip(codusu, profile)

            if codvia:
                stats[actual_profile] += 1

                profile_emoji = {
                    'excellent': '🌟',
                    'good': '👍',
                    'average': '😐',
                    'poor': '⚠️',
                    'aggressive': '🔥'
                }

                print(f"  {profile_emoji[actual_profile]} Viagem {trip_num+1}: "
                      f"CODVIA={codvia} | Perfil: {DriverProfile.PROFILES[actual_profile]['name']}")
            else:
                print(f"  ❌ Viagem {trip_num+1}: Erro ao gerar")

            # Aguardar conclusão (se não for fast mode)
            if not args.fast:
                time.sleep(0.5)  # Simula processamento

    # Resumo final
    print(f"\n{'='*70}")
    print(f"✅ GERAÇÃO CONCLUÍDA")
    print(f"{'='*70}")
    print(f"Total de viagens geradas: {total_trips}")
    print(f"\nDistribuição de perfis:")
    for profile, count in stats.items():
        if total_trips > 0:
            percentage = (count / total_trips) * 100
            profile_name = DriverProfile.PROFILES[profile]['name']
            bar = '█' * int(percentage / 2)
            print(f"  {profile_name:12} ({profile:10}): {count:3} ({percentage:5.1f}%) {bar}")

    print(f"\n💾 Dados salvos no banco 'dirijabem'")
    print(f"📊 As viagens estão sendo emitidas em tempo real pelo replay manager")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
