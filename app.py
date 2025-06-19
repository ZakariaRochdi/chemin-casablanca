from flask import Flask, render_template, request
import osmnx as ox
import networkx as nx
import folium
import os

app = Flask(__name__)

# 📍 Chemins des fichiers locaux
GRAPH_FILES = {
    "voiture": "static/casa_drive.graphml",
    "pied": "static/casa_walk.graphml"
}

# 🚗 Vitesse moyenne en km/h
VITESSE_KMH = {
    "voiture": 40,
    "pied": 5
}

# 📥 Chargement + projection du graphe
def charger_graphe(mode):
    chemin_fichier = GRAPH_FILES[mode]
    if os.path.exists(chemin_fichier):
        print(f"✅ Chargement local du graphe {mode}")
        G = ox.load_graphml(chemin_fichier)
    else:
        print(f"📥 Téléchargement OSM du graphe {mode}")
        G = ox.graph_from_place("Casablanca, Morocco", network_type='drive' if mode == "voiture" else 'walk')
        ox.save_graphml(G, chemin_fichier)

    # ✅ Projection obligatoire pour distances correctes
    G = ox.project_graph(G)
    return G

# 🌍 Géocodage flexible
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

        G = charger_graphe(mode)
        start_point = get_location(start_input)
        end_point = get_location(end_input)

        if not start_point or not end_point:
            return render_template('index.html', error="⚠️ Adresse invalide.")

        try:
            # Recherche des nœuds les plus proches
            start_node = ox.distance.nearest_nodes(G, X=start_point[1], Y=start_point[0])
            end_node = ox.distance.nearest_nodes(G, X=end_point[1], Y=end_point[0])
            chemin = nx.shortest_path(G, start_node, end_node, weight='length')

            # Calcul distance
            distance_m = sum(G[u][v][0]['length'] for u, v in zip(chemin[:-1], chemin[1:]))
            distance_km = distance_m / 1000
            duree_min = (distance_km / VITESSE_KMH[mode]) * 60

            # 📍 Création de la carte
            m = folium.Map(location=start_point, zoom_start=14)
            folium.Marker(start_point, popup="Départ", icon=folium.Icon(color="green")).add_to(m)
            folium.Marker(end_point, popup="Arrivée", icon=folium.Icon(color="red")).add_to(m)
            coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in chemin]
            folium.PolyLine(coords, color="blue", weight=5).add_to(m)

            # Enregistrement
            m.save("static/chemin.html")

            return render_template('result.html',
                                   distance=round(distance_km, 2),
                                   duree=round(duree_min),
                                   mode=mode)
        except Exception as e:
            return render_template('index.html', error=f"❌ Erreur : {e}")

    return render_template('index.html')

# 🚀 Lancement avec Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
