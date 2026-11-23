import json

import frappe
import requests
from frappe.model.document import Document


class VehicleLocationLog(Document):
	def before_save(self):
		if not self.location:
			frappe.throw("Location name is required.")

		if not self.latitude and not self.longitude:
			coordinates = self.fetch_coordinates(self.location)

			if not coordinates:
				frappe.throw("Coordinates could not be fetched.")

			self.latitude = coordinates.get("latitude")
			self.longitude = coordinates.get("longitude")
			self.map = self.construct_map_field(coordinates)
			self.location_details = coordinates.get("display_name")

	def fetch_coordinates(self, location_name):
		url = "https://nominatim.openstreetmap.org/search"
		params = {"format": "json", "q": location_name}
		headers = {"User-Agent": "MyApp/1.0 (youremail@example.com)"}
		try:
			response = requests.get(url, params=params, headers=headers)
			response.raise_for_status()
			data = response.json()

			if not data:
				return None

			# Select the first entry from the results
			location = max(data, key=lambda x: x.get("importance", 0))
			return {
				"latitude": location.get("lat"),
				"longitude": location.get("lon"),
				"display_name": location.get("display_name"),
			}
		except requests.exceptions.RequestException as e:
			frappe.throw(f"Error fetching coordinates: {str(e)}")

	def construct_map_field(self, coordinates):
		map_data = {
			"type": "FeatureCollection",
			"features": [
				{
					"type": "Feature",
					"geometry": {
						"type": "Point",
						"coordinates": [float(coordinates["longitude"]), float(coordinates["latitude"])],
					},
					"properties": {"icon": "vehicle"},
				}
			],
		}
		return json.dumps(map_data)
