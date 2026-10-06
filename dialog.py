from settings import * 
from timer import Timer # type: ignore
from sprites import Sprite
from debug import global_profiler


class DialogTree:
	@global_profiler.profile_func()
	def __init__(self, character, player, all_sprites, font, end_dialog, get_input):
		self.player = player
		self.character = character
		self.font = font 
		self.all_sprites = all_sprites
		self.end_dialog = end_dialog
		self.get_input = get_input
		
		self.dialog_lines = character.get_dialog()
		self.num_dialog_lines = len(self.dialog_lines)
		self.dialog_index = 0

		self.current_dialog_sprite = DialogSprite(self.dialog_lines[self.dialog_index], self.character, self.all_sprites, self.font)
		self.dialog_timer = Timer(500, autostart = True)

	@global_profiler.profile_func()
	def input(self):
		if self.get_input()['A'] and not self.dialog_timer.active:
			# advance dialog
			self.current_dialog_sprite.kill()
			self.dialog_index += 1
			
			if self.dialog_index < self.num_dialog_lines:
				# create new dialog
				self.current_dialog_sprite = DialogSprite(self.dialog_lines[self.dialog_index], self.character, self.all_sprites, self.font)
				self.dialog_timer.activate()
			
			else:
				self.end_dialog(self.character)

	@global_profiler.profile_func()
	def update(self):
		self.dialog_timer.update()
		self.input()

class DialogSprite(Sprite):
	@global_profiler.profile_func()
	def __init__(self, message, character, groups, font):

		# text 
		text_surf = font.render(message, False, COLORS['black'])
		padding = 5
		width = max(30, text_surf.get_width() + padding * 2)
		height = text_surf.get_height() + padding * 2

		# background
		background_surf = pygame.Surface((width, height), pygame.SRCALPHA).convert_alpha()
		background_surf.fill((0,0,0,0))
		pygame.draw.rect(background_surf, COLORS['pure white'], background_surf.get_frect(topleft = (0,0)),0, 4)
		background_surf.blit(text_surf, text_surf.get_frect(center = (width / 2, height / 2)))

		super().__init__(character.rect.midtop + vector(0,-10), background_surf, groups, WORLD_LAYERS['top'])
		self.rect.midbottom = character.rect.midtop + vector(0,-10)
