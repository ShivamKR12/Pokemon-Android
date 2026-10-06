from settings import * 
from support import import_image
from entities import Entity
from debug import global_profiler


class AllSprites(pygame.sprite.Group):
	@global_profiler.profile_func()
	def __init__(self, zoom = 1.0):
		super().__init__()
		
		self.display_surface = pygame.display.get_surface()
		self.offset = vector()
		self.zoom = zoom
		
		self.shadow_surf = import_image('graphics', 'other', 'shadow')
		self.notice_surf = import_image('graphics', 'ui', 'notice')
		
		self.camera_rect = self.display_surface.get_frect()
		
		self.shadow_cache = {}
		self.notice_cache = {}
		
		self.rendered_sprite_count = 0

	@global_profiler.profile_func()
	def draw(self, player):
		self.rendered_sprite_count = 0 # reset count
		
		# calculate the camera
		self.offset = vector(player.rect.center) - vector(WINDOW_WIDTH / 2 / self.zoom, WINDOW_HEIGHT / 2 / self.zoom)
		shadow_offset = vector(40, 110) * self.zoom

		bg_sprites = [sprite for sprite in self if sprite.z < WORLD_LAYERS['main']]
		main_sprites = sorted([sprite for sprite in self if sprite.z == WORLD_LAYERS['main']], key = lambda sprite: sprite.y_sort)
		fg_sprites = [sprite for sprite in self if sprite.z > WORLD_LAYERS['main']]

		for layer in (bg_sprites, main_sprites, fg_sprites):
			# y-sort
			for sprite in layer:
				cull_rect = pygame.FRect(0,0, sprite.rect.width * self.zoom, sprite.rect.height * self.zoom)
				cull_rect.center = (vector(sprite.rect.center) - self.offset) * self.zoom

				if self.camera_rect.colliderect(cull_rect):
					self.rendered_sprite_count += 1

					scaled_image = sprite.get_scaled_image(self.zoom)
					scaled_rect = scaled_image.get_frect(center = cull_rect.center)

					# shadow
					if isinstance(sprite, Entity):
						if self.zoom not in self.shadow_cache:
							scaled_shadow_size = (int(self.shadow_surf.get_width() * self.zoom), int(self.shadow_surf.get_height() * self.zoom))
							self.shadow_cache[self.zoom] = pygame.transform.scale(self.shadow_surf, scaled_shadow_size)
						
						scaled_shadow = self.shadow_cache[self.zoom]
						shadow_pos = scaled_rect.topleft + shadow_offset
						self.display_surface.blit(scaled_shadow, shadow_pos)

					self.display_surface.blit(scaled_image, scaled_rect)

					# notice icon
					if sprite == player and player.noticed:
						if self.zoom not in self.notice_cache:
							
							scaled_notice_size = (int(self.notice_surf.get_width() * self.zoom), int(self.notice_surf.get_height() * self.zoom))
							self.notice_cache[self.zoom] = pygame.transform.scale(self.notice_surf, scaled_notice_size)
						
						scaled_notice = self.notice_cache[self.zoom]
						notice_rect = scaled_notice.get_frect(midbottom = scaled_rect.midtop)
						self.display_surface.blit(scaled_notice, notice_rect)

class BattleSprites(pygame.sprite.Group):
	@global_profiler.profile_func()
	def __init__(self):
		super().__init__()
		self.display_surface = pygame.display.get_surface()

	@global_profiler.profile_func()
	def draw(self, current_monster_sprite, side, mode, target_index, player_sprites, opponent_sprites):
		# get available positions 
		sprite_group = opponent_sprites if side == 'opponent' else player_sprites
		sprites = {sprite.pos_index: sprite for sprite in sprite_group}
		monster_sprite = sprites[list(sprites.keys())[target_index]] if sprites else None

		for sprite in sorted(self, key = lambda sprite: sprite.z):
			# outline condition
			if sprite.z == BATTLE_LAYERS['outline']:
				
				if sprite.monster_sprite == current_monster_sprite and not (mode == 'target' and side == 'player') or\
				   sprite.monster_sprite == monster_sprite and sprite.monster_sprite.entity == side and mode and mode == 'target':
					self.display_surface.blit(sprite.image, sprite.rect)
			
			else:
				self.display_surface.blit(sprite.image, sprite.rect)
