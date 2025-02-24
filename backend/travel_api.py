import os
from amadeus import Client, ResponseError
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class TravelAPI:
    def __init__(self):
        self.amadeus = Client(
            client_id=os.getenv('AMADEUS_API_KEY'),
            client_secret=os.getenv('AMADEUS_API_SECRET')
        )

    def search_flights(self, origin, destination, departure_date, return_date=None):
        """
        Busca voos usando a API da Amadeus
        """
        try:
            if return_date:
                response = self.amadeus.shopping.flight_offers_search.get(
                    originLocationCode=origin,
                    destinationLocationCode=destination,
                    departureDate=departure_date,
                    returnDate=return_date,
                    adults=1,
                    max=5
                )
            else:
                response = self.amadeus.shopping.flight_offers_search.get(
                    originLocationCode=origin,
                    destinationLocationCode=destination,
                    departureDate=departure_date,
                    adults=1,
                    max=5
                )

            return self._format_flight_response(response.data)
        except ResponseError as error:
            return {"error": str(error)}

    def search_hotels(self, city_code, check_in_date, check_out_date):
        """
        Busca hotéis usando a API da Amadeus
        """
        try:
            # Primeiro, obtém as coordenadas da cidade
            city_search = self.amadeus.reference_data.locations.get(
                keyword=city_code,
                subType=["CITY"]
            )

            if not city_search.data:
                return {"error": "Cidade não encontrada"}

            city = city_search.data[0]
            
            # Busca hotéis na cidade
            hotels = self.amadeus.shopping.hotel_offers.get(
                cityCode=city['iataCode'],
                checkInDate=check_in_date,
                checkOutDate=check_out_date,
                adults=1,
                radius=20,
                radiusUnit='KM',
                paymentPolicy='NONE',
                includeClosed=False,
                bestRateOnly=True,
                view='FULL'
            )

            return self._format_hotel_response(hotels.data)
        except ResponseError as error:
            return {"error": str(error)}

    def search_activities(self, latitude, longitude):
        """
        Busca atividades próximas usando a API da Amadeus
        """
        try:
            activities = self.amadeus.shopping.activities.get(
                latitude=latitude,
                longitude=longitude,
                radius=20
            )

            return self._format_activity_response(activities.data)
        except ResponseError as error:
            return {"error": str(error)}

    def _format_flight_response(self, flights):
        """
        Formata a resposta de voos para um formato mais amigável
        """
        formatted_flights = []
        for flight in flights:
            price = flight['price']
            itineraries = flight['itineraries']
            
            formatted_flight = {
                'price': {
                    'amount': price['total'],
                    'currency': price['currency']
                },
                'outbound': self._format_itinerary(itineraries[0]),
            }
            
            if len(itineraries) > 1:
                formatted_flight['inbound'] = self._format_itinerary(itineraries[1])
            
            formatted_flights.append(formatted_flight)
            
        return formatted_flights

    def _format_itinerary(self, itinerary):
        """
        Formata um itinerário de voo
        """
        segments = []
        for segment in itinerary['segments']:
            segments.append({
                'departure': {
                    'airport': segment['departure']['iataCode'],
                    'time': segment['departure']['at']
                },
                'arrival': {
                    'airport': segment['arrival']['iataCode'],
                    'time': segment['arrival']['at']
                },
                'carrier': segment['carrierCode'],
                'flight_number': segment['number']
            })
            
        return {
            'duration': itinerary['duration'],
            'segments': segments
        }

    def _format_hotel_response(self, hotels):
        """
        Formata a resposta de hotéis para um formato mais amigável
        """
        formatted_hotels = []
        for hotel in hotels:
            offers = hotel['offers'][0] if hotel.get('offers') else {}
            formatted_hotel = {
                'name': hotel['hotel']['name'],
                'rating': hotel['hotel'].get('rating'),
                'location': {
                    'address': hotel['hotel']['address'].get('lines', []),
                    'city': hotel['hotel']['address'].get('cityName'),
                },
                'price': {
                    'amount': offers.get('price', {}).get('total'),
                    'currency': offers.get('price', {}).get('currency')
                },
                'amenities': hotel['hotel'].get('amenities', []),
                'available': True
            }
            formatted_hotels.append(formatted_hotel)
            
        return formatted_hotels

    def _format_activity_response(self, activities):
        """
        Formata a resposta de atividades para um formato mais amigável
        """
        formatted_activities = []
        for activity in activities:
            formatted_activity = {
                'name': activity['name'],
                'description': activity.get('shortDescription', ''),
                'price': {
                    'amount': activity['price']['amount'],
                    'currency': activity['price']['currencyCode']
                },
                'rating': activity.get('rating'),
                'pictures': [pic['uri'] for pic in activity.get('pictures', [])],
                'booking_link': activity.get('bookingLink')
            }
            formatted_activities.append(formatted_activity)
            
        return formatted_activities
