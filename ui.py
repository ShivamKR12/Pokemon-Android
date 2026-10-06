from settings import *
from debug import global_profiler


class Button(pygame.sprite.Sprite):
    @global_profiler.profile_func()
    def __init__(self, pos, surf, groups, key):
        super().__init__(groups)
        
        # sprite setup
        self.image = surf
        self.pressed_image = surf.copy()
        self.pressed_image.set_alpha(255)
        self.key = key
        self.rect = self.image.get_frect(center = pos)
        self.pressed = False

class JoyPad:
    @global_profiler.profile_func()
    def __init__(self, font):
        self.display_surface = pygame.display.get_surface()
        self.buttons = pygame.sprite.Group()
        self.font = font

        # button data
        button_data = {
            'up': {'pos': (WINDOW_WIDTH - 250, WINDOW_HEIGHT - 400)},
            'down': {'pos': (WINDOW_WIDTH - 250, WINDOW_HEIGHT - 100)},
            'left': {'pos': (WINDOW_WIDTH - 400, WINDOW_HEIGHT - 250)},
            'right': {'pos': (WINDOW_WIDTH - 100, WINDOW_HEIGHT - 250)},
            'A': {'pos': (300, WINDOW_HEIGHT - 150)},
            'B': {'pos': (150, WINDOW_HEIGHT - 350)},
            'start': {'pos': (WINDOW_WIDTH / 2, 50)},
        }

        self.last_touch_pos = None
        
        # button graphics
        arrow_surf = self.font.render('v', False, COLORS['white'])
        button_surfs = {
            'up': pygame.transform.rotate(arrow_surf, 180),
            'down': pygame.transform.rotate(arrow_surf, 0),
            'left': pygame.transform.rotate(arrow_surf, -90),
            'right': pygame.transform.rotate(arrow_surf, 90),
            'A': self.font.render('A', False, COLORS['white']),
            'B': self.font.render('B', False, COLORS['white']),
            'start': self.font.render('Menu', False, COLORS['white']),
        }

        # create buttons
        for key, data in button_data.items():
            text_surf = button_surfs[key]

            if key == 'start':
                # rectangular start button
                padding = 20
                width = text_surf.get_width() + padding * 2
                height = 60
                
                surf = pygame.Surface((width, height), pygame.SRCALPHA).convert_alpha()
                pygame.draw.rect(surf, (*pygame.Color(COLORS['dark'])[:3], 128), (0, 0, width, height), 0, 20) # Draw with 128 alpha
                text_rect = text_surf.get_frect(center = (width / 2, height / 2))
            
            else: 
                # circular buttons
                surf = pygame.Surface((200, 200), pygame.SRCALPHA).convert_alpha()
                pygame.draw.circle(surf, (*pygame.Color(COLORS['dark'])[:3], 128), (100, 100), 100) # Draw with 128 alpha
                text_rect = text_surf.get_frect(center = (100, 100))
            
            surf.blit(text_surf, text_rect)
            button_surf = surf
            Button(data['pos'], button_surf, self.buttons, key)

        # input state
        self.input_state = {
            'up': False, 'down': False, 'left': False, 'right': False,
            'A': False, 'B': False, 'start': False,
        }
        self.just_pressed = self.input_state.copy()

    @global_profiler.profile_func()
    def process_input(self, event):
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION):
            touch_pos = (event.x * WINDOW_WIDTH, event.y * WINDOW_HEIGHT)
            
            # check buttons
            self.last_touch_pos = touch_pos
            for button in self.buttons:
                if button.rect.collidepoint(touch_pos):
                    if not button.pressed:
                        button.pressed = True
                        self.input_state[button.key] = True
                        self.just_pressed[button.key] = True

        if event.type == pygame.FINGERUP:
            # reset all buttons
            for button in self.buttons:
                button.pressed = False
                self.input_state[button.key] = False
            self.last_touch_pos = None

    @global_profiler.profile_func()
    def reset_just_pressed(self):
        for key in self.just_pressed:
            self.just_pressed[key] = False

    @global_profiler.profile_func()
    def draw(self):
        for button in self.buttons:
            # pressed state
            if button.pressed:
                pos = button.rect.topleft + vector(2, 2)
                self.display_surface.blit(button.pressed_image, pos)
            else:
                self.display_surface.blit(button.image, button.rect)

    @global_profiler.profile_func()
    def update(self, event):
        self.process_input(event)
        self.draw()
