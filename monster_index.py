from settings import * 
from support import draw_bar
from game_data import MONSTER_DATA, ATTACK_DATA
from debug import global_profiler


class MonsterIndex:
	@global_profiler.profile_func()
	def __init__(self, monsters, fonts, monster_frames):
		self.display_surface = pygame.display.get_surface()
		self.fonts = fonts
		self.monsters = monsters
		self.frame_index = 0

		# frames 
		self.icon_frames = monster_frames['icons']
		self.monster_frames = monster_frames['monsters']
		self.ui_frames = monster_frames['ui']

		# tint surf 
		self.tint_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT)).convert()
		self.tint_surf.set_alpha(200)

		# dimensions 
		self.main_rect = pygame.FRect(0,0,WINDOW_WIDTH * 0.6,WINDOW_HEIGHT * 0.8).move_to(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))

		# list 
		self.visible_items = 6
		self.list_width = self.main_rect.width * 0.3
		self.item_height = self.main_rect.height / self.visible_items
		self.index = 0
		self.selected_index = None
		
		# abilities
		self.ability_surfs = []
		self.current_monster_id = -1

		# shadow surf
		self.shadow_surf = pygame.Surface((4, self.main_rect.height))
		self.shadow_surf.set_alpha(100)

		# max values 
		self.max_stats = {}
		for data in MONSTER_DATA.values():
			for stat, value in data['stats'].items():
				if stat != 'element':
					if stat not in self.max_stats:
						self.max_stats[stat] = value
					else:
						self.max_stats[stat] = value if value > self.max_stats[stat] else self.max_stats[stat]
		self.max_stats['health'] = self.max_stats.pop('max_health')
		self.max_stats['energy'] = self.max_stats.pop('max_energy')

		# pre-render static text
		self.stats_text_surf = self.fonts['regular'].render('Stats', False, COLORS['white'])
		self.ability_text_surf = self.fonts['regular'].render('Ability', False, COLORS['white'])

	@global_profiler.profile_func()
	def input(self, just_pressed):
		if not self.monsters:
			return

		# navigation
		if just_pressed['up']:
			self.index -= 1
		if just_pressed['down']:
			self.index += 1
		if just_pressed['A']:
			if self.selected_index != None:
				selected_monster = self.monsters[self.selected_index]
				
				# swap monsters
				current_monster  = self.monsters[self.index]
				self.monsters[self.index] = selected_monster
				self.monsters[self.selected_index] = current_monster
				self.selected_index = None
			
			else:
				self.selected_index = self.index

		# clamp index
		self.index = self.index % len(self.monsters)

	@global_profiler.profile_func()
	def display_list(self):
		# background
		bg_rect = pygame.FRect(self.main_rect.topleft,(self.list_width, self.main_rect.height))
		pygame.draw.rect(self.display_surface, COLORS['gray'], bg_rect,0,0,12,0,12,0)

		v_offset = 0 if self.index < self.visible_items else -(self.index - self.visible_items + 1) * self.item_height
		for index, monster in self.monsters.items():
			
			# colors 
			bg_color = COLORS['gray'] if self.index != index else COLORS['light']
			text_color = COLORS['white'] if self.selected_index != index else COLORS['gold']

			top = self.main_rect.top + index * self.item_height + v_offset
			item_rect = pygame.FRect(self.main_rect.left,top,self.list_width,self.item_height)
			
			text_surf = self.fonts['regular'].render(monster.name, False, text_color)
			text_rect = text_surf.get_frect(midleft = item_rect.midleft + vector(90, 0))

			icon_surf = self.icon_frames[monster.name]
			icon_rect = icon_surf.get_frect(center = item_rect.midleft + vector(45,0))

			# clipping
			if item_rect.colliderect(self.main_rect):
				
				# check corners
				if item_rect.collidepoint(self.main_rect.topleft):
					pygame.draw.rect(self.display_surface, bg_color, item_rect,0,0,12)
				
				elif item_rect.collidepoint(self.main_rect.bottomleft + vector(1,-1)):
					pygame.draw.rect(self.display_surface, bg_color, item_rect,0,0,0,0,12,0)
				
				else:
					pygame.draw.rect(self.display_surface, bg_color, item_rect)
				
				self.display_surface.blit(text_surf, text_rect)
				self.display_surface.blit(icon_surf, icon_rect)

		# lines 
		for i in range(1, min(self.visible_items, len(self.monsters))):
			y = self.main_rect.top + self.item_height * i
			left = self.main_rect.left
			right = self.main_rect.left + self.list_width
			pygame.draw.line(self.display_surface, COLORS['light-gray'], (left, y), (right, y))

		# shadow
		self.display_surface.blit(self.shadow_surf,(self.main_rect.left + self.list_width - 4,self.main_rect.top))
	
	@global_profiler.profile_func()
	def display_main(self, dt):
		# data 
		monster = self.monsters[self.index]
		
		# check for monster change to update ability surfaces
		if self.index != self.current_monster_id:
			self.ability_surfs.clear()
			# create new surfaces
			for ability in monster.get_abilities():
				element = ATTACK_DATA[ability]['element']
				text_surf = self.fonts['regular'].render(ability, False, COLORS['black'])
				bg_surf = pygame.Surface(vector(text_surf.get_size()) + vector(10,10), pygame.SRCALPHA)
				pygame.draw.rect(bg_surf, COLORS[element], bg_surf.get_frect(), 0, 4)
				bg_surf.blit(text_surf, (5,5))
				self.ability_surfs.append(bg_surf)
			self.current_monster_id = self.index

		# main bg
		main_panel_rect = pygame.FRect(self.main_rect.left + self.list_width,self.main_rect.top, self.main_rect.width - self.list_width, self.main_rect.height)
		pygame.draw.rect(self.display_surface, COLORS['dark'], main_panel_rect, 0, 12,0, 12,0)

		# monster display
		monster_display_rect = pygame.FRect(main_panel_rect.topleft, (main_panel_rect.width, main_panel_rect.height * 0.4))
		pygame.draw.rect(self.display_surface, COLORS[monster.element], monster_display_rect, 0,0,0,12)

		# monster animation 
		self.frame_index += ANIMATION_SPEED * dt
		monster_surf = self.monster_frames[monster.name]['idle'][int(self.frame_index) % len(self.monster_frames[monster.name]['idle'])]
		monster_rect = monster_surf.get_frect(center = monster_display_rect.center)
		self.display_surface.blit(monster_surf, monster_rect)

		# name 
		name_surf = self.fonts['bold'].render(monster.name, False, COLORS['white'])
		name_rect = name_surf.get_frect(topleft = monster_display_rect.topleft + vector(10,10))
		self.display_surface.blit(name_surf, name_rect)

		# level
		level_surf = self.fonts['regular'].render(f'Lvl: {monster.level}', False, COLORS['white'])
		level_rect = level_surf.get_frect(bottomleft = monster_display_rect.bottomleft + vector(10,-16))
		self.display_surface.blit(level_surf, level_rect)
		
		# xp
		draw_bar(
			surface = self.display_surface, 
			rect = pygame.FRect(level_rect.bottomleft, (100,4)), 
			value = monster.xp, 
			max_value = monster.level_up, 
			color = COLORS['white'], 
			bg_color = COLORS['dark']
		)

		# element
		element_surf = self.fonts['regular'].render(monster.element, False, COLORS['white'])
		element_rect = element_surf.get_frect(bottomright = monster_display_rect.bottomright + vector(-10,-10))
		self.display_surface.blit(element_surf, element_rect)

		# health and energy
		ui_bar_data = {
			'width': main_panel_rect.width * 0.45,
			'height': 30,
			'top': monster_display_rect.bottom + main_panel_rect.width * 0.03,
			'left_side': main_panel_rect.left + main_panel_rect.width / 4,
			'right_side': main_panel_rect.left + main_panel_rect.width * 3/4
		}

		# health
		healthbar_rect = pygame.FRect((0,0), (ui_bar_data['width'],ui_bar_data['height'])).move_to(midtop = (ui_bar_data['left_side'], ui_bar_data['top']))
		draw_bar(self.display_surface, healthbar_rect, monster.health, monster.get_stat('max_health'), COLORS['red'], COLORS['black'], 2)
		hp_text = self.fonts['regular'].render(f"HP: {int(monster.health)}/{int(monster.get_stat('max_health'))}", False, COLORS['white'])
		hp_rect = hp_text.get_frect(midleft = healthbar_rect.midleft + vector(10,0))
		self.display_surface.blit(hp_text, hp_rect)

		# energy
		energybar_rect = pygame.FRect((0,0), (ui_bar_data['width'],ui_bar_data['height'])).move_to(midtop = (ui_bar_data['right_side'], ui_bar_data['top']))
		draw_bar(self.display_surface, energybar_rect, monster.energy, monster.get_stat('max_energy'), COLORS['blue'], COLORS['black'], 2)
		ep_text = self.fonts['regular'].render(f"EP: {int(monster.energy)}/{int(monster.get_stat('max_energy'))}", False, COLORS['white'])
		ep_rect = ep_text.get_frect(midleft = energybar_rect.midleft + vector(10,0))
		self.display_surface.blit(ep_text, ep_rect)

		# info 
		info_panel_sides = {'left': healthbar_rect.left, 'right': energybar_rect.left}
		info_height = main_panel_rect.bottom - healthbar_rect.bottom

		# stats 
		stats_rect = pygame.FRect(info_panel_sides['left'], healthbar_rect.bottom, healthbar_rect.width, info_height).inflate(0,-60).move(0,15)
		stats_text_rect = self.stats_text_surf.get_frect(bottomleft = stats_rect.topleft)
		self.display_surface.blit(self.stats_text_surf, stats_text_rect)

		monster_stats = monster.get_stats()
		stat_height = stats_rect.height / len(monster_stats)

		for index, (stat, value) in enumerate(monster_stats.items()):
			single_stat_rect = pygame.FRect(stats_rect.left,stats_rect.top + index * stat_height,stats_rect.width,stat_height)

			# icon 
			icon_surf = self.ui_frames[stat]
			icon_rect = icon_surf.get_frect(midleft = single_stat_rect.midleft + vector(5,0))
			self.display_surface.blit(icon_surf, icon_rect)

			# text 
			text_surf = self.fonts['regular'].render(stat, False, COLORS['white'])
			text_rect = text_surf.get_frect(topleft = icon_rect.topleft + vector(30,-10))
			self.display_surface.blit(text_surf, text_rect)

			# bar 
			bar_rect = pygame.FRect((text_rect.left, text_rect.bottom + 2), (single_stat_rect.width  - (text_rect.left - single_stat_rect.left),4))
			draw_bar(self.display_surface, bar_rect, value, self.max_stats[stat] * monster.level, COLORS['white'], COLORS['black'])


		# abilities 
		ability_rect = stats_rect.copy().move_to(left = info_panel_sides['right'])
		ability_text_rect = self.ability_text_surf.get_frect(bottomleft = ability_rect.topleft)
		self.display_surface.blit(self.ability_text_surf, ability_text_rect)

		for index, surf in enumerate(self.ability_surfs):
			x = ability_rect.left + index % 2 * ability_rect.width / 2
			y = 20 + ability_rect.top + int(index / 2) * (surf.get_height() + 10)
			ability_icon_rect = surf.get_frect(topleft = (x,y))
			self.display_surface.blit(surf, ability_icon_rect)

	@global_profiler.profile_func()
	def update(self, dt, just_pressed):
		if not self.monsters:
			return

		# update and draw
		self.input(just_pressed)
		self.display_surface.blit(self.tint_surf, (0,0))
		self.display_list() 
		self.display_main(dt)
