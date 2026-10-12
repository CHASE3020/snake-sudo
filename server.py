import http.server
import json
import random
import os

WIDTH = 20
HEIGHT = 20

class SnakeGame:
    def __init__(self):
        self.reset()

    def reset(self):
        # Start at center, length 3, moving UP
        self.snake = [(10, 10), (10, 11), (10, 12)] 
        self.direction = "UP"
        self.last_moved_direction = "UP"
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
            
        # Food Generation on Snake Body edge case handled strictly via Sets
        all_pos = {(x, y) for x in range(WIDTH) for y in range(HEIGHT)}
        snake_pos = set(self.snake)
        empty_pos = list(all_pos - snake_pos)
        
        if not empty_pos:
            self.win = True
            self.game_over = True
            self.food = None
        else:
            self.food = random.choice(empty_pos)

    def tick(self, input_dir):
        if self.game_over:
            return

        valid_dirs = {"UP", "DOWN", "LEFT", "RIGHT"}
        opposites = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
        
        # Rapid-Input Suicide prevention: strictly compare to LAST MOVED direction
        if input_dir in valid_dirs:
            if opposites.get(input_dir) != self.last_moved_direction:
                self.direction = input_dir

        head_x, head_y = self.snake[0]
        if self.direction == "UP": head_y -= 1
        elif self.direction == "DOWN": head_y += 1
        elif self.direction == "LEFT": head_x -= 1
        elif self.direction == "RIGHT": head_x += 1

        new_head = (head_x, head_y)

        # Boundary & Wall Collisions
        if head_x < 0 or head_x >= WIDTH or head_y < 0 or head_y >= HEIGHT:
            self.game_over = True
            return

        eating = (self.food is not None) and (new_head == self.food)

        # Tail-Chasing / Tail-Space Collision edge case
        # If the snake eats, the tail stays. If not, the tail moves. 
        # Moving into the old tail spot is perfectly valid.
        collision_body = self.snake if eating else self.snake[:-1]
        
        if new_head in collision_body:
            self.game_over = True
            return

        self.snake.insert(0, new_head)
        self.last_moved_direction = self.direction

        if eating:
            self.score += 10
            self.spawn_food()
        else:
            self.snake.pop()

        # Win Condition (Board Full)
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
            "last_moved_direction": self.last_moved_direction
        }

# Global isolated state
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
                self.send_error(404, "index.html not found. Ensure it is in the same directory.")
        else:
            self.send_error(404)

    def do_POST(self):
        global game
        if self.path == '/start':
            game.reset() # Clean isolation
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
        else:
            self.send_error(404)

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    # Suppress console logging to keep terminal clean
    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    port = 8000
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, GameServerHandler)
    print(f"🐍 Server running on port {port}...")
    print(f"🎮 Play the game at: http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()