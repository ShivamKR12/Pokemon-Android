from settings import * 
from support import check_connections
from timer import Timer # type: ignore
from sprites import AnimatedSprite
from random import choice
from monster import Monster
from debug import global_profiler


class Entity(AnimatedSprite):
	@global_profiler.profile_func()
	def __init__(self, position, animation_frames, groups, facing_direction):
		self.facing_direction = facing_direction
		self.direction = vector() # must be before get_state
		initial_surf = animation_frames[self.get_state()][0]
		super().__init__(position, animation_frames, groups, initial_surf=initial_surf)
		self.rect.center = position # Center the rect after initialization

		# movement 
		self.speed = 250
		self.blocked = False
		self.hitbox = self.rect.inflate(-self.rect.width / 2, -60)
	
	@global_profiler.profile_func()
	def get_state(self):
		# get animation state
		if self.direction:
			if self.direction.x != 0:
				self.facing_direction = 'right' if self.direction.x > 0 else 'left'
			
			if self.direction.y != 0:
				self.facing_direction = 'down' if self.direction.y > 0 else 'up'
			
			return self.facing_direction
		
		else:
			return f"{self.facing_direction}_idle"

	@global_profiler.profile_func()
	def animate(self, delta_time):
		# loop over frames
		self.frame_index += ANIMATION_SPEED * delta_time
		self.image = self.frames[self.get_state()][int(self.frame_index % len(self.frames[self.get_state()]))]
		self.rect = self.image.get_frect(center = self.rect.center)

	@global_profiler.profile_func()
	def change_facing_direction(self, target_position):
		vector_to_target = vector(target_position) - vector(self.rect.center)
		
		# y direction
		if abs(vector_to_target.y) < 30:
			self.facing_direction = 'right' if vector_to_target.x > 0 else 'left'
		
		else:
			self.facing_direction = 'down' if vector_to_target.y > 0 else 'up'

	@global_profiler.profile_func()
	def block(self):
		# stop movement
		self.blocked = True
		self.direction = vector(0,0)

	@global_profiler.profile_func()
	def unblock(self):
		self.blocked = False

class Character(Entity):
	@global_profiler.profile_func()
	def __init__(self, position, animation_frames, groups, facing_direction, character_data, player, create_dialog, collision_sprites, notice_radius, is_nurse, notice_sound):
		super().__init__(position, animation_frames, groups, facing_direction)
		self.character_data = character_data
		self.player = player
		self.create_dialog = create_dialog
		self.collision_rects = [sprite.rect for sprite in collision_sprites if sprite is not self]
		self.is_nurse = is_nurse
		self.monsters = {i: Monster(name, lvl) for i, (name, lvl) in character_data['monsters'].items()} if 'monsters' in character_data else None

		# movement 
		self.has_moved = False
		self.can_rotate = True
		self.has_noticed = False
		self.notice_radius = int(notice_radius)
		self.view_directions = character_data['directions']

		self.timers = {
			'look around': Timer(1500, autostart = True, repeat = True, func = self.random_view_direction),
			'notice': Timer(500, func = self.start_move)
		}
		
		self.notice_sound = notice_sound

	@global_profiler.profile_func()
	def random_view_direction(self):
		if self.can_rotate:
			self.facing_direction = choice(self.view_directions)

	@global_profiler.profile_func()
	def get_dialog(self):
		return self.character_data['dialog'][f"{'defeated' if self.character_data['defeated'] else 'default'}"]

	@global_profiler.profile_func()
	def raycast(self):
		# check for player
		if check_connections(self.notice_radius, self, self.player) and self.has_los() and not self.has_moved and not self.has_noticed:
			self.player.block()
			self.player.change_facing_direction(self.rect.center)
			self.timers['notice'].activate()
			self.can_rotate = False
			self.has_noticed = True
			self.player.noticed = True
			self.notice_sound.play()

	@global_profiler.profile_func()
	def has_los(self):
		if vector(self.rect.center).distance_to(self.player.rect.center) < self.notice_radius:
			# check for obstacles
			return not any(rect.clipline(self.rect.center, self.player.rect.center) for rect in self.collision_rects)

	@global_profiler.profile_func()
	def start_move(self):
		if not self.player:
			return

		# move towards player
		vector_to_player = (vector(self.player.rect.center) - vector(self.rect.center)).normalize()
		self.direction = vector(round(vector_to_player.x), round(vector_to_player.y))

	@global_profiler.profile_func()
	def move(self, delta_time):
		if not self.has_moved and self.direction:
			if not self.hitbox.inflate(10,10).colliderect(self.player.hitbox):
				
				# move until collision
				self.rect.center += self.direction * self.speed * delta_time
				self.hitbox.center = self.rect.center
			
			else:
				self.direction = vector()
				self.has_moved = True
				self.create_dialog(self)
				self.player.noticed = False

	@global_profiler.profile_func()
	def update(self, delta_time, *args, **kwargs):
		for timer in self.timers.values():
			timer.update()

		# npc logic
		self.animate(delta_time)
		if self.character_data['look_around']:
			self.raycast()
			self.move(delta_time)

class Player(Entity):
	@global_profiler.profile_func()
	def __init__(self, position, animation_frames, groups, facing_direction, collision_sprites):
		super().__init__(position, animation_frames, groups, facing_direction)
		self.collision_sprites = collision_sprites
		self.noticed = False

	@global_profiler.profile_func()
	def input(self, input_state):
		# get input vector
		input_vector = vector()
		if input_state['up']:
			input_vector.y -= 1
		if input_state['down']:
			input_vector.y += 1
		if input_state['left']:
			input_vector.x -= 1
		if input_state['right']:
			input_vector.x += 1
		
		# normalize
		self.direction = input_vector.normalize() if input_vector else input_vector

	@global_profiler.profile_func()
	def move(self, delta_time):
		self.rect.centerx += self.direction.x * self.speed * delta_time
		self.hitbox.centerx = self.rect.centerx
		self.collisions('horizontal')

		self.rect.centery += self.direction.y * self.speed * delta_time
		self.hitbox.centery = self.rect.centery
		self.collisions('vertical')

	@global_profiler.profile_func()
	def collisions(self, axis):
		collided_sprites = pygame.sprite.spritecollide(self, self.collision_sprites, False, pygame.sprite.collide_rect)
		for sprite in collided_sprites:
			
			# check hitbox
			if sprite.hitbox.colliderect(self.hitbox):
				if axis == 'horizontal':
					
					if self.direction.x > 0: 
						self.hitbox.right = sprite.hitbox.left
					if self.direction.x < 0:
						self.hitbox.left = sprite.hitbox.right
					self.rect.centerx = self.hitbox.centerx
				
				else:
					if self.direction.y > 0:
						self.hitbox.bottom = sprite.hitbox.top
					if self.direction.y < 0:
						self.hitbox.top = sprite.hitbox.bottom
					self.rect.centery = self.hitbox.centery

	@global_profiler.profile_func()
	def update(self, delta_time, input_state):
		self.y_sort = self.rect.centery
		# movement and animation
		if not self.blocked:
			self.input(input_state)
			self.move(delta_time)
		self.animate(delta_time)
