import random

# =========================
# 👥 MOCK PLAYERS
# =========================

def create_mock_players(n=2):
    return [
        {
            "id": f"user_{i}",
            "name": f"Player_{i}",
            "difficulty": round(random.uniform(0.2, 0.9), 2),
            "nb_exercices": random.randint(1, 5),
            "cards": {
                "plus2_cards": 1,
                "skip_cards": 1,
                "reverse_cards": 1,
                "joker_cards": 1,
                "plus4_cards": 1
            },
            "hand": [random.randint(0, 3) for _ in range(7)]
        }
        for i in range(n)
    ]

# =========================
# 🎴 UNO STATE CHECK
# =========================

def check_uno(player):
    return sum(player["hand"]) == 1 and player["nb_exercices"] == 1

# =========================
# 🎮 ACTIONS
# =========================

def play_plus2(attacker, target):
    if attacker["cards"]["plus2_cards"] <= 0:
        return

    attacker["cards"]["plus2_cards"] -= 1

    if target.get("reverse_shield", False):
        target["reverse_shield"] = False
        attacker["nb_exercices"] += 2
        print(f"🔁 {target['name']} a renvoyé +2 à {attacker['name']}")
    else:
        target["nb_exercices"] += 2
        print(f"➕ {attacker['name']} impose +2 à {target['name']}")

def play_skip(player):
    if player["cards"]["skip_cards"] > 0:
        player["cards"]["skip_cards"] -= 1
        player["nb_exercices"] = max(0, player["nb_exercices"] - 2)
        print(f"⏭️ {player['name']} skip des exercices")

def play_reverse(player):
    if player["cards"]["reverse_cards"] > 0:
        player["cards"]["reverse_cards"] -= 1
        player["reverse_shield"] = True
        print(f"🛡️ {player['name']} active inversion (shield)")

def play_joker(player):
    if player["cards"]["joker_cards"] > 0:
        player["cards"]["joker_cards"] -= 1
        player["difficulty"] = round(random.uniform(0.1, 1), 2)
        print(f"🎴 {player['name']} change difficulté → {player['difficulty']}")

# =========================
# 🎮 GAME LOOP
# =========================

def run_match(players):
    turn = 0
    round_count = 0

    print("\n🚀 START MATCH\n")

    while round_count < 10:  # limite sécurité
        player = players[turn]

        print(f"\n🎯 Turn: {player['name']}")
        print(f"📊 Exercices: {player['nb_exercices']}")

        # 🔥 UNO CHECK
        if check_uno(player):
            print(f"🔴 UNO !!! {player['name']} est proche de la victoire")

        # 🎮 random action
        action = random.choice(["plus2", "skip", "reverse", "joker", "none"])

        if action == "plus2":
            target = random.choice([p for p in players if p != player])
            play_plus2(player, target)

        elif action == "skip":
            play_skip(player)

        elif action == "reverse":
            play_reverse(player)

        elif action == "joker":
            play_joker(player)

        else:
            print(f"😐 {player['name']} passe son tour")

        # 🏁 win condition
        if player["nb_exercices"] == 0:
            print(f"\n🏆 {player['name']} a gagné le match !")
            break

        # next player
        turn = (turn + 1) % len(players)
        round_count += 1

# =========================
# 🧪 TEST SCENARIOS
# =========================

def test_2_players():
    players = create_mock_players(2)
    run_match(players)

def test_4_players():
    players = create_mock_players(4)
    run_match(players)

# =========================
# ▶️ EXECUTION
# =========================

if __name__ == "__main__":
    print("\n====================")
    print("🎮 TEST 2 PLAYERS")
    print("====================")
    test_2_players()

    print("\n====================")
    print("🎮 TEST 4 PLAYERS")
    print("====================")
    test_4_players()