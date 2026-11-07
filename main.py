from os.path import join, dirname, abspath
from random import randint
from java import jclass

from settings import *
from game_data import *
from sprites import *
from entities import Player, Character
from groups import AllSprites
from dialog import DialogTree
from monster_index import MonsterIndex
from battle import Battle
from timer import Timer # type: ignore
from evolution import Evolution
from ui import JoyPad
from support import *
from debug import debug, global_profiler
from monster import Monster


BASE_DIR = dirname(abspath(__file__))

class Game:
	# general
	@global_profiler.profile_func()
	def __init__(self):
		pygame.init()
		self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.FULLSCREEN)
		self.clock = pygame.time.Clock()

		# timers
		self.dialog_cooldown = Timer(500)
		self.encounter_timer = Timer(2000, func = self.monster_encounter)

		# player monsters 
		self.player_monsters = {
			0: Monster('Ivieron', 32),
			1: Monster('Atrox', 15),
			2: Monster('Cindrill', 16),
			3: Monster('Atrox', 10),
			4: Monster('Sparchu', 11),
			5: Monster('Gulfin', 9),
			6: Monster('Jacana', 10),
		}

		# randomize xp
		for monster in self.player_monsters.values():
			monster.xp += randint(0,monster.level * 100)
		self.test_monsters = {
			0: Monster('Finsta', 15),
			1: Monster('Pouch', 13),
			2: Monster('Larvea', 12),
		}

		# groups 
		self.all_sprites = AllSprites(zoom = 2.0)
		self.collision_sprites = pygame.sprite.Group()
		self.character_sprites = pygame.sprite.Group()
		self.transition_sprites = pygame.sprite.Group()
		self.monster_sprites = pygame.sprite.Group()
		
		# transition / tint
		self.transition_target = None
		self.tint_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
		self.tint_mode = 'untint'
		self.tint_progress = 0
		self.tint_direction = -1
		self.tint_speed = 600

		# unified input
		self.input_state = {
			'up': False, 'down': False, 'left': False, 'right': False,
			'A': False, 'B': False, 'start': False, 'escape': False
		}
		self.just_pressed = self.input_state.copy()

		# initial setup
		self.import_assets()
		self.setup(self.tmx_maps['world'], 'house')
		self.audio['overworld'].play(-1)

		# overlays 
		self.dialog_tree = None
		self.monster_index = MonsterIndex(self.player_monsters, self.fonts, self.monster_frames)
		self.index_open = False
		self.battle = None
		self.evolution = None
		self.game_over = False
		self.joypad = JoyPad(self.fonts['big'])

	@global_profiler.profile_func()
	def import_assets(self):
		self.tmx_maps = tmx_importer('data', 'maps')

		self.overworld_frames = {
			'water': import_folder('graphics', 'tilesets', 'water'),
			'coast': coast_importer(24, 12, 'graphics', 'tilesets', 'coast'),
			'characters': all_character_import('graphics', 'characters')
		}

		self.monster_frames = {
			'icons': import_folder_dict('graphics', 'icons'),
			'monsters': monster_importer(4,2,'graphics', 'monsters'),
			'ui': import_folder_dict('graphics', 'ui'),
			'attacks': attack_importer('graphics', 'attacks')
		}
		self.monster_frames['outlines'] = outline_creator(self.monster_frames['monsters'], 4)
		self.monster_frames['white'] = {}
		
		for monster, data in self.monster_frames['monsters'].items():
			self.monster_frames['white'][monster] = {}
			
			for state, frames in data.items():
				self.monster_frames['white'][monster][state] = []
				
				for frame in frames:
					white_surf = pygame.mask.from_surface(frame).to_surface()
					white_surf.set_colorkey('black')
					self.monster_frames['white'][monster][state].append(white_surf)

		self.fonts = {
			'dialog': pygame.font.Font(join(BASE_DIR, 'graphics', 'fonts', 'PixeloidSans.ttf'), 30),
			'regular': pygame.font.Font(join(BASE_DIR, 'graphics', 'fonts', 'PixeloidSans.ttf'), 18),
			'small': pygame.font.Font(join(BASE_DIR, 'graphics', 'fonts', 'PixeloidSans.ttf'), 14),
            'big': pygame.font.Font(join(BASE_DIR, 'graphics', 'fonts', 'PixeloidSans.ttf'), 60),
			'bold': pygame.font.Font(join(BASE_DIR, 'graphics', 'fonts', 'dogicapixelbold.otf'), 20),
		}
		
		self.bg_frames = import_folder_dict('graphics', 'backgrounds')
		self.start_animation_frames = import_folder('graphics', 'other', 'star animation')

		# scale battle backgrounds
		for key, surf in self.bg_frames.items():
			self.bg_frames[key] = pygame.transform.scale(surf, (WINDOW_WIDTH, WINDOW_HEIGHT))

		# Pre-scale battle UI
		self.monster_frames['scaled_ui'] = {key: pygame.transform.scale_by(surf, 1.0) for key, surf in self.monster_frames['ui'].items()}
		self.monster_frames['scaled_icons'] = {key: pygame.transform.scale_by(surf, 1.0) for key, surf in self.monster_frames['icons'].items()}
	
		self.audio = audio_importer('audio')

	@global_profiler.profile_func()
	def setup(self, tmx_map, player_start_pos):
		# clear the map
		for group in (self.all_sprites, self.collision_sprites, self.transition_sprites, self.character_sprites):
			group.empty()

		# map background
		map_width = tmx_map.width * TILE_SIZE
		map_height = tmx_map.height * TILE_SIZE
		bg_surface = pygame.Surface((map_width, map_height)).convert()

		# terrain
		for layer in ['Terrain', 'Terrain Top']:
			for x, y, tile_surf in tmx_map.get_layer_by_name(layer).tiles():
				bg_surface.blit(tile_surf, (x * TILE_SIZE, y * TILE_SIZE))
		Sprite((0, 0), bg_surface, self.all_sprites, WORLD_LAYERS['bg'])

		# water 
		for water_obj in tmx_map.get_layer_by_name('Water'):
			for x in range(int(water_obj.x), int(water_obj.x + water_obj.width), TILE_SIZE):
				for y in range(int(water_obj.y), int(water_obj.y + water_obj.height), TILE_SIZE):
					AnimatedSprite((x,y), self.overworld_frames['water'], self.all_sprites, WORLD_LAYERS['water'])

		# coast
		for coast_obj in tmx_map.get_layer_by_name('Coast'):
			terrain_type = coast_obj.properties['terrain']
			side = coast_obj.properties['side']
			AnimatedSprite((coast_obj.x, coast_obj.y), self.overworld_frames['coast'][terrain_type][side], self.all_sprites, WORLD_LAYERS['bg'])
		
		# objects 
		for map_object in tmx_map.get_layer_by_name('Objects'):
			if map_object.name == 'top':
				Sprite((map_object.x, map_object.y), map_object.image, self.all_sprites, WORLD_LAYERS['top'])
			else:
				CollidableSprite((map_object.x, map_object.y), map_object.image, (self.all_sprites, self.collision_sprites))

		# transition objects
		for transition_obj in tmx_map.get_layer_by_name('Transition'):
			TransitionSprite((transition_obj.x, transition_obj.y), (transition_obj.width, transition_obj.height), (transition_obj.properties['target'], transition_obj.properties['pos']), self.transition_sprites)

		# collision objects 
		for collision_obj in tmx_map.get_layer_by_name('Collisions'):
			BorderSprite((collision_obj.x, collision_obj.y), pygame.Surface((collision_obj.width, collision_obj.height)), self.collision_sprites)

		# grass patches 
		for monster_patch in tmx_map.get_layer_by_name('Monsters'):
			MonsterPatchSprite((monster_patch.x, monster_patch.y), monster_patch.image, (self.all_sprites, self.monster_sprites), monster_patch.properties['biome'], monster_patch.properties['monsters'], monster_patch.properties['level'])

		# entities 
		for entity_obj in tmx_map.get_layer_by_name('Entities'):
			if entity_obj.name == 'Player':
				if entity_obj.properties['pos'] == player_start_pos:
					
					self.player = Player(
						position = (entity_obj.x + entity_obj.width / 2, entity_obj.y - entity_obj.height / 2), 
						animation_frames = self.overworld_frames['characters']['player'], 
						groups = self.all_sprites,
						facing_direction = entity_obj.properties['direction'], 
						collision_sprites = self.collision_sprites)
			
			else:
				Character(
					position = (entity_obj.x + entity_obj.width / 2, entity_obj.y - entity_obj.height / 2), 
					animation_frames = self.overworld_frames['characters'][entity_obj.properties['graphic']], 
					groups = (self.all_sprites, self.collision_sprites, self.character_sprites),
					facing_direction = entity_obj.properties.get('direction', 'down'),
					character_data = TRAINER_DATA[entity_obj.properties['character_id']],
					player = self.player,
					create_dialog = self.create_dialog,
					collision_sprites = self.collision_sprites,
					notice_radius = entity_obj.properties.get('radius', 100),
					is_nurse = entity_obj.properties['character_id'] == 'Nurse',
					notice_sound = self.audio['notice'])

	def input(self):
		# overworld input
		if not self.dialog_tree and not self.battle and not self.dialog_cooldown.active:
			if self.just_pressed['A']:
				for character in self.character_sprites:
					
					if check_connections(100, self.player, character):
						self.player.block()
						character.change_facing_direction(self.player.rect.center)
						self.create_dialog(character)
						character.can_rotate = False
			
			if self.just_pressed['start']:
				self.index_open = not self.index_open
				self.player.blocked = not self.player.blocked

	@global_profiler.profile_func()
	def create_dialog(self, character):
		if not self.dialog_tree:
			self.dialog_tree = DialogTree(character, self.player, self.all_sprites, self.fonts['dialog'], self.end_dialog, lambda: self.just_pressed)

	@global_profiler.profile_func()
	def end_dialog(self, character):
		self.dialog_tree = None
		self.dialog_cooldown.activate()
		
		# nurse behavior
		if character.is_nurse:
			for monster in self.player_monsters.values():
				monster.health = monster.get_stat('max_health')
				monster.energy = monster.get_stat('max_energy')

			self.player.unblock()
		
		# trainer battle
		elif not character.character_data['defeated']:
			pygame.mixer.pause()
			self.audio['battle'].stop()
			self.audio['battle'].play(-1)
			
			self.transition_target = Battle(
				player_monsters = self.player_monsters, 
				opponent_monsters = character.monsters, 
				monster_frames = self.monster_frames, 
				bg_surf = self.bg_frames[character.character_data['biome']], 
				fonts = self.fonts, 
				end_battle = self.end_battle, 
				get_input_state = lambda: (self.input_state, self.just_pressed),
				opponent_character = character, 
				sounds = self.audio)
			self.tint_mode = 'tint'
		
		# after defeat
		else:
			self.player.unblock()
			self.check_evolution()

	# transition system
	@global_profiler.profile_func()
	def transition_check(self):
		colliding_transition_sprites = [sprite for sprite in self.transition_sprites if sprite.rect.colliderect(self.player.hitbox)]
		if colliding_transition_sprites:
			self.player.block()
			self.transition_target = colliding_transition_sprites[0].target
			self.tint_mode = 'tint'

	@global_profiler.profile_func()
	def tint_screen(self, delta_time):
		if self.tint_progress == 0 and self.tint_mode == 'untint':
			return

		if self.tint_mode == 'untint':
			self.tint_progress -= self.tint_speed * delta_time

		if self.tint_mode == 'tint':
			self.tint_progress += self.tint_speed * delta_time
			
			# state change
			if self.tint_progress >= 255:
				if type(self.transition_target) == Battle:
					self.battle = self.transition_target
				
				elif self.transition_target == 'level':
					self.battle = None
				
				else:
					self.setup(self.tmx_maps[self.transition_target[0]], self.transition_target[1])
				
				self.tint_mode = 'untint'
				self.transition_target = None

		# apply tint
		self.tint_progress = max(0, min(self.tint_progress, 255))
		self.tint_surf.set_alpha(self.tint_progress)
		self.display_surface.blit(self.tint_surf, (0,0))
	
	@global_profiler.profile_func()
	def end_battle(self, opponent_character, was_wild_battle, forfeited=False, player_won=True):
		self.audio['battle'].stop()
		self.transition_target = 'level'
		self.tint_mode = 'tint'
		
		# game over
		if not player_won:
			self.game_over = True
		
		# forfeited
		elif forfeited:
			self.player.unblock()
			self.check_evolution()
		
		# won against trainer
		elif opponent_character:
			opponent_character.character_data['defeated'] = True
			self.create_dialog(opponent_character)
		
		# won against wild
		elif was_wild_battle:
			self.player.unblock()
			self.check_evolution()

	@global_profiler.profile_func()
	def draw_game_over(self):
		
		# background tint
		self.tint_surf.set_alpha(200)
		self.display_surface.blit(self.tint_surf, (0,0))

		# text
		game_over_text = self.fonts['bold'].render('Game Over', False, COLORS['white'])
		prompt_text = self.fonts['regular'].render('Press SPACE to close', False, COLORS['white'])
		game_over_rect = game_over_text.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 30))
		prompt_rect = prompt_text.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 30))

		self.display_surface.blit(game_over_text, game_over_rect)
		self.display_surface.blit(prompt_text, prompt_rect)

	@global_profiler.profile_func()
	def check_evolution(self):
		if self.evolution: # prevent multiple evolutions
			return

		for index, monster in self.player_monsters.items():
			if monster.evolution:
				if monster.level == monster.evolution[1]:
					
					self.audio['evolution'].play()
					self.player.block()
					self.evolution = Evolution(self.monster_frames, monster.name, monster.evolution[0], self.fonts['bold'], self.end_evolution, self.start_animation_frames)
					self.player_monsters[index] = Monster(monster.evolution[0], monster.level)
					return # one evolution at a time
		
		pygame.mixer.unpause() # Unpause only if no evolutions were found/started

	@global_profiler.profile_func()
	def end_evolution(self):
		self.evolution = None
		self.player.unblock()
		self.audio['evolution'].stop()
		self.check_evolution()

	# monster encounters 
	@global_profiler.profile_func()
	def check_monster(self):
		collided_sprite = pygame.sprite.spritecollideany(self.player, self.monster_sprites, collided=lambda p, s: p.hitbox.colliderect(s.rect))
		if collided_sprite and not self.battle and self.player.direction:
			if not self.encounter_timer.active:
				self.encounter_timer.activate()

	@global_profiler.profile_func()
	def monster_encounter(self):
		collided_sprite = pygame.sprite.spritecollideany(self.player, self.monster_sprites, collided=lambda p, s: p.hitbox.colliderect(s.rect))

		if not collided_sprite:
			return

		# start battle
		if collided_sprite and self.player.direction:
			self.encounter_timer.duration = randint(800, 2500)
			self.player.block()
			pygame.mixer.pause()
			self.audio['battle'].stop()
			self.audio['battle'].play(-1)
			
			self.transition_target = Battle(
				player_monsters = self.player_monsters, 
				opponent_monsters = {index:Monster(monster, collided_sprite.level + randint(-3,3)) for index, monster in enumerate(collided_sprite.monsters)}, 
				monster_frames = self.monster_frames, 
				bg_surf = self.bg_frames[collided_sprite.biome], 
				fonts = self.fonts, 
				end_battle = self.end_battle, 
				get_input_state = lambda: (self.input_state, self.just_pressed),
				opponent_character = None,
				sounds = self.audio)
			
			self.tint_mode = 'tint'

	@global_profiler.profile_func()
	def run(self):
		while True:
			delta_time = self.clock.tick() / 1000
			global_profiler.start_frame()
			self.display_surface.fill('black')

			# reset input
			for key in self.just_pressed:
				self.just_pressed[key] = False
			self.joypad.reset_just_pressed()

			# event loop 
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					global_profiler.save_report()
					pygame.quit()
					exit()
				if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
					self.joypad.process_input(event)

			# unified input processing
			keys = pygame.key.get_pressed()
			just_keys = pygame.key.get_just_pressed()

			self.input_state['up'] = keys[pygame.K_UP] or self.joypad.input_state['up']
			self.input_state['down'] = keys[pygame.K_DOWN] or self.joypad.input_state['down']
			self.input_state['left'] = keys[pygame.K_LEFT] or self.joypad.input_state['left']
			self.input_state['right'] = keys[pygame.K_RIGHT] or self.joypad.input_state['right']
			self.input_state['A'] = keys[pygame.K_SPACE] or self.joypad.input_state['A']
			self.input_state['B'] = (keys[pygame.K_ESCAPE] or keys[pygame.K_AC_BACK]) or self.joypad.input_state['B']
			self.input_state['start'] = keys[pygame.K_RETURN] or self.joypad.input_state['start']

			for key, just_key_code in [('up', pygame.K_UP), ('down', pygame.K_DOWN), ('left', pygame.K_LEFT), ('right', pygame.K_RIGHT), ('A', pygame.K_SPACE), ('start', pygame.K_RETURN), ('B', pygame.K_ESCAPE), ('B', pygame.K_AC_BACK)]:
				if just_keys[just_key_code] or self.joypad.just_pressed.get(key, False):
					self.just_pressed[key] = True

			# handle closing the game
			is_overlay_active = self.dialog_tree or self.battle or self.index_open or self.evolution
			if self.just_pressed['B'] and not is_overlay_active:
				if not self.player.blocked:
					global_profiler.save_report(directory = BASE_DIR)
					pygame.quit()
					exit()
			
			if self.game_over and self.just_pressed['A']:
				global_profiler.save_report()
				pygame.quit()
				exit()

			# update 
			with global_profiler.measure("Game_Update"):
				self.dialog_cooldown.update()
				
				# overworld updates
				if not self.battle:
					self.encounter_timer.update()
					self.input()
					self.transition_check()
					self.all_sprites.update(delta_time, self.input_state)
					self.check_monster()

			# drawing
			with global_profiler.measure("Game_Draw"):
				# overworld drawing
				if not self.battle:
					self.all_sprites.draw(self.player)
			
			# overlays
			with global_profiler.measure("Overlays"):
				if self.dialog_tree: self.dialog_tree.update()
				if self.index_open:  self.monster_index.update(delta_time, self.just_pressed)
				if self.battle:      self.battle.update(delta_time, self.joypad)
				if self.evolution:   self.evolution.update(delta_time)
				if self.game_over:   self.draw_game_over()
				self.joypad.draw()

			# debug info
			with global_profiler.measure("Debug_Draw"):
				debug(f'FPS: {int(self.clock.get_fps())}', x = 50)
				debug(f'Rendered Sprites: {self.all_sprites.rendered_sprite_count}', x = 50, y = 40)

			self.tint_screen(delta_time)
			global_profiler.end_frame()
			pygame.display.update()


if __name__ == '__main__':
	game = Game()
	game.run()
