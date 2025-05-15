import pygame
import math
import numpy # For sound generation

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (50, 50, 255)  # Player
BRIGHT_BLUE = (100,100,255) # Player accent
GREEN = (34, 139, 34) # Platforms
DARK_GREEN = (0, 100, 0) # Platform accent
BROWN = (160, 82, 45) # Ground
DARK_BROWN = (139, 69, 19) # Ground accent
SKY_BLUE = (135, 206, 250)
RED = (255, 0, 0) # Goal / simple enemy placeholder
YELLOW = (255, 255, 0) # Coin placeholder color
DARK_RED = (139,0,0) # For Game Over screen

# Player properties
PLAYER_WIDTH = 32 # Mario-esque proportions
PLAYER_HEIGHT = 48
PLAYER_ACC = 0.6  # Acceleration
PLAYER_FRICTION = -0.15 # Friction
PLAYER_GRAVITY = 0.9 # Gravity
PLAYER_JUMP_STRENGTH = -18 # Jump strength (negative for upward Y)
MAX_FALL_SPEED = 15 # Terminal velocity

# Platform properties
PLATFORM_THICKNESS = 20

# Sound properties (basic)
SAMPLE_RATE = 44100
FREQ_JUMP = 523.25  # C5 note (brighter jump sound)
DURATION_JUMP = 0.08 # seconds
FREQ_COIN = 1046.50 # C6 note (coin sound)
DURATION_COIN = 0.05 # seconds


# --- Helper Functions ---
def generate_sine_wave(frequency, duration, sample_rate, amplitude=0.6):
    """
    Generates a sine wave for sound effects with a quick fade-out.
    Args:
        frequency (float): Frequency of the sine wave in Hz.
        duration (float): Duration of the sound in seconds.
        sample_rate (int): Sampling rate in Hz.
        amplitude (float): Amplitude of the wave (0.0 to 1.0).
    Returns:
        pygame.mixer.Sound: A Pygame Sound object.
    """
    num_samples = int(sample_rate * duration)
    t = numpy.linspace(0, duration, num_samples, False)
    
    # Generate sine wave
    wave = numpy.sin(frequency * t * 2 * numpy.pi)
    
    # Apply a quick fade-out (envelope)
    envelope = numpy.exp(-numpy.linspace(0, 5, num_samples)) # Exponential decay
    wave *= envelope
    
    # Normalize and convert to 16-bit PCM
    audio = wave * amplitude * (2**15 - 1)
    audio = audio.astype(numpy.int16)
    
    # Create stereo audio (Pygame often prefers stereo)
    # Pygame's sndarray module expects a 2D array for stereo (num_samples, num_channels)
    stereo_audio = numpy.zeros((num_samples, 2), dtype=numpy.int16)
    stereo_audio[:, 0] = audio # Left channel
    stereo_audio[:, 1] = audio # Right channel (same as left for mono effect)
    
    return pygame.sndarray.make_sound(stereo_audio)

# --- Classes ---
class Player(pygame.sprite.Sprite):
    """
    Represents the player character.
    Handles movement, physics, and collision.
    """
    def __init__(self, initial_x, initial_y):
        super().__init__()
        self.image = pygame.Surface([PLAYER_WIDTH, PLAYER_HEIGHT], pygame.SRCALPHA) # Use SRCALPHA for transparency
        self.rect = self.image.get_rect()
        self.rect.x = initial_x
        self.rect.y = initial_y

        self.vel = pygame.math.Vector2(0, 0) # Velocity vector
        self.acc = pygame.math.Vector2(0, 0) # Acceleration vector (for clarity, though reset each frame)
        self.on_ground = False # Flag to check if player is on a platform

        self.is_moving_right = True # For player facing direction
        self.draw_player_shape() # Initial draw of the player

        # Load sounds
        try:
            self.jump_sound = generate_sine_wave(FREQ_JUMP, DURATION_JUMP, SAMPLE_RATE)
        except Exception as e:
            print(f"Could not initialize jump sound: {e}")
            self.jump_sound = None
        

    def draw_player_shape(self):
        """Draws a simple representation of the player. Called when direction changes."""
        self.image.fill((0,0,0,0)) # Transparent background
        # Body (e.g., overalls)
        pygame.draw.rect(self.image, BLUE, (0, PLAYER_HEIGHT * 0.3, PLAYER_WIDTH, PLAYER_HEIGHT * 0.7), border_radius=3)
        # Head (e.g., skin tone or hat color)
        pygame.draw.ellipse(self.image, BRIGHT_BLUE, (PLAYER_WIDTH * 0.1, 0, PLAYER_WIDTH * 0.8, PLAYER_HEIGHT * 0.4))
        # Simple eye (optional)
        eye_x = PLAYER_WIDTH * 0.65 if self.is_moving_right else PLAYER_WIDTH * 0.35 # Adjusted for better centering
        pygame.draw.circle(self.image, WHITE, (eye_x, PLAYER_HEIGHT * 0.2), 3)
        pupil_x_offset = 1 if self.is_moving_right else -1
        pygame.draw.circle(self.image, BLACK, (eye_x + pupil_x_offset, PLAYER_HEIGHT * 0.2 + 1), 1) # Pupil


    def jump(self):
        """Makes the player jump if on the ground."""
        if self.on_ground:
            self.vel.y = PLAYER_JUMP_STRENGTH
            if self.jump_sound:
                self.jump_sound.play()
            self.on_ground = False # Player is airborne after jumping

    def update(self, platforms, current_level_width):
        """
        Updates the player's state each frame.
        Args:
            platforms (pygame.sprite.Group): Group of platform sprites for collision.
            current_level_width (int): The total width of the current level.
        """
        # --- Horizontal Movement ---
        self.acc = pygame.math.Vector2(0, PLAYER_GRAVITY) # Reset acceleration, apply gravity
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.acc.x = -PLAYER_ACC
            if self.is_moving_right:
                self.is_moving_right = False
                self.draw_player_shape() # Redraw facing left
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.acc.x = PLAYER_ACC
            if not self.is_moving_right:
                self.is_moving_right = True
                self.draw_player_shape() # Redraw facing right

        # Apply friction to horizontal movement
        self.acc.x += self.vel.x * PLAYER_FRICTION
        
        # Update velocity based on acceleration (Euler integration)
        self.vel.x += self.acc.x
        # Limit horizontal speed (optional, but can prevent overly fast movement)
        # MAX_SPEED_X = 7 
        # if abs(self.vel.x) > MAX_SPEED_X: self.vel.x = numpy.sign(self.vel.x) * MAX_SPEED_X
        if abs(self.vel.x) < 0.1: # Stop very small movements to prevent drifting
            self.vel.x = 0
        
        # Update horizontal position
        self.rect.x += self.vel.x + 0.5 * self.acc.x # More accurate position update

        # Horizontal collision detection
        self.check_collision_x(platforms)

        # --- Vertical Movement ---
        self.vel.y += self.acc.y
        if self.vel.y > MAX_FALL_SPEED: # Terminal velocity
            self.vel.y = MAX_FALL_SPEED
            
        # Update vertical position
        self.rect.y += self.vel.y + 0.5 * self.acc.y # More accurate position update
        self.on_ground = False # Assume not on ground until collision check below
        
        # Vertical collision detection
        self.check_collision_y(platforms)

        # Prevent player from going off the left edge of the level
        if self.rect.left < 0:
            self.rect.left = 0
            self.vel.x = 0 # Stop movement at edge
        
        # Prevent player from going off the right edge of the level
        if self.rect.right > current_level_width:
            self.rect.right = current_level_width
            self.vel.x = 0 # Stop movement at edge


    def check_collision_x(self, platforms):
        """Checks and handles horizontal collisions with platforms."""
        collided_platforms = pygame.sprite.spritecollide(self, platforms, False)
        for platform in collided_platforms:
            if self.vel.x > 0: # Moving right, collided with left side of platform
                self.rect.right = platform.rect.left
            elif self.vel.x < 0: # Moving left, collided with right side of platform
                self.rect.left = platform.rect.right
            self.vel.x = 0 # Stop horizontal movement upon collision

    def check_collision_y(self, platforms):
        """Checks and handles vertical collisions with platforms."""
        collided_platforms = pygame.sprite.spritecollide(self, platforms, False)
        for platform in collided_platforms:
            if self.vel.y > 0: # Moving down (landing on top of platform)
                self.rect.bottom = platform.rect.top
                self.on_ground = True
                self.vel.y = 0
            elif self.vel.y < 0: # Moving up (hitting bottom of platform)
                self.rect.top = platform.rect.bottom
                self.vel.y = 0 # Stop upward movement

class Platform(pygame.sprite.Sprite):
    """Represents a static platform in the game."""
    def __init__(self, x, y, width, height, color=GREEN, accent_color=DARK_GREEN):
        super().__init__()
        self.image = pygame.Surface([width, height])
        self.image.fill(color)
        # Add a simple 3D effect/border
        pygame.draw.rect(self.image, accent_color, (0, 0, width, height), 3) # Border
        pygame.draw.line(self.image, WHITE, (2, 2), (width - 3, 2), 1) # Top highlight
        pygame.draw.line(self.image, WHITE, (2, 2), (2, height - 3), 1) # Left highlight
        
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

class Coin(pygame.sprite.Sprite):
    """Represents a collectible coin."""
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface([15, 15], pygame.SRCALPHA)
        pygame.draw.circle(self.image, YELLOW, (7, 7), 7) # Outer coin
        pygame.draw.circle(self.image, (200,200,0), (7,7), 5) # Inner darker circle for depth
        pygame.draw.circle(self.image, (255,223,0), (7,7), 3, 1) # Shine/detail
        self.rect = self.image.get_rect(center=(x,y))
        try:
            self.collect_sound = generate_sine_wave(FREQ_COIN, DURATION_COIN, SAMPLE_RATE, amplitude=0.4)
        except Exception as e:
            print(f"Could not initialize coin sound: {e}")
            self.collect_sound = None

    def play_collect_sound(self):
        if self.collect_sound:
            self.collect_sound.play()

class Level:
    """
    Manages the platforms, items, and overall structure of a single level.
    """
    def __init__(self, player_ref):
        self.platforms = pygame.sprite.Group()
        self.coins = pygame.sprite.Group()
        self.goal = None # Will be a sprite or rect
        self.all_sprites = pygame.sprite.Group() # For drawing everything except player
        
        self.player = player_ref # Reference to the player object
        
        self.world_shift = 0 # Camera horizontal shift
        self.level_width = 0 # Total width of the level in pixels
        
        # Attempt to use a more game-like font if available, fallback to Arial
        try:
            self.font = pygame.font.Font(None, 30) # Default Pygame font
        except:
            self.font = pygame.font.SysFont("Arial", 24, bold=True) 
        self.score = 0

        # Define level data here
        self.load_level_data(self.get_world_1_1_data()) 

    def get_world_1_1_data(self):
        """
        Defines the layout for World 1-1.
        Format: list of tuples.
        Platform: ('platform', x, y, width, height, [color], [accent_color])
        Coin: ('coin', x, y)
        Goal: ('goal', x, y, width, height)
        """
        data = [
            # Ground sections
            ('platform', 0, SCREEN_HEIGHT - PLATFORM_THICKNESS, 600, PLATFORM_THICKNESS, BROWN, DARK_BROWN),
            ('platform', 700, SCREEN_HEIGHT - PLATFORM_THICKNESS, 400, PLATFORM_THICKNESS, BROWN, DARK_BROWN),
            ('platform', 1200, SCREEN_HEIGHT - PLATFORM_THICKNESS, 800, PLATFORM_THICKNESS, BROWN, DARK_BROWN),

            # Floating platforms
            ('platform', 200, SCREEN_HEIGHT - PLATFORM_THICKNESS * 5, 100, PLATFORM_THICKNESS),
            ('platform', 350, SCREEN_HEIGHT - PLATFORM_THICKNESS * 8, 100, PLATFORM_THICKNESS),
            ('platform', 550, SCREEN_HEIGHT - PLATFORM_THICKNESS * 6, 150, PLATFORM_THICKNESS),
            
            # Coins for World 1-1
            ('coin', 225, SCREEN_HEIGHT - PLATFORM_THICKNESS * 6 - 15), # Adjusted Y for better visual placement
            ('coin', 375, SCREEN_HEIGHT - PLATFORM_THICKNESS * 9 - 15),
            ('coin', 575, SCREEN_HEIGHT - PLATFORM_THICKNESS * 7 - 15),
            ('coin', 600, SCREEN_HEIGHT - PLATFORM_THICKNESS * 7 - 15),
            ('coin', 625, SCREEN_HEIGHT - PLATFORM_THICKNESS * 7 - 15),

            # More platforms after a gap
            ('platform', 800, SCREEN_HEIGHT - PLATFORM_THICKNESS * 4, 120, PLATFORM_THICKNESS),
            ('platform', 1000, SCREEN_HEIGHT - PLATFORM_THICKNESS * 5, 120, PLATFORM_THICKNESS),
            
            ('coin', 830, SCREEN_HEIGHT - PLATFORM_THICKNESS * 5 - 15),
            ('coin', 1030, SCREEN_HEIGHT - PLATFORM_THICKNESS * 6 - 15),

            # Final section and goal
            ('platform', 1700, SCREEN_HEIGHT - PLATFORM_THICKNESS * 3, 100, PLATFORM_THICKNESS),
            ('goal', 1950, SCREEN_HEIGHT - PLATFORM_THICKNESS * 6, 30, PLATFORM_THICKNESS * 5) # Goal post
        ]
        return data

    def load_level_data(self, level_data):
        """
        Processes the level data to create sprites.
        Args:
            level_data (list): A list containing the definitions for platforms, coins, etc.
        """
        self.platforms.empty()
        self.coins.empty()
        self.all_sprites.empty()
        self.goal = None
        
        max_x = 0
        for item in level_data:
            item_type = item[0]
            if item_type == 'platform':
                _, x, y, w, h, *colors = item
                color = colors[0] if colors else GREEN
                accent = colors[1] if len(colors) > 1 else DARK_GREEN
                platform = Platform(x, y, w, h, color, accent)
                self.platforms.add(platform)
                self.all_sprites.add(platform)
                if x + w > max_x: max_x = x + w
            elif item_type == 'coin':
                _, x, y = item
                coin = Coin(x,y)
                self.coins.add(coin)
                self.all_sprites.add(coin)
                if x > max_x: max_x = x 
            elif item_type == 'goal':
                _, x, y, w, h = item
                # The goal is also a "platform" visually but with different color and purpose
                self.goal = Platform(x,y,w,h, RED, (150,0,0)) 
                self.all_sprites.add(self.goal) # Add goal to all_sprites for drawing
                if x + w > max_x: max_x = x + w
        
        self.level_width = max_x
        # Reset player to start of level
        self.player.rect.x = 50
        self.player.rect.y = SCREEN_HEIGHT - PLATFORM_THICKNESS * 2 - PLAYER_HEIGHT # Start on first ground platform
        self.player.vel = pygame.math.Vector2(0,0)
        self.player.on_ground = False # Ensure player checks for ground again
        self.world_shift = 0 # Reset camera
        self.score = 0


    def update(self):
        """Updates all level elements, including player and camera."""
        self.player.update(self.platforms, self.level_width) 
        self.scroll_camera()
        # self.all_sprites.update() # Only needed if platforms/coins have their own update logic (e.g., animation)

        # Check for coin collection
        collected_coins = pygame.sprite.spritecollide(self.player, self.coins, True) # True to remove coin
        for coin in collected_coins:
            self.score += 100
            coin.play_collect_sound()
            # The coin is removed from self.coins group and also from self.all_sprites if it was added there.
            # pygame.sprite.Group.remove() is called internally by spritecollide if dokill=True.

        # Check for goal
        if self.goal and self.player.rect.colliderect(self.goal.rect):
            return "WIN"
        
        # Check for fall (death)
        if self.player.rect.top > SCREEN_HEIGHT + PLAYER_HEIGHT: # Fallen off screen
            return "LOSE"

        return None # Game continues

    def draw(self, screen):
        """Draws the level, including background, sprites, and UI."""
        screen.fill(SKY_BLUE) # Background

        # Draw all sprites (shifted by camera)
        for sprite in self.all_sprites:
            screen.blit(sprite.image, sprite.rect.move(self.world_shift, 0))
        
        # Draw player separately (can be on top of other things if needed, or managed by group draw order)
        screen.blit(self.player.image, self.player.rect.move(self.world_shift, 0))

        # Draw Score
        score_text_surface = self.font.render(f"Score: {self.score}", True, WHITE)
        screen.blit(score_text_surface, (10, 10))
        
        # Draw Level Name (placeholder)
        level_name_surface = self.font.render("World 1-1", True, WHITE)
        screen.blit(level_name_surface, (SCREEN_WIDTH - level_name_surface.get_width() - 10, 10))


    def scroll_camera(self):
        """Adjusts the world_shift to keep the player centered, creating a scrolling effect."""
        # Scroll right: if player is past 60% of screen width AND moving right
        # CORRECTED: Use self.player.vel.x instead of self.vel.x
        if self.player.rect.right > SCREEN_WIDTH * 0.6 and self.player.vel.x > 0:
            shift = self.player.rect.right - (SCREEN_WIDTH * 0.6)
            self.player.rect.x -= shift # Keep player effectively at the 60% mark
            self.world_shift -= shift   # Move the world left
        
        # Scroll left: if player is before 40% of screen width AND moving left
        # CORRECTED: Use self.player.vel.x instead of self.vel.x
        if self.player.rect.left < SCREEN_WIDTH * 0.4 and self.player.vel.x < 0:
            shift = (SCREEN_WIDTH * 0.4) - self.player.rect.left
            self.player.rect.x += shift # Keep player effectively at the 40% mark
            self.world_shift += shift   # Move the world right

        # Clamp camera to level boundaries
        # Prevent scrolling beyond the start of the level (world_shift should not be positive)
        if self.world_shift > 0:
            self.world_shift = 0
        
        # Prevent scrolling beyond the end of the level
        # The rightmost point the camera should show is level_width.
        # So, the leftmost point of the camera (world_shift) is -(level_width - SCREEN_WIDTH)
        if self.level_width > SCREEN_WIDTH: # Only if level is wider than screen
            if self.world_shift < -(self.level_width - SCREEN_WIDTH):
                self.world_shift = -(self.level_width - SCREEN_WIDTH)
        else: # Level is narrower than or same width as screen, no scrolling needed, or center it
            self.world_shift = 0


    def reset_level(self):
        """Resets the player's position and other level states for a new attempt."""
        # Re-create sprites and reset positions by reloading level data
        self.load_level_data(self.get_world_1_1_data()) # Reload the current level's data
        # Player position, velocity, score etc. are reset within load_level_data

# --- Game States ---
STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_GAME_OVER = "game_over"
STATE_WIN = "win"
# STATE_LEVEL_TRANSITION = "level_transition" # For future use

def main_game_loop():
    """Main function to initialize and run the game."""
    pygame.init()
    
    # Attempt to initialize mixer with common parameters
    try:
        pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
        print("Pygame mixer initialized successfully.")
        pygame.mixer.set_num_channels(16) # Allow more simultaneous sounds
    except pygame.error as e:
        print(f"Failed to initialize pygame.mixer: {e}. Sound effects may be limited or disabled.")

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Platformer Adventure - World 1")
    clock = pygame.time.Clock()

    # Create player instance
    # Initial position doesn't matter as much here, Level.load_level_data will set it.
    player = Player(50, SCREEN_HEIGHT - PLATFORM_THICKNESS * 2 - PLAYER_HEIGHT) 
    
    level_manager = Level(player) # Manages current level's state and objects

    game_state = STATE_MENU 
    
    # Fonts for menu and messages
    try:
        title_font = pygame.font.Font(None, 74) # Default Pygame font, larger
        menu_font = pygame.font.Font(None, 48)  # Default Pygame font, medium
    except:
        title_font = pygame.font.SysFont("Arial", 60, bold=True)
        menu_font = pygame.font.SysFont("Arial", 30)


    running = True
    while running:
        # dt = clock.tick(FPS) / 1000.0 # Delta time in seconds, useful for frame-rate independent physics

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if game_state == STATE_PLAYING:
                    if event.key == pygame.K_SPACE or event.key == pygame.K_UP or event.key == pygame.K_w:
                        player.jump()
                    if event.key == pygame.K_ESCAPE: 
                        game_state = STATE_MENU 
                elif game_state == STATE_MENU:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        level_manager.reset_level() # Ensure level is fresh
                        game_state = STATE_PLAYING
                    if event.key == pygame.K_ESCAPE:
                        running = False # Exit from menu
                elif game_state == STATE_GAME_OVER or game_state == STATE_WIN:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        game_state = STATE_MENU # Go back to menu
                        # Optional: if win, could go to next level instead of menu
                    if event.key == pygame.K_ESCAPE:
                         running = False # Allow exit from these screens too
                        

        # --- Game State Logic ---
        if game_state == STATE_MENU:
            screen.fill(BLACK)
            title_text_surface = title_font.render("Platformer Adventure", True, WHITE)
            start_text_surface = menu_font.render("Press ENTER or SPACE to Start", True, WHITE)
            exit_text_surface = menu_font.render("Press ESCAPE to Exit", True, WHITE)
            
            screen.blit(title_text_surface, (SCREEN_WIDTH // 2 - title_text_surface.get_width() // 2, SCREEN_HEIGHT // 3 - title_text_surface.get_height() // 2))
            screen.blit(start_text_surface, (SCREEN_WIDTH // 2 - start_text_surface.get_width() // 2, SCREEN_HEIGHT // 2))
            screen.blit(exit_text_surface, (SCREEN_WIDTH // 2 - exit_text_surface.get_width() // 2, SCREEN_HEIGHT // 2 + 50))

        elif game_state == STATE_PLAYING:
            game_status = level_manager.update() # Update level, player, camera
            if game_status == "WIN":
                game_state = STATE_WIN
            elif game_status == "LOSE":
                game_state = STATE_GAME_OVER
            
            level_manager.draw(screen) # Draw the current state of the level

        elif game_state == STATE_GAME_OVER:
            screen.fill(DARK_RED) 
            msg_text_surface = title_font.render("GAME OVER", True, WHITE)
            restart_text_surface = menu_font.render("Press ENTER to return to Menu", True, WHITE)
            
            screen.blit(msg_text_surface, (SCREEN_WIDTH // 2 - msg_text_surface.get_width() // 2, SCREEN_HEIGHT // 3 - msg_text_surface.get_height()//2))
            screen.blit(restart_text_surface, (SCREEN_WIDTH // 2 - restart_text_surface.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

        elif game_state == STATE_WIN:
            screen.fill(DARK_GREEN) 
            msg_text_surface = title_font.render("LEVEL COMPLETE!", True, WHITE)
            next_text_surface = menu_font.render("Press ENTER to return to Menu", True, WHITE)
            final_score_surface = menu_font.render(f"Final Score: {level_manager.score}", True, WHITE)

            screen.blit(msg_text_surface, (SCREEN_WIDTH // 2 - msg_text_surface.get_width() // 2, SCREEN_HEIGHT // 3 - msg_text_surface.get_height()//2 - 20))
            screen.blit(final_score_surface, (SCREEN_WIDTH // 2 - final_score_surface.get_width() // 2, SCREEN_HEIGHT // 2))
            screen.blit(next_text_surface, (SCREEN_WIDTH // 2 - next_text_surface.get_width() // 2, SCREEN_HEIGHT // 2 + 50))
        
        pygame.display.flip() # Update the full display
        clock.tick(FPS) # Control the frame rate

    pygame.quit()

if __name__ == '__main__':
    main_game_loop()
