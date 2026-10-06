from settings import * 
from random import uniform
from support import draw_bar
from timer import Timer # type: ignore
from debug import global_profiler


# overworld sprites
class Sprite(pygame.sprite.Sprite):
	@global_profiler.profile_func()
	def __init__(self, position, surface, groups, z_layer = WORLD_LAYERS['main']):
		super().__init__(groups)
		# sprite setup
		self.image = surface
		self.original_image = surface
		self.scaled_cache = {}
		self.rect = self.image.get_frect(topleft = position)
		self.z = z_layer
		self.y_sort = self.rect.centery
		self.hitbox = self.rect.copy()

	@global_profiler.profile_func()
	def get_scaled_image(self, zoom):
		# image scaling
		if zoom not in self.scaled_cache:
			self.scaled_cache[zoom] = pygame.transform.scale(self.original_image, (int(self.original_image.get_width() * zoom), int(self.original_image.get_height() * zoom)))
		return self.scaled_cache[zoom]

class BorderSprite(Sprite):
	@global_profiler.profile_func()
	def __init__(self, position, surface, groups):
		super().__init__(position, surface, groups)
		self.hitbox = self.rect.copy()

class TransitionSprite(Sprite):
	@global_profiler.profile_func()
	def __init__(self, position, size, target_destination, groups):
		surf = pygame.Surface(size)
		super().__init__(position, surf, groups)
		self.target = target_destination

class CollidableSprite(Sprite):
	@global_profiler.profile_func()
	def __init__(self, position, surface, groups):
		super().__init__(position, surface, groups)
		self.hitbox = self.rect.inflate(0, -self.rect.height * 0.6)

class MonsterPatchSprite(Sprite):
	@global_profiler.profile_func()
	def __init__(self, position, surface, groups, biome, monster_names, base_level):
		# area setup
		self.biome = biome
		super().__init__(position, surface, groups, WORLD_LAYERS['main' if biome != 'sand' else 'bg'])
		self.y_sort -= MONSTER_PATCH_Y_OFFSET
		self.biome = biome
		self.monsters = monster_names.split(',')
		self.level = base_level

class AnimatedSprite(Sprite):
	@global_profiler.profile_func()
	def __init__(self, position, animation_frames, groups, z_layer = WORLD_LAYERS['main'], initial_surf = None):
		# animation setup
		self.frame_index, self.frames = 0, animation_frames
		super().__init__(position, initial_surf if initial_surf else animation_frames[self.frame_index], groups, z_layer)
		self.original_frames = animation_frames
		self.scaled_cache = {}

	@global_profiler.profile_func()
	def animate(self, dt):
		# loop over frames
		self.frame_index += ANIMATION_SPEED * dt
		self.image = self.frames[int(self.frame_index % len(self.frames))]

	@global_profiler.profile_func()
	def get_scaled_image(self, zoom):
		# check cache
		if zoom not in self.scaled_cache:
			if isinstance(self.original_frames, dict):
				# Handle dictionary of states (e.g., Player, NPCs)
				self.scaled_cache[zoom] = {}
				for state, frames in self.original_frames.items():
					self.scaled_cache[zoom][state] = [pygame.transform.scale(frame, (int(frame.get_width() * zoom), int(frame.get_height() * zoom))) for frame in frames]
			else:
				# Handle simple list of frames (e.g., water tiles)
				self.scaled_cache[zoom] = [pygame.transform.scale(frame, (int(frame.get_width() * zoom), int(frame.get_height() * zoom))) for frame in self.original_frames]

		# return scaled image
		if isinstance(self.original_frames, dict):
			return self.scaled_cache[zoom][self.get_state()][int(self.frame_index % len(self.frames[self.get_state()]))]
		else:
			return self.scaled_cache[zoom][int(self.frame_index % len(self.frames))]

	@global_profiler.profile_func()
	def update(self, delta_time, *args, **kwargs):
		self.animate(delta_time)

# battle sprites 
class MonsterSprite(pygame.sprite.Sprite):
	@global_profiler.profile_func()
	def __init__(self, position, animation_frames, groups, monster_object, monster_id, position_index, entity_type, apply_attack_callback, create_monster_callback):
		# data
		self.index = monster_id 
		self.pos_index = position_index
		self.entity = entity_type
		self.monster = monster_object
		self.frame_index, self.frames, self.state = 0, animation_frames, 'idle'
		self.animation_speed = ANIMATION_SPEED + uniform(-1, 1)
		self.z = BATTLE_LAYERS['monster']
		self.highlight = False
		self.target_sprite = None
		self.current_attack_name = None
		self.apply_attack = apply_attack_callback
		self.create_monster = create_monster_callback

		# sprite setup
		super().__init__(groups)
		self.image = self.frames[self.state][self.frame_index]
		self.rect = self.image.get_frect(center = position)

		# timers 
		self.timers = {
			'remove highlight': Timer(300, func = lambda: self.set_highlight(False)),
			'kill': Timer(600, func = self.destroy)
		}
		
		# pre-render highlight frames
		self.highlight_frames = {}
		for state, frame_list in self.frames.items():
			self.highlight_frames[state] = []
			for frame in frame_list:
				white_surf = pygame.mask.from_surface(frame).to_surface()
				white_surf.set_colorkey('black')
				self.highlight_frames[state].append(white_surf)

	@global_profiler.profile_func()
	def animate(self, delta_time):
		# loop over frames
		self.frame_index += ANIMATION_SPEED * delta_time
		if self.state == 'attack' and self.frame_index >= len(self.frames['attack']):
			self.apply_attack(self.target_sprite, self.current_attack_name, self.monster.get_base_damage(self.current_attack_name))
			self.state = 'idle'

		self.adjusted_frame_index = int(self.frame_index % len(self.frames[self.state]))
		if self.highlight:
			self.image = self.highlight_frames[self.state][self.adjusted_frame_index]
		else:
			self.image = self.frames[self.state][self.adjusted_frame_index]

	@global_profiler.profile_func()
	def set_highlight(self, value):
		# activate highlight
		self.highlight = value
		if value: 
			self.timers['remove highlight'].activate()

	@global_profiler.profile_func()
	def activate_attack(self, target_sprite, attack_name):
		self.state = 'attack'
		
		# reset animation
		self.frame_index = 0
		self.target_sprite = target_sprite
		self.current_attack_name = attack_name
		self.monster.reduce_energy(attack_name)

	@global_profiler.profile_func()
	def delayed_kill(self, replacement_monster_data):
		# start kill timer
		if not self.timers['kill'].active:
			self.next_monster_data = replacement_monster_data
			self.timers['kill'].activate()

	@global_profiler.profile_func()
	def destroy(self):
		if hasattr(self, 'next_monster_data') and self.next_monster_data:
			# create replacement
			self.create_monster(*self.next_monster_data)
		self.kill()

	@global_profiler.profile_func()
	def update(self, delta_time):
		for timer in self.timers.values():
			timer.update()
		self.animate(delta_time)
		self.monster.update(delta_time)

class MonsterOutlineSprite(pygame.sprite.Sprite):
	@global_profiler.profile_func()
	def __init__(self, monster_sprite, groups, frames):
		super().__init__(groups)
		self.z = BATTLE_LAYERS['outline']
		
		# sprite data
		self.monster_sprite = monster_sprite
		self.frames = frames

		self.image = self.frames[self.monster_sprite.state][self.monster_sprite.frame_index]
		self.rect = self.image.get_frect(center = self.monster_sprite.rect.center)

	@global_profiler.profile_func()
	def update(self, _):
		self.image = self.frames[self.monster_sprite.state][self.monster_sprite.adjusted_frame_index]
		
		# destroy outline
		if not self.monster_sprite.groups():
			self.kill()

class MonsterNameSprite(pygame.sprite.Sprite):
	@global_profiler.profile_func()
	def __init__(self, pos, monster_sprite, groups, font):
		super().__init__(groups)
		self.monster_sprite = monster_sprite
		self.z = BATTLE_LAYERS['name']

		# surface
		text_surf = font.render(monster_sprite.monster.name, False, COLORS['black'])
		padding = 10

		self.image = pygame.Surface((text_surf.get_width() + 2 * padding, text_surf.get_height() + 2 * padding)).convert()
		self.image.fill(COLORS['white'])
		self.image.blit(text_surf, (padding, padding))
		self.rect = self.image.get_frect(midtop = pos)

	@global_profiler.profile_func()
	def update(self, _):
		if not self.monster_sprite.groups():
			# destroy name
			self.kill()

class MonsterLevelSprite(pygame.sprite.Sprite):
	@global_profiler.profile_func()
	def __init__(self, entity, pos, monster_sprite, groups, font):
		super().__init__(groups)
		self.monster_sprite = monster_sprite
		self.font = font
		self.z = BATTLE_LAYERS['name']

		# surface
		self.image = pygame.Surface((60,26)).convert()
		self.rect = self.image.get_frect(topleft = pos) if entity == 'player' else self.image.get_frect(topright = pos)
		self.xp_rect = pygame.FRect(0,self.rect.height - 2,self.rect.width,2)
		
		# text cache
		self.cached_level = -1
		self.text_surf = None

	@global_profiler.profile_func()
	def update(self, _):
		self.image.fill(COLORS['white'])

		# update level
		if self.monster_sprite.monster.level != self.cached_level:
			self.cached_level = self.monster_sprite.monster.level
			self.text_surf = self.font.render(f'Lvl {self.cached_level}', False, COLORS['black'])

		text_rect = self.text_surf.get_frect(center = (self.rect.width / 2, self.rect.height / 2))
		self.image.blit(self.text_surf, text_rect)
		draw_bar(self.image, self.xp_rect, self.monster_sprite.monster.xp, self.monster_sprite.monster.level_up, COLORS['black'], COLORS['white'], 0)

		# destroy level
		if not self.monster_sprite.groups():
			self.kill()

class MonsterStatsSprite(pygame.sprite.Sprite):
	@global_profiler.profile_func()
	def __init__(self, pos, monster_sprite, size, groups, font):
		super().__init__(groups)
		self.monster_sprite = monster_sprite
		
		# surface
		self.image = pygame.Surface(size).convert()
		self.rect = self.image.get_frect(midbottom = pos)
		self.font = font
		self.z = BATTLE_LAYERS['overlay']
		
		# text cache
		self.cached_health = -1
		self.cached_energy = -1
		self.health_surf = None
		self.energy_surf = None

	@global_profiler.profile_func()
	def update(self, _):
		self.image.fill(COLORS['white'])

		# get stats
		for index, (value, max_value) in enumerate(self.monster_sprite.monster.get_info()):
			color = (COLORS['red'], COLORS['blue'], COLORS['gray'])[index]
			if index < 2: # health and energy 
				
				if index == 0: # health
					if int(value) != self.cached_health:
						self.cached_health = int(value)
						self.health_surf = self.font.render(f'{self.cached_health}/{max_value}', False, COLORS['black'])
					text_rect = self.health_surf.get_frect(topleft = (self.rect.width * 0.05, index * self.rect.height / 2))
					self.image.blit(self.health_surf, text_rect)
				
				else: # energy
					if int(value) != self.cached_energy:
						self.cached_energy = int(value)
						self.energy_surf = self.font.render(f'{self.cached_energy}/{max_value}', False, COLORS['black'])
					text_rect = self.energy_surf.get_frect(topleft = (self.rect.width * 0.05, index * self.rect.height / 2))
					self.image.blit(self.energy_surf, text_rect)

				bar_rect = pygame.FRect(text_rect.bottomleft + vector(0,-2), (self.rect.width * 0.9, 4))
				draw_bar(self.image, bar_rect, value, max_value, color, COLORS['black'], 2)
			
			else: # initiative
				init_rect = pygame.FRect((0, self.rect.height - 2), (self.rect.width, 2)) 
				draw_bar(self.image, init_rect, value, max_value, color, COLORS['white'], 0)

		# destroy stats
		if not self.monster_sprite.groups():
			self.kill()

class AttackSprite(AnimatedSprite):
	@global_profiler.profile_func()
	def __init__(self, pos, frames, groups):
		super().__init__(pos, frames, groups, BATTLE_LAYERS['overlay'])
		self.rect.center = pos

	@global_profiler.profile_func()
	def animate(self, dt):
		# loop over frames
		self.frame_index += ANIMATION_SPEED * dt
		
		if self.frame_index < len(self.frames):
			self.image = self.frames[int(self.frame_index)]
		else:
			self.kill()

	@global_profiler.profile_func()
	def update(self, dt):
		self.animate(dt)

class TimedSprite(Sprite):
	@global_profiler.profile_func()
	def __init__(self, pos, surf, groups, duration):
		
		# sprite setup
		super().__init__(pos, surf, groups, z = BATTLE_LAYERS['overlay'])
		self.rect.center = pos
		self.death_timer = Timer(duration, autostart = True, func = self.kill)

	@global_profiler.profile_func()
	def update(self, _):
		self.death_timer.update()