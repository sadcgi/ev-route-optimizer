from flask import Flask, render_template, request, jsonify
import requests
import math
import time

app = Flask(__name__)

OSRM_BASE = "http://router.project-osrm.org"
NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT = "EV-Route-Optimizer/1.0 (local-dev-project)"

# ─── UK EV Charging Station Dataset ─────────────────────────────────────────
# Includes motorway services, GRIDSERVE forecourts, city hubs, airports, retail
CHARGING_STATIONS = [
    # M1 Corridor
    {"id": 1,  "name": "Moto Woolley Edge (M1 J38)",         "lat": 53.6089, "lon": -1.5614, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 2,  "name": "Moto Woodall (M1 J31)",              "lat": 53.3712, "lon": -1.3157, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 3,  "name": "Moto Tibshelf (M1 J28)",             "lat": 53.1198, "lon": -1.3395, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 4,  "name": "Welcome Break Donington Park (M1)",  "lat": 52.8321, "lon": -1.3640, "power_kw": 150, "network": "Pod Point",  "connectors": ["CCS", "CHAdeMO"]},
    {"id": 5,  "name": "Moto Leicester Forest East (M1 J21)","lat": 52.6156, "lon": -1.2271, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 6,  "name": "Moto Toddington (M1 J11)",           "lat": 51.9379, "lon": -0.4742, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 7,  "name": "Moto London Gateway (M1 J7)",        "lat": 51.7003, "lon": -0.3673, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    # M6 Corridor
    {"id": 8,  "name": "Moto Corley (M6 J3a)",              "lat": 52.4603, "lon": -1.5388, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 9,  "name": "Moto Hilton Park (M6 J10a)",        "lat": 52.6139, "lon": -2.0174, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 10, "name": "Moto Stafford (M6 J14)",            "lat": 52.8312, "lon": -2.0523, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 11, "name": "Moto Knutsford (M6 J19)",           "lat": 53.3047, "lon": -2.3695, "power_kw": 150, "network": "Pod Point",  "connectors": ["CCS", "CHAdeMO"]},
    {"id": 12, "name": "Moto Charnock Richard (M6 J27)",    "lat": 53.6259, "lon": -2.6635, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 13, "name": "Moto Lancaster (M6 J33)",           "lat": 54.0541, "lon": -2.7013, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 14, "name": "Moto Tebay (M6 J38)",               "lat": 54.4286, "lon": -2.5824, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 15, "name": "Moto Southwaite (M6 J41)",          "lat": 54.7889, "lon": -2.8289, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    # M4 Corridor
    {"id": 16, "name": "Moto Reading (M4 J11)",             "lat": 51.4342, "lon": -1.0318, "power_kw": 350, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 17, "name": "Moto Membury (M4 J14)",             "lat": 51.5085, "lon": -1.5611, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 18, "name": "Welcome Break Swindon (M4 J16)",    "lat": 51.5763, "lon": -1.7945, "power_kw": 150, "network": "Pod Point",  "connectors": ["CCS", "CHAdeMO"]},
    {"id": 19, "name": "Moto Leigh Delamere (M4 J17)",      "lat": 51.5173, "lon": -2.1219, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 20, "name": "Welcome Break Magor (M4 J23)",      "lat": 51.5757, "lon": -2.8467, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 21, "name": "Sarn Park Services (M4 J36)",       "lat": 51.5293, "lon": -3.6179, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    # M25 Ring
    {"id": 22, "name": "Moto Clacket Lane (M25 J5)",        "lat": 51.2891, "lon":  0.0135, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 23, "name": "Welcome Break Cobham (M25 J9)",     "lat": 51.3237, "lon": -0.3993, "power_kw": 150, "network": "Pod Point",  "connectors": ["CCS", "CHAdeMO"]},
    {"id": 24, "name": "Moto Thurrock (M25 J31)",           "lat": 51.4836, "lon":  0.3296, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 25, "name": "Welcome Break South Mimms (M25)",   "lat": 51.7178, "lon": -0.2116, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    # M5 Corridor
    {"id": 26, "name": "Moto Strensham (M5 J8)",            "lat": 52.0786, "lon": -2.1006, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 27, "name": "Moto Michaelwood (M5 J14)",         "lat": 51.6679, "lon": -2.4064, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 28, "name": "Moto Gordano (M5 J19)",             "lat": 51.4687, "lon": -2.7551, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 29, "name": "Moto Bridgwater (M5 J24)",          "lat": 51.1448, "lon": -2.9895, "power_kw": 150, "network": "Pod Point",  "connectors": ["CCS", "CHAdeMO"]},
    {"id": 30, "name": "Moto Taunton Deane (M5 J25)",       "lat": 51.0301, "lon": -3.0823, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 31, "name": "GRIDSERVE Exeter (M5 J29)",         "lat": 50.7286, "lon": -3.4764, "power_kw": 350, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    # A1(M) East Coast
    {"id": 32, "name": "Moto Baldock (A1M)",                "lat": 51.9913, "lon": -0.1872, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 33, "name": "Moto Peterborough (A1M)",           "lat": 52.6032, "lon": -0.3067, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 34, "name": "Moto Blyth (A1M J34)",             "lat": 53.4098, "lon": -1.0556, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 35, "name": "Welcome Break Washington (A1M)",    "lat": 54.9068, "lon": -1.5187, "power_kw": 150, "network": "Pod Point",  "connectors": ["CCS", "CHAdeMO"]},
    # M40 Corridor
    {"id": 36, "name": "Welcome Break Cherwell Valley (M40)","lat": 51.9738, "lon": -1.2751, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 37, "name": "Welcome Break Warwick (M40 J15)",   "lat": 52.2854, "lon": -1.5874, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    # M3 Corridor
    {"id": 38, "name": "Fleet Services (M3 J4a)",           "lat": 51.2756, "lon": -0.8513, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 39, "name": "Winchester Services (M3 J9)",       "lat": 51.0677, "lon": -1.3120, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    # M11 Corridor
    {"id": 40, "name": "Birchanger Green (M11 J8)",         "lat": 51.8842, "lon":  0.1731, "power_kw": 150, "network": "Pod Point",  "connectors": ["CCS", "CHAdeMO"]},
    # M62 Corridor
    {"id": 41, "name": "Moto Ferrybridge (M62 J33)",        "lat": 53.7019, "lon": -1.2744, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 42, "name": "Birch Services (M62 J18)",          "lat": 53.5847, "lon": -2.1441, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    # GRIDSERVE Electric Forecourts
    {"id": 43, "name": "GRIDSERVE Electric Forecourt Braintree","lat": 51.8778,"lon": 0.5509,"power_kw": 350, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 44, "name": "GRIDSERVE Electric Forecourt Norwich", "lat": 52.6280,"lon": 1.2977,"power_kw": 350, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 45, "name": "GRIDSERVE Electric Forecourt Gatwick","lat": 51.1567,"lon":-0.1683,"power_kw": 350, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    # IONITY Hubs
    {"id": 46, "name": "IONITY Rugby",                      "lat": 52.3684, "lon": -1.2666, "power_kw": 350, "network": "IONITY",     "connectors": ["CCS"]},
    {"id": 47, "name": "IONITY Grantham",                   "lat": 52.9168, "lon": -0.6447, "power_kw": 350, "network": "IONITY",     "connectors": ["CCS"]},
    {"id": 48, "name": "IONITY Exeter",                     "lat": 50.7256, "lon": -3.4834, "power_kw": 350, "network": "IONITY",     "connectors": ["CCS"]},
    {"id": 49, "name": "IONITY Carlisle",                   "lat": 54.8825, "lon": -2.9332, "power_kw": 350, "network": "IONITY",     "connectors": ["CCS"]},
    {"id": 50, "name": "IONITY Perth",                      "lat": 56.4018, "lon": -3.4370, "power_kw": 350, "network": "IONITY",     "connectors": ["CCS"]},
    {"id": 51, "name": "IONITY Scotch Corner",              "lat": 54.4356, "lon": -1.6715, "power_kw": 350, "network": "IONITY",     "connectors": ["CCS"]},
    # London
    {"id": 52, "name": "Pod Point Westminster",             "lat": 51.5016, "lon": -0.1296, "power_kw":  50, "network": "Pod Point",  "connectors": ["CCS", "Type 2"]},
    {"id": 53, "name": "ChargePoint Canary Wharf",          "lat": 51.5035, "lon": -0.0209, "power_kw":  50, "network": "ChargePoint","connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 54, "name": "Osprey Croydon",                    "lat": 51.3763, "lon": -0.0982, "power_kw": 150, "network": "Osprey",     "connectors": ["CCS", "CHAdeMO"]},
    {"id": 55, "name": "Instavolt Stratford",               "lat": 51.5431, "lon":  0.0080, "power_kw": 150, "network": "Instavolt",  "connectors": ["CCS", "CHAdeMO"]},
    {"id": 56, "name": "ChargePoint Heathrow Airport",      "lat": 51.4700, "lon": -0.4543, "power_kw":  50, "network": "ChargePoint","connectors": ["CCS", "Type 2"]},
    {"id": 57, "name": "BP Pulse Stansted Airport",         "lat": 51.8850, "lon":  0.2389, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 58, "name": "Osprey Wembley",                    "lat": 51.5560, "lon": -0.2796, "power_kw": 150, "network": "Osprey",     "connectors": ["CCS", "CHAdeMO"]},
    # Birmingham
    {"id": 59, "name": "NEC Birmingham",                    "lat": 52.4514, "lon": -1.7236, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 60, "name": "Brindleyplace Birmingham",          "lat": 52.4773, "lon": -1.9139, "power_kw":  50, "network": "Pod Point",  "connectors": ["CCS", "Type 2"]},
    {"id": 61, "name": "Merry Hill Brierley Hill",          "lat": 52.4828, "lon": -2.0919, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    # Manchester
    {"id": 62, "name": "Trafford Centre Manchester",        "lat": 53.4668, "lon": -2.3479, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 63, "name": "Manchester Airport",                "lat": 53.3658, "lon": -2.2727, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 64, "name": "Arndale Manchester City",           "lat": 53.4831, "lon": -2.2418, "power_kw":  50, "network": "ChargePoint","connectors": ["CCS", "Type 2"]},
    # Leeds
    {"id": 65, "name": "White Rose Leeds",                  "lat": 53.7617, "lon": -1.5802, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 66, "name": "Leeds Bradford Airport",            "lat": 53.8659, "lon": -1.6607, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    # Sheffield
    {"id": 67, "name": "Meadowhall Sheffield",              "lat": 53.4140, "lon": -1.4121, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    # Liverpool
    {"id": 68, "name": "Liverpool ONE",                     "lat": 53.4017, "lon": -2.9905, "power_kw": 150, "network": "Pod Point",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 69, "name": "Liverpool Airport",                 "lat": 53.3337, "lon": -2.8497, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    # Newcastle
    {"id": 70, "name": "Gateshead Metrocentre",             "lat": 54.9572, "lon": -1.6770, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 71, "name": "Newcastle Airport",                 "lat": 55.0374, "lon": -1.6916, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 72, "name": "Osprey Newcastle Silverlink",       "lat": 55.0187, "lon": -1.5514, "power_kw": 150, "network": "Osprey",     "connectors": ["CCS", "CHAdeMO"]},
    # Edinburgh
    {"id": 73, "name": "Edinburgh Fort Kinnaird",           "lat": 55.9368, "lon": -3.0921, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 74, "name": "Edinburgh Cameron Toll",            "lat": 55.9211, "lon": -3.1617, "power_kw": 150, "network": "Osprey",     "connectors": ["CCS", "CHAdeMO"]},
    {"id": 75, "name": "Edinburgh Airport",                 "lat": 55.9508, "lon": -3.3615, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 76, "name": "Hermiston Gait Edinburgh",          "lat": 55.9267, "lon": -3.2943, "power_kw": 150, "network": "ChargePoint","connectors": ["CCS", "CHAdeMO"]},
    # Glasgow
    {"id": 77, "name": "Glasgow Fort",                      "lat": 55.8686, "lon": -4.1001, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 78, "name": "Silverburn Glasgow",                "lat": 55.8034, "lon": -4.3230, "power_kw": 150, "network": "Pod Point",  "connectors": ["CCS", "CHAdeMO"]},
    {"id": 79, "name": "Glasgow Airport",                   "lat": 55.8720, "lon": -4.4338, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    # Cardiff
    {"id": 80, "name": "St David's Cardiff",                "lat": 51.4819, "lon": -3.1751, "power_kw": 150, "network": "Pod Point",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 81, "name": "Cardiff Gate",                      "lat": 51.5249, "lon": -3.1568, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    # Bristol
    {"id": 82, "name": "Cabot Circus Bristol",              "lat": 51.4589, "lon": -2.5822, "power_kw": 150, "network": "ChargePoint","connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 83, "name": "Cribbs Causeway Bristol",           "lat": 51.5238, "lon": -2.5943, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    # Nottingham / East Midlands
    {"id": 84, "name": "Victoria Centre Nottingham",        "lat": 52.9551, "lon": -1.1462, "power_kw": 150, "network": "Pod Point",  "connectors": ["CCS", "CHAdeMO"]},
    {"id": 85, "name": "East Midlands Airport",             "lat": 52.8311, "lon": -1.3280, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    # Leicester
    {"id": 86, "name": "Fosse Park Leicester",              "lat": 52.5965, "lon": -1.1900, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    # Oxford
    {"id": 87, "name": "Kassam Stadium Oxford",             "lat": 51.6981, "lon": -1.2046, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    # Cambridge
    {"id": 88, "name": "Grand Arcade Cambridge",            "lat": 52.2038, "lon":  0.1221, "power_kw":  50, "network": "ChargePoint","connectors": ["CCS", "Type 2"]},
    # Southampton
    {"id": 89, "name": "West Quay Southampton",             "lat": 50.9049, "lon": -1.4093, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 90, "name": "Southampton Airport",               "lat": 50.9503, "lon": -1.3568, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    # Portsmouth
    {"id": 91, "name": "Gunwharf Quays Portsmouth",         "lat": 50.7976, "lon": -1.1053, "power_kw": 150, "network": "Pod Point",  "connectors": ["CCS", "CHAdeMO"]},
    # Brighton
    {"id": 92, "name": "Brighton Marina",                   "lat": 50.8132, "lon": -0.1082, "power_kw": 150, "network": "Osprey",     "connectors": ["CCS", "CHAdeMO"]},
    # Norwich
    {"id": 93, "name": "Riverside Norwich",                 "lat": 52.6270, "lon":  1.2938, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    # Exeter / Plymouth / Cornwall
    {"id": 94, "name": "Princesshay Exeter",                "lat": 50.7237, "lon": -3.5279, "power_kw": 150, "network": "ChargePoint","connectors": ["CCS", "CHAdeMO"]},
    {"id": 95, "name": "Drake Circus Plymouth",             "lat": 50.3734, "lon": -4.1395, "power_kw": 150, "network": "Osprey",     "connectors": ["CCS", "CHAdeMO"]},
    {"id": 96, "name": "Truro Lemon Quay",                  "lat": 50.2601, "lon": -5.0513, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 97, "name": "Penzance",                          "lat": 50.1192, "lon": -5.5370, "power_kw":  50, "network": "Pod Point",  "connectors": ["CCS", "Type 2"]},
    # York / Yorkshire
    {"id": 98, "name": "Monks Cross York",                  "lat": 53.9938, "lon": -1.0426, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 99, "name": "Xscape Wakefield",                  "lat": 53.7064, "lon": -1.5556, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    # Teesside
    {"id": 100,"name": "Teesside Park Middlesbrough",       "lat": 54.5573, "lon": -1.2457, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    # Stirling / Perth / Dundee
    {"id": 101,"name": "Stirling Thistles",                 "lat": 56.1165, "lon": -3.9369, "power_kw": 150, "network": "ChargePoint","connectors": ["CCS", "CHAdeMO"]},
    {"id": 102,"name": "St Catherine's Perth",              "lat": 56.3975, "lon": -3.4306, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 103,"name": "Gallagher Retail Park Dundee",      "lat": 56.4785, "lon": -2.9739, "power_kw": 150, "network": "Osprey",     "connectors": ["CCS", "CHAdeMO"]},
    # Aberdeen / Inverness
    {"id": 104,"name": "Union Square Aberdeen",             "lat": 57.1437, "lon": -2.0960, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 105,"name": "Inverness Retail Park",             "lat": 57.4760, "lon": -4.2017, "power_kw": 150, "network": "ChargePoint","connectors": ["CCS", "CHAdeMO"]},
    # Swansea / Wales
    {"id": 106,"name": "Parc Trostre Swansea",             "lat": 51.6619, "lon": -4.0097, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 107,"name": "Eagles Meadow Wrexham",             "lat": 53.0458, "lon": -2.9943, "power_kw": 150, "network": "Pod Point",  "connectors": ["CCS", "CHAdeMO"]},
    # Midlands extra
    {"id": 108,"name": "Milton Keynes Centre",              "lat": 52.0429, "lon": -0.7591, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 109,"name": "Instavolt Milton Keynes",           "lat": 52.0306, "lon": -0.7240, "power_kw": 150, "network": "Instavolt",  "connectors": ["CCS", "CHAdeMO"]},
    {"id": 110,"name": "Luton Airport",                     "lat": 51.8747, "lon": -0.3683, "power_kw": 150, "network": "BP Pulse",   "connectors": ["CCS", "CHAdeMO"]},
    {"id": 111,"name": "The Oracle Reading",                "lat": 51.4551, "lon": -0.9700, "power_kw":  50, "network": "Pod Point",  "connectors": ["CCS", "Type 2"]},
    {"id": 112,"name": "Colchester Retail Park",            "lat": 51.8886, "lon":  0.9050, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 113,"name": "Gloucester Quays",                  "lat": 51.8564, "lon": -2.2511, "power_kw": 150, "network": "ChargePoint","connectors": ["CCS", "CHAdeMO"]},
    {"id": 114,"name": "SouthGate Bath",                    "lat": 51.3796, "lon": -2.3596, "power_kw":  50, "network": "Pod Point",  "connectors": ["CCS", "Type 2"]},
    {"id": 115,"name": "Coventry City Centre",              "lat": 52.4081, "lon": -1.5106, "power_kw": 150, "network": "Osprey",     "connectors": ["CCS", "CHAdeMO"]},
    # Scotland extras
    {"id": 116,"name": "Falkirk Retail Park",               "lat": 56.0028, "lon": -3.7934, "power_kw": 150, "network": "Osprey",     "connectors": ["CCS", "CHAdeMO"]},
    {"id": 117,"name": "Dunfermline Fife Retail Park",      "lat": 56.0735, "lon": -3.4491, "power_kw": 150, "network": "ChargePoint","connectors": ["CCS", "CHAdeMO"]},
    {"id": 118,"name": "Kilmarnock Galleon Centre",         "lat": 55.6121, "lon": -4.4926, "power_kw": 150, "network": "Pod Point",  "connectors": ["CCS", "CHAdeMO"]},
    {"id": 119,"name": "Dumfries Loreburn Centre",          "lat": 55.0700, "lon": -3.6030, "power_kw":  50, "network": "Pod Point",  "connectors": ["CCS", "Type 2"]},
    # North England extras
    {"id": 120,"name": "Preston St George's Centre",        "lat": 53.7620, "lon": -2.7021, "power_kw": 150, "network": "Osprey",     "connectors": ["CCS", "CHAdeMO"]},
    {"id": 121,"name": "Carlisle The Lanes",                "lat": 54.8931, "lon": -2.9364, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 122,"name": "St Marks Lincoln",                  "lat": 53.2279, "lon": -0.5404, "power_kw": 150, "network": "Osprey",     "connectors": ["CCS", "CHAdeMO"]},
    {"id": 123,"name": "Derby Meteor Centre",               "lat": 52.9368, "lon": -1.4974, "power_kw": 150, "network": "GRIDSERVE",  "connectors": ["CCS", "CHAdeMO", "Type 2"]},
    {"id": 124,"name": "Stoke Wolstanton Retail Park",      "lat": 53.0299, "lon": -2.2037, "power_kw": 150, "network": "ChargePoint","connectors": ["CCS", "CHAdeMO"]},
    {"id": 125,"name": "Nene Valley Retail Park Northampton","lat": 52.2381,"lon": -0.8671, "power_kw": 150, "network": "Osprey",     "connectors": ["CCS", "CHAdeMO"]},
]


# ─── Utility Functions ───────────────────────────────────────────────────────

def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def off_route_penalty(s_lat, s_lon, cur_lat, cur_lon, end_lat, end_lon):
    """
    Estimate how far a station deviates from the current→end straight line.
    Returns km of lateral deviation.
    """
    dx = end_lon - cur_lon
    dy = end_lat - cur_lat
    length_sq = dx * dx + dy * dy
    if length_sq < 1e-12:
        return 0.0
    # Project station onto the line segment
    t = ((s_lon - cur_lon) * dx + (s_lat - cur_lat) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    proj_lon = cur_lon + t * dx
    proj_lat = cur_lat + t * dy
    # Perpendicular distance (degrees → km approx)
    perp = math.sqrt((s_lon - proj_lon) ** 2 + (s_lat - proj_lat) ** 2)
    return perp * 111.0  # 1° ≈ 111 km


def geocode_location(query):
    """Nominatim geocoder – returns {lat, lon, display_name} or None."""
    url = f"{NOMINATIM_BASE}/search"
    params = {"q": query, "format": "json", "limit": 1,
              "countrycodes": "gb", "addressdetails": 0}
    try:
        r = requests.get(url, params=params,
                         headers={"User-Agent": USER_AGENT}, timeout=10)
        results = r.json()
        if results:
            return {
                "lat": float(results[0]["lat"]),
                "lon": float(results[0]["lon"]),
                "display_name": results[0]["display_name"],
            }
    except Exception as e:
        print(f"Geocode error: {e}")
    return None


def get_osrm_route(waypoints):
    """
    Fetch a driving route from the public OSRM instance.
    waypoints: list of (lat, lon) tuples
    Returns {geometry (list of [lon,lat]), distance_km, duration_hrs} or None.
    """
    coord_str = ";".join(f"{lon},{lat}" for lat, lon in waypoints)
    url = f"{OSRM_BASE}/route/v1/driving/{coord_str}"
    params = {"overview": "full", "geometries": "geojson", "annotations": "false"}
    try:
        r = requests.get(url, params=params, timeout=20)
        data = r.json()
        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            return {
                "geometry": route["geometry"]["coordinates"],  # [[lon,lat],…]
                "distance_km": route["distance"] / 1000.0,
                "duration_hrs": route["duration"] / 3600.0,
            }
    except Exception as e:
        print(f"OSRM error: {e}")
    return None


def estimate_charge_minutes(range_km, power_kw):
    """
    Estimate time (minutes) to charge from ~15 % to ~85 % (usable 70 % SoC).
    Assumes ~180 Wh/km consumption to estimate battery capacity.
    """
    battery_kwh = range_km * 0.18
    charge_kwh = battery_kwh * 0.70
    return round(charge_kwh / power_kw * 60)


# ─── Core Routing Algorithm ──────────────────────────────────────────────────

def calculate_charging_stops(start, end, range_km):
    """
    Greedy Maximum-Advance with Detour Penalty algorithm.

    From current position, score every station within usable range by:
        score = progress_km
              + fast_charger_bonus  (up to +20 km equivalent for 350 kW)
              - detour_penalty      (lateral deviation × 0.4)

    'progress_km' = reduction in straight-line distance to destination.
    A station must provide positive net progress to be selected.

    Returns (stops_list, error_string_or_None).
    """
    SAFETY_MARGIN = 0.18        # Keep 18 % in reserve
    DETOUR_WEIGHT  = 0.40       # Penalty factor for lateral deviation
    MAX_CHARGER_KW = 350.0
    FAST_BONUS_KM  = 20.0       # Max bonus for the fastest charger

    usable_range = range_km * (1.0 - SAFETY_MARGIN)

    current = start
    remaining = range_km          # Start fully charged
    stops = []

    for _ in range(25):           # Hard cap – prevents infinite loop
        dist_to_end = haversine(*current, *end)

        # Can we reach the destination on current charge?
        if dist_to_end <= remaining * (1.0 - SAFETY_MARGIN):
            break

        candidates = []
        for s in CHARGING_STATIONS:
            dist = haversine(*current, s["lat"], s["lon"])
            if dist >= usable_range:          # Not reachable
                continue
            if dist < 0.5:                    # Already at this station
                continue

            dist_s_to_end = haversine(s["lat"], s["lon"], *end)
            progress = dist_to_end - dist_s_to_end   # Positive = closer to end

            if progress < -20:               # Ignore stations that go far backward
                continue

            penalty = off_route_penalty(s["lat"], s["lon"], *current, *end)
            fast_bonus = (s["power_kw"] / MAX_CHARGER_KW) * FAST_BONUS_KM

            score = progress + fast_bonus - (penalty * DETOUR_WEIGHT)

            candidates.append({
                **s,
                "dist_from_here":  round(dist, 1),
                "dist_to_end":     round(dist_s_to_end, 1),
                "progress_km":     round(progress, 1),
                "detour_km":       round(penalty, 1),
                "score":           score,
                "charge_mins":     estimate_charge_minutes(range_km, s["power_kw"]),
            })

        if not candidates:
            return None, (
                f"No charging stations within the usable {usable_range:.0f} km range "
                f"from the current position. Try a vehicle with a longer range, or "
                f"reduce the safety buffer."
            )

        best = max(candidates, key=lambda x: x["score"])
        stops.append(best)
        remaining = range_km          # Fully recharged
        current = (best["lat"], best["lon"])

    else:
        return None, "Could not find a viable route within 25 charging stops."

    return stops, None


def get_nearby_stations(route_geom, max_dist_km=12):
    """Return stations within max_dist_km of any sampled route point."""
    step = max(1, len(route_geom) // 80)
    nearby_ids = set()
    for i in range(0, len(route_geom), step):
        lon, lat = route_geom[i]
        for s in CHARGING_STATIONS:
            if haversine(lat, lon, s["lat"], s["lon"]) <= max_dist_km:
                nearby_ids.add(s["id"])
    return [s for s in CHARGING_STATIONS if s["id"] in nearby_ids]


# ─── Flask Routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stations")
def all_stations():
    """Return the full charging station dataset for map initialisation."""
    return jsonify(CHARGING_STATIONS)


@app.route("/api/route", methods=["POST"])
def plan_route():
    data       = request.get_json()
    start_q    = (data.get("start") or "").strip()
    end_q      = (data.get("end")   or "").strip()
    range_km   = float(data.get("range_km", 300))

    if not start_q or not end_q:
        return jsonify({"error": "Please enter both a start and destination."}), 400
    if range_km < 30:
        return jsonify({"error": "Range must be at least 30 km."}), 400

    # ── Geocode ──────────────────────────────────────────────────────────────
    start_loc = geocode_location(start_q)
    time.sleep(1.1)                          # Nominatim rate-limit compliance
    end_loc   = geocode_location(end_q)

    if not start_loc:
        return jsonify({"error": f'Location not found: "{start_q}"'}), 400
    if not end_loc:
        return jsonify({"error": f'Location not found: "{end_q}"'}), 400

    start_coords = (start_loc["lat"], start_loc["lon"])
    end_coords   = (end_loc["lat"],   end_loc["lon"])

    direct_km = haversine(*start_coords, *end_coords)

    # ── Charging stop optimisation ───────────────────────────────────────────
    stops, err = calculate_charging_stops(start_coords, end_coords, range_km)
    if err:
        return jsonify({"error": err}), 400

    # ── OSRM routing ─────────────────────────────────────────────────────────
    waypoints = [start_coords] + [(s["lat"], s["lon"]) for s in stops] + [end_coords]
    route = get_osrm_route(waypoints)

    if not route:
        # Graceful fallback: straight-line segments
        geom = [[lon, lat] for lat, lon in waypoints]
        route = {
            "geometry":    geom,
            "distance_km": direct_km * 1.15,   # road-vs-straight correction
            "duration_hrs": direct_km * 1.15 / 80.0,
        }

    # ── Nearby stations for background display ───────────────────────────────
    nearby = get_nearby_stations(route["geometry"])

    # ── Energy estimate ──────────────────────────────────────────────────────
    energy_kwh = round(route["distance_km"] * 0.18, 1)

    return jsonify({
        "success": True,
        "start": {**start_loc, "query": start_q},
        "end":   {**end_loc,   "query": end_q},
        "charging_stops": stops,
        "route_geometry": route["geometry"],
        "stats": {
            "total_distance_km":  round(route["distance_km"], 1),
            "direct_distance_km": round(direct_km, 1),
            "duration_hrs":       round(route["duration_hrs"], 2),
            "num_stops":          len(stops),
            "energy_kwh":         energy_kwh,
            "range_km":           range_km,
        },
        "nearby_stations": nearby,
    })


if __name__ == "__main__":
    print("\n  EV Route Optimiser – starting on http://localhost:5000\n")
    app.run(debug=True, port=5000)
