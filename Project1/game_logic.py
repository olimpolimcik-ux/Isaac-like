game_config.yaml:
yaml

# Настройки баланса (легко менять без перекомпиляции)
game:
  ball_speed: 5.0
  player_speed: 7.0
  winning_score: 5
  
physics:
  paddle_height: 100
  paddle_width: 10
  ball_radius: 5

game_logic.py:
python

import json
import yaml
import time
import os

class PongLogic:
    def init(self):
        self.load_config()
        self.reset_game()
        
    def load_config(self):
        with open('game_config.yaml', 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.ball_speed = self.config['game']['ball_speed']
        self.player_speed = self.config['game']['player_speed']
        self.winning_score = self.config['game']['winning_score']
    
    def reset_game(self):
        # Начальное состояние игры
        self.game_state = {
            "ball_x": 400, "ball_y": 300,
            "ball_speed_x": self.ball_speed, 
            "ball_speed_y": self.ball_speed,
            "player1_y": 300, "player2_y": 300,
            "player1_score": 0, "player2_score": 0,
            "game_running": True
        }
    
    def read_input(self):
        """Читает ввод от C++"""
        try:
            with open('../shared/input.json', 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def update_game(self, input_data):
        """Обновляет логику игры"""
        if not self.game_state["game_running"]:
            return
            
        # Движение ракеток
        if input_data.get("player1_up"):
            self.game_state["player1_y"] -= self.player_speed
        if input_data.get("player1_down"):
            self.game_state["player1_y"] += self.player_speed
        if input_data.get("player2_up"):
            self.game_state["player2_y"] -= self.player_speed
        if input_data.get("player2_down"):
            self.game_state["player2_y"] += self.player_speed
            
        # Движение мяча
        self.game_state["ball_x"] += self.game_state["ball_speed_x"]
        self.game_state["ball_y"] += self.game_state["ball_speed_y"]
        
        # Коллизии с верхом/низом
        if self.game_state["ball_y"] <= 0 or self.game_state["ball_y"] >= 600:
            self.game_state["ball_speed_y"] *= -1
            
        # Коллизии с ракетками
        self.check_paddle_collision()
        
        # Голы
        self.check_scoring()
        
        # Пауза
        if input_data.get("pause"):
            self.game_state["game_running"] = not self.game_state["game_running"]
    
    def check_paddle_collision(self):
        ball_x, ball_y = self.game_state["ball_x"], self.game_state["ball_y"]
        p1_y, p2_y = self.game_state["player1_y"], self.game_state["player2_y"]
        
        # Левая ракетка
        if (50 <= ball_x <= 60 and 
            p1_y - 50 <= ball_y <= p1_y + 50):
            self.game_state["ball_speed_x"] *= -1
            
        # Правая ракетка  
        if (740 <= ball_x <= 750 and 
            p2_y - 50 <= ball_y <= p2_y + 50):
            self.game_state["ball_speed_x"] *= -1
    
    def check_scoring(self):
        # Левый игрок пропустил
        if self.game_state["ball_x"] <= 0:
            self.game_state["player2_score"] += 1
            self.reset_ball()
            
        # Правый игрок пропустил  
        elif self.game_state["ball_x"] >= 800:
            self.game_state["player1_score"] += 1
            self.reset_ball()
            
        # Проверка победы
        if (self.game_state["player1_score"] >= self.winning_score or 
            self.game_state["player2_score"] >= self.winning_score):
            self.game_state["game_running"] = False
    
    def reset_ball(self):
        self.game_state["ball_x"] = 400
        self.game_state["ball_y"] = 300
        self.game_state["ball_speed_x"] *= -1  # Меняем направление
    
    def save_game_state(self):
        """Сохраняет состояние для C++"""
        with open('../shared/game_state.json', 'w') as f:
            json.dump(self.game_state, f, indent=2)
    
    def run(self):
        """Главный цикл Python логики"""
        while True:
            input_data = self.read_input()
            self.update_game(input_data)
            self.save_game_state()
            time.sleep(0.016)  # ~60 FPS

if name == "main":
    game = PongLogic()
    game.run()
