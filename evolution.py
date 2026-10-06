from settings import * 
from timer import Timer # type: ignore
from debug import global_profiler


class Evolution:
	@global_profiler.profile_func()
	def __init__(self, all_monster_frames, start_monster_name, end_monster_name, evolution_font, end_evolution_callback, star_animation_frames):
		self.display_surface = pygame.display.get_surface()
		self.start_monster_surf = pygame.transform.scale2x(all_monster_frames['monsters'][start_monster_name]['idle'][0])
		self.end_monster_surf = pygame.transform.scale2x(all_monster_frames['monsters'][end_monster_name]['idle'][0])
		
		self.timers = {
			'start_delay': Timer(800, autostart = True),
			'end_delay': Timer(1800, func = end_evolution_callback)
		}

		# star animation
		self.star_frames = [pygame.transform.scale2x(frame) for frame in star_animation_frames]
		self.frame_index = 0

		# screen tint
		self.tint_surf = pygame.Surface(self.display_surface.get_size()).convert()
		self.tint_surf.set_alpha(200)

		# white tint
		self.start_monster_surf_white = pygame.transform.scale2x(all_monster_frames['white'][start_monster_name]['idle'][0])
		self.tint_amount, self.tint_speed = 0, EVOLUTION_TINT_SPEED
		self.start_monster_surf_white.set_alpha(self.tint_amount)

		# text 
		self.start_text_surf = evolution_font.render(f'{start_monster_name} is evolving', False, COLORS['black'])
		self.end_text_surf = evolution_font.render(f'{start_monster_name} evolved into {end_monster_name}', False, COLORS['black'])

	@global_profiler.profile_func()
	def display_stars(self, delta_time):
		self.frame_index += EVOLUTION_STAR_SPEED * delta_time
		if self.frame_index < len(self.star_frames):
			
			star_frame = self.star_frames[int(self.frame_index)]
			star_rect = star_frame.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
			self.display_surface.blit(star_frame, star_rect)

	@global_profiler.profile_func()
	def update(self, delta_time):
		for timer in self.timers.values():
			timer.update()

		# tint and text
		if not self.timers['start_delay'].active:
			self.display_surface.blit(self.tint_surf, (0,0))
			
			if self.tint_amount < 255:
				monster_rect = self.start_monster_surf.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
				
				# start monster
				self.display_surface.blit(self.start_monster_surf, monster_rect)

				self.tint_amount += self.tint_speed * delta_time
				self.start_monster_surf_white.set_alpha(self.tint_amount)
				self.display_surface.blit(self.start_monster_surf_white, monster_rect)

				text_rect = self.start_text_surf.get_frect(midtop = monster_rect.midbottom + vector(0,20))
				pygame.draw.rect(self.display_surface, COLORS['white'], text_rect.inflate(20,20), 0, 5)
				self.display_surface.blit(self.start_text_surf, text_rect)

			else:
				# end monster
				monster_rect = self.end_monster_surf.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
				self.display_surface.blit(self.end_monster_surf, monster_rect)
				
				text_rect = self.end_text_surf.get_frect(midtop = monster_rect.midbottom + vector(0,20))
				pygame.draw.rect(self.display_surface, COLORS['white'], text_rect.inflate(20,20), 0, 5)
				self.display_surface.blit(self.end_text_surf, text_rect)
				self.display_stars(delta_time)

				# end evolution
				if not self.timers['end_delay'].active:
					self.timers['end_delay'].activate()
