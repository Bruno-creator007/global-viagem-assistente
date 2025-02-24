from travel_api import TravelAPI
from datetime import datetime, timedelta

def test_flights():
    api = TravelAPI()
    
    # Busca voos de São Paulo para Paris
    results = api.search_flights(
        origin='GRU',        # Aeroporto de Guarulhos
        destination='CDG',   # Charles de Gaulle
        departure_date='2024-03-15',
        return_date='2024-03-22'
    )
    
    print("\n=== Resultados da Busca de Voos ===")
    if isinstance(results, list):
        for i, flight in enumerate(results, 1):
            print(f"\nVoo {i}:")
            print(f"Preço: {flight['price']['amount']} {flight['price']['currency']}")
            
            print("\nIda:")
            for segment in flight['outbound']['segments']:
                print(f"  {segment['departure']['airport']} -> {segment['arrival']['airport']}")
                print(f"  Voo: {segment['carrier']}{segment['flight_number']}")
                print(f"  Horário: {segment['departure']['time']} -> {segment['arrival']['time']}")
            
            if 'inbound' in flight:
                print("\nVolta:")
                for segment in flight['inbound']['segments']:
                    print(f"  {segment['departure']['airport']} -> {segment['arrival']['airport']}")
                    print(f"  Voo: {segment['carrier']}{segment['flight_number']}")
                    print(f"  Horário: {segment['departure']['time']} -> {segment['arrival']['time']}")
    else:
        print("Erro:", results.get('error', 'Erro desconhecido'))

def test_hotels():
    api = TravelAPI()
    
    # Busca hotéis em Paris
    results = api.search_hotels(
        city_code='PAR',
        check_in_date='2024-03-15',
        check_out_date='2024-03-22'
    )
    
    print("\n=== Resultados da Busca de Hotéis ===")
    if isinstance(results, list):
        for i, hotel in enumerate(results, 1):
            print(f"\nHotel {i}:")
            print(f"Nome: {hotel['name']}")
            print(f"Classificação: {hotel['rating']} estrelas")
            print(f"Endereço: {', '.join(hotel['location']['address'])}")
            print(f"Cidade: {hotel['location']['city']}")
            if hotel['price']['amount']:
                print(f"Preço: {hotel['price']['amount']} {hotel['price']['currency']}")
            print(f"Comodidades: {', '.join(hotel['amenities'][:5])}...")
    else:
        print("Erro:", results.get('error', 'Erro desconhecido'))

def test_activities():
    api = TravelAPI()
    
    # Busca atividades em Paris (coordenadas da Torre Eiffel)
    results = api.search_activities(
        latitude=48.8584,
        longitude=2.2945
    )
    
    print("\n=== Resultados da Busca de Atividades ===")
    if isinstance(results, list):
        for i, activity in enumerate(results, 1):
            print(f"\nAtividade {i}:")
            print(f"Nome: {activity['name']}")
            print(f"Descrição: {activity['description'][:100]}...")
            print(f"Preço: {activity['price']['amount']} {activity['price']['currency']}")
            if activity['rating']:
                print(f"Avaliação: {activity['rating']}")
            if activity['booking_link']:
                print(f"Link para reserva: {activity['booking_link']}")
    else:
        print("Erro:", results.get('error', 'Erro desconhecido'))

if __name__ == '__main__':
    print("Testando APIs de viagem...")
    test_flights()
    test_hotels()
    test_activities()
