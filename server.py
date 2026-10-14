import http.server
import json
import random
import os

WIDTH = 20
HEIGHT = 20
SCORES_FILE = "scores.json"

# --- Database / File I/O Logic ---
def load_scores():
    if not os.path.exists(SCORES_FILE):
        return []
    try:
        with open(SCORES_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_score(name, score):
    scores = load_scores()
    scores.append({"name": name, "score": score})
    # Sort by score descending
    scores.sort(key=lambda x: x["score"], reverse=True)
    # Keep only top 10
    scores = scores[:10]
    
    with open(SCORES_FILE, 'w') as f:
        json.dump(scores, f, indent=4)
    return scores
# ---------------------------------

class SnakeGame:
    def __init__(self):
        self.reset()

    def reset(self):
        self.snake = [(10, 10), (10, 11), (10, 12)] 
        self.direction = "UP"
        self.last_moved_direction = "UP"
        self.base_tick_rate = 130
        self.tick_rate = self.base_tick_rate
        self.food = None
        self.score = 0
        self.game_over = False
        self.win = False
        self.spawn_food()

    def spawn_food(self):
        if len(self.snake) >= WIDTH * HEIGHT:
            self.win = True
            self.game_over = True
            return
            
        all_pos = {(x, y) for x in range(WIDTH) for y in range(HEIGHT)}
        snake_pos = set(self.snake)
        empty_pos = list(all_pos - snake_pos)
        
        if not empty_pos:
            self.win = True
            self.game_over = True
            self.food = None
        else:
            pos = random.choice(empty_pos)
            food_types = ["normal", "fast", "slow"]
            weights = [0.6, 0.2, 0.2]
            chosen_type = random.choices(food_types, weights=weights, k=1)[0]
            self.food = {"pos": pos, "type": chosen_type}

    def tick(self, input_dir):
        if self.game_over:
            return

        valid_dirs = {"UP", "DOWN", "LEFT", "RIGHT"}
        opposites = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
        
        if input_dir in valid_dirs:
            if opposites.get(input_dir) != self.last_moved_direction:
                self.direction = input_dir

        head_x, head_y = self.snake[0]
        if self.direction == "UP": head_y -= 1
        elif self.direction == "DOWN": head_y += 1
        elif self.direction == "LEFT": head_x -= 1
        elif self.direction == "RIGHT": head_x += 1

        new_head = (head_x, head_y)

        if head_x < 0 or head_x >= WIDTH or head_y < 0 or head_y >= HEIGHT:
            self.game_over = True
            return

        eating = False
        if self.food is not None and new_head == self.food["pos"]:
            eating = True

        collision_body = self.snake if eating else self.snake[:-1]
        
        if new_head in collision_body:
            self.game_over = True
            return

        self.snake.insert(0, new_head)
        self.last_moved_direction = self.direction

        if eating:
            food_type = self.food["type"]
            if food_type == "normal":
                self.score += 10
            elif food_type == "fast":
                self.score += 20
                self.tick_rate = max(50, self.tick_rate - 25)
            elif food_type == "slow":
                self.score += 15
                self.tick_rate = min(220, self.tick_rate + 35)

            self.spawn_food()
        else:
            self.snake.pop()

        if len(self.snake) == WIDTH * HEIGHT:
            self.win = True
            self.game_over = True

    def to_dict(self):
        return {
            "snake": self.snake,
            "food": self.food,
            "score": self.score,
            "game_over": self.game_over,
            "win": self.win,
            "width": WIDTH,
            "height": HEIGHT,
            "tick_rate": self.tick_rate,
            "last_moved_direction": self.last_moved_direction
        }

game = SnakeGame()

class GameServerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            index_path = os.path.join(os.path.dirname(__file__), 'index.html')
            try:
                with open(index_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_error(404, "index.html not found.")
                
        # NEW: Provide leaderboard data to frontend
        elif self.path == '/leaderboard':
            scores = load_scores()
            self.send_json(scores)
        else:
            self.send_error(404)

    def do_POST(self):
        global game
        if self.path == '/start':
            game.reset()
            self.send_json(game.to_dict())
            
        elif self.path == '/tick':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            input_dir = None
            if post_data:
                data = json.loads(post_data)
                input_dir = data.get("direction")
                
            game.tick(input_dir)
            self.send_json(game.to_dict())
            
        # NEW: Accept new high scores
        elif self.path == '/submit_score':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            if post_data:
                data = json.loads(post_data)
                name = data.get("name", "Anonymous")
                score = data.get("score", 0)
                
                # Protect against fake giant scores (basic validation)
                if score == game.score and game.game_over:
                    updated_scores = save_score(name, score)
                    self.send_json({"success": True, "leaderboard": updated_scores})
                else:
                    self.send_error(400, "Invalid score submission.")
        else:
            self.send_error(404)

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    port = 8000
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, GameServerHandler)
    print(f"🐍 Global Leaderboard Server running on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()