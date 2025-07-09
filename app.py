from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from itertools import combinations
from inference import get_model
import os
import cv2
from treys import Card, Evaluator, Deck
from collections import Counter
import tempfile

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload size

# === Load model globally ===
model = get_model(model_id="poker-j2pzb/2")

# === Parse card string for Treys ===
def parse_treys_card(card_str):
    rank = card_str[:-1].upper().replace('10', 'T')
    suit = card_str[-1].lower()
    return Card.new(rank + suit)

# === Detect and convert cards from images ===
def create_hands(image_paths):
    hands = []
    for path in image_paths:
        img = cv2.imread(path)
        results = model.infer(img)
        predictions = results[0].predictions
        labels_list = [p.class_name for p in predictions]

        if len(labels_list) % 2 != 0:
            raise ValueError(f"{os.path.basename(path)}: Detected cards do not form a complete hand.")

        hand = labels_list[:2]
        hands.append(hand)
    return hands

# === Simulation ===
def simulate_win_probabilities(known_hands, game_type="texas_holdem", nb_simulation=1000, total_players=9):
    evaluator = Evaluator()
    parsed_known = [[parse_treys_card(card) for card in hand] for hand in known_hands]
    num_real = len(parsed_known)
    wins = Counter()

    for _ in range(nb_simulation):
        used = [c for hand in parsed_known for c in hand]
        deck = Deck()
        deck.cards = [c for c in deck.cards if c not in used]

        # Fill rest of table
        remaining = total_players - num_real
        random_hands = [deck.draw(2) for _ in range(remaining)]

        all_hands = parsed_known + random_hands
        community = deck.draw(5)

        scores = []
        for hand in all_hands:
            if game_type == "omaha":
                best_score = min(
                    evaluator.evaluate(hcombo, bcombo)
                    for hcombo in combinations(hand, 2)
                    for bcombo in combinations(community, 3)
                )
            else:
                best_score = evaluator.evaluate(hand, community)
            scores.append(best_score)

        min_score = min(scores)
        winners = [i for i, s in enumerate(scores) if s == min_score]
        for w in winners:
            if w < num_real:
                wins[w] += 1 / len(winners)

    return [round(wins[i] / nb_simulation, 4) for i in range(num_real)]

# === Routes ===

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        files = request.files.getlist("images")
        game_type = request.form.get("game_type")

        if not files:
            return render_template("index.html", error="No files selected.")

        saved_paths = []
        for file in files:
            filename = secure_filename(file.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(path)
            saved_paths.append(path)

        try:
            known_hands = create_hands(saved_paths)
            probs = simulate_win_probabilities(known_hands, game_type=game_type)
            results = [(f"Hand {i+1}", f"{prob*100:.2f}%") for i, prob in enumerate(probs)]
            return render_template("result.html", results=results, game_type=game_type.replace("_", " ").title())
        except Exception as e:
            return render_template("index.html", error=str(e))

    return render_template("index.html")

# === Run app ===
if __name__ == "__main__":
    app.run(debug=True)
