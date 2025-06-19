from flask import Flask, render_template, request
import osmnx as ox
import networkx as nx
import folium
import os

app = Flask(__name__)

# Charger les graphes pour voiture et pied
print("📥 Chargement des cartes OSM...")
GRAPHS = {
    "voiture": ox.graph_from_place("Casablanca, Morocco", network_type='drive'),
    "pied": ox.graph_from_place("Casablanca, Morocco", network_type='walk')
}

# Vitesse moyenne en km/h
VITESSE_KMH = {
    "voiture": 40,
    "pied": 5
}

# Géocodage flexible
def get_location(input_str):
    try:
        if ',' in input_str:
            lat, lon = map(float, input_str.strip().split(','))
            return (lat, lon)
        else:
            return ox.geocode(input_str + ", Casablanca, Morocco")
    except:
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        start_input = request.form['start']
        end_input = request.form['end']
        mode = request.form['mode']

        if mode not in GRAPHS:
            return render_template('index.html', error="❌ Mode de transport invalide.")

        G = GRAPHS[mode]
        start_point = get_location(start_input)
        end_point = get_location(end_input)

        if not start_point or not end_point:
            return render_template('index.html', error="⚠️ Adresse invalide.")

        try:
            start_node = ox.distance.nearest_nodes(G, X=start_point[1], Y=start_point[0])
            end_node = ox.distance.nearest_nodes(G, X=end_point[1], Y=end_point[0])
            chemin = nx.shortest_path(G, start_node, end_node, weight='length')

            # Calcul distance manuellement
            distance_m = sum(
                G[u][v][0]['length'] for u, v in zip(chemin[:-1], chemin[1:])
            )
            distance_km = distance_m / 1000
            duree_min = (distance_km / VITESSE_KMH[mode]) * 60

            # Carte
            m = folium.Map(location=start_point, zoom_start=14)
            folium.Marker(start_point, popup="Départ", icon=folium.Icon(color="green")).add_to(m)
            folium.Marker(end_point, popup="Arrivée", icon=folium.Icon(color="red")).add_to(m)
            coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in chemin]
            folium.PolyLine(coords, color="blue", weight=5, opacity=0.8).add_to(m)

            m.save(os.path.join("static", "chemin.html"))

            return render_template(
                'result.html',
                distance=round(distance_km, 2),
                duree=round(duree_min),
                mode=mode
            )

        except Exception as e:
            return render_template('index.html', error=f"❌ Erreur pendant le calcul : {e}")

    return render_template('index.html')
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
