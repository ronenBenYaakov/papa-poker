import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from collections import Counter
from itertools import combinations
import os
import cv2
from PIL import Image

from treys import Card, Evaluator, Deck
from inference import get_model

# Load model globally
model = get_model(model_id="poker-j2pzb/2")

def parse_treys_card(card_str):
    rank = card_str[:-1].upper().replace('10', 'T')
    suit = card_str[-1].lower()
    return Card.new(rank + suit)

def create_hands(image_paths):
    hands = []
    for path in image_paths:
        # Read image with OpenCV
        img_cv = cv2.imread(path)
        if img_cv is None:
            raise FileNotFoundError(f"Could not read image: {path}")
        
        # Convert BGR to RGB and then to PIL Image for inference
        img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        results = model.infer(pil_img)  # pass PIL Image here
        predictions = results[0].predictions
        labels_list = [p.class_name for p in predictions]

        if len(labels_list) % 2 != 0:
            raise ValueError(f"{os.path.basename(path)}: Detected cards do not form a complete hand.")

        hand = labels_list[:2]
        hands.append(hand)
    return hands

def simulate_win_probabilities(known_hands, game_type="texas_holdem", nb_simulation=1000, total_players=9):
    evaluator = Evaluator()
    parsed_known = [[parse_treys_card(card) for card in hand] for hand in known_hands]
    num_real = len(parsed_known)
    wins = Counter()

    for _ in range(nb_simulation):
        used = [c for hand in parsed_known for c in hand]
        deck = Deck()
        deck.cards = [c for c in deck.cards if c not in used]

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

# Import your screenshot function here (make sure it returns a list of paths)
from windows import screenshot_quarter_screen_windows

class PokerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Poker Win Probability")
        self.image_paths = []

        # Controls frame
        frame = tk.Frame(root)
        frame.pack(pady=10)

        self.upload_btn = tk.Button(frame, text="Upload Hand Images", command=self.upload_images)
        self.upload_btn.pack(side=tk.LEFT, padx=10)

        self.screenshot_btn = tk.Button(frame, text="Use Quarter-Screen Window Screenshots", command=self.use_screenshots)
        self.screenshot_btn.pack(side=tk.LEFT, padx=10)

        self.game_type = tk.StringVar(value="texas_holdem")
        self.game_dropdown = ttk.Combobox(frame, textvariable=self.game_type, values=["texas_holdem", "omaha"], state="readonly", width=15)
        self.game_dropdown.pack(side=tk.LEFT, padx=10)

        self.run_btn = tk.Button(frame, text="Run Simulation", command=self.run_simulation)
        self.run_btn.pack(side=tk.LEFT, padx=10)

        # Output textbox
        self.output_text = tk.Text(root, height=15, width=70)
        self.output_text.pack(padx=10, pady=10)

    def upload_images(self):
        files = filedialog.askopenfilenames(filetypes=[("Images", "*.jpg *.png *.jpeg")])
        if files:
            self.image_paths = list(files)
            self.output_text.insert(tk.END, f"✅ Selected {len(files)} image(s).\n")

    def use_screenshots(self):
        self.output_text.insert(tk.END, "📸 Taking screenshots of quarter-screen windows...\n")
        self.root.update()
        try:
            self.image_paths = screenshot_quarter_screen_windows()
            if self.image_paths:
                self.output_text.insert(tk.END, f"✅ Captured {len(self.image_paths)} screenshots.\n")
            else:
                self.output_text.insert(tk.END, "⚠️ No quarter-screen windows detected.\n")
        except Exception as e:
            messagebox.showerror("Screenshot Error", str(e))

    def run_simulation(self):
        self.output_text.delete(1.0, tk.END)

        if not self.image_paths:
            messagebox.showerror("Error", "Please upload images or take screenshots first.")
            return

        try:
            hands = create_hands(self.image_paths)
            probs = simulate_win_probabilities(hands, game_type=self.game_type.get())
            for i, p in enumerate(probs):
                self.output_text.insert(tk.END, f"Hand {i+1}: {p*100:.2f}% win probability\n")
        except Exception as e:
            messagebox.showerror("Simulation Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = PokerApp(root)
    root.mainloop()
