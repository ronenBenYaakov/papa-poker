import tkinter as tk
from tkinter import filedialog, messagebox
from itertools import combinations
from inference import get_model
import cv2
from treys import Card, Evaluator, Deck
from collections import Counter

# === Load model globally once ===
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
            raise ValueError(f"{path}: Detected cards do not form a complete hand.")

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

# === GUI Code ===
def run_simulation(game_type):
    try:
        image_paths = filedialog.askopenfilenames(title="Select hand images (1 hand per image)", 
                                                  filetypes=[("Image files", "*.jpg *.png")])
        if not image_paths:
            return

        known_hands = create_hands(image_paths)
        probs = simulate_win_probabilities(known_hands, game_type=game_type)

        result_str = "\n".join([f"Hand {i+1}: {prob*100:.2f}%" for i, prob in enumerate(probs)])
        messagebox.showinfo(f"{game_type.replace('_', ' ').title()} Win Probabilities", result_str)

    except Exception as e:
        messagebox.showerror("Error", str(e))

# === Tkinter Window ===
def create_gui():
    window = tk.Tk()
    window.title("Poker Win Probability Simulator")
    window.geometry("400x220")

    label = tk.Label(window, text="Choose the Poker Game Type:", font=("Arial", 14))
    label.pack(pady=20)

    btn_texas = tk.Button(window, text="Texas Hold'em", font=("Arial", 12), bg="blue", fg="white",
                          command=lambda: run_simulation("texas_holdem"))
    btn_texas.pack(pady=10, ipadx=10, ipady=5)

    btn_omaha = tk.Button(window, text="Omaha", font=("Arial", 12), bg="orange", fg="white",
                         command=lambda: run_simulation("omaha"))
    btn_omaha.pack(pady=10, ipadx=10, ipady=5)

    window.mainloop()

# === Entry Point ===
if __name__ == "__main__":
    create_gui()
