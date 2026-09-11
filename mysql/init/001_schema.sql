CREATE TABLE users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  email         VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  display_name  VARCHAR(64)  NOT NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE games (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  mode          ENUM('bot','pvp') NOT NULL,
  player1_id    INT NOT NULL,
  player2_id    INT NULL,
  status        ENUM('active','finished','resigned') NOT NULL DEFAULT 'active',
  state_json    JSON NOT NULL,
  winner        ENUM('player1','player2','draw') NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at   DATETIME NULL,
  FOREIGN KEY (player1_id) REFERENCES users(id),
  FOREIGN KEY (player2_id) REFERENCES users(id)
);

CREATE TABLE game_results (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  game_id         INT NOT NULL,
  user_id         INT NOT NULL,
  worms           INT NOT NULL,
  tiles_won       JSON NOT NULL,
  is_winner       BOOLEAN NOT NULL,
  best_turn_score INT NOT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (game_id) REFERENCES games(id),
  FOREIGN KEY (user_id) REFERENCES users(id)
);
