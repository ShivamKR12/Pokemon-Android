from settings import * 
from sprites import *
from groups import BattleSprites
from game_data import ATTACK_DATA
from support import draw_bar
from timer import Timer # type: ignore
from random import choice
from itertools import chain
from debug import global_profiler


class Battle:
	# main
	@global_profiler.profile_func()
	def __init__(self, player_monsters, opponent_monsters, monster_frames, bg_surf, fonts, end_battle, opponent_character, sounds, get_input_state):
		# general
		self.display_surface = pygame.display.get_surface()
		self.bg_surf = bg_surf
		self.monster_frames = monster_frames
		self.fonts = fonts # player_monsters is a dict of Monster objects, opponent_monsters is a dict of (name, level) tuples
		self.monster_data = {'player': player_monsters.copy(), 'opponent': opponent_monsters.copy()}
		self.get_input_state = get_input_state
		self.battle_over = False
		self.end_battle = end_battle
		self.opponent_character = opponent_character
		self.sounds = sounds
		self.scale = 1.0

		# timers 
		self.timers = {
			'opponent delay': Timer(600, func = self.opponent_attack)
		}

		# groups
		self.battle_sprites   = BattleSprites()
		self.player_sprites   = pygame.sprite.Group()
		self.opponent_sprites = pygame.sprite.Group()

		# control
		self.current_monster = None
		self.selection_mode  = None
		self.selected_attack = None
		self.selection_side  = 'player'
		self.indexes = {
			'general': 0,
			'monster': 0,
			'attacks': 0,
			'switch' : 0,
			'target' : 0,
		}

		# ui rects for touch input
		self.ui_rects = {}
		self.available_monsters = {}

		self.setup()

	@global_profiler.profile_func()
	def setup(self):
		for entity_type, monster_party in self.monster_data.items():
			if entity_type == 'player':
				healthy_monsters = {monster_id:monster_object for monster_id,monster_object in monster_party.items() if monster_object.health > 0}
				for position_index, (monster_id, monster_object) in enumerate(healthy_monsters.items()):
					if position_index <= 2:
						self.create_monster(monster_object, monster_id, position_index, entity_type)
			else:
				for monster_id, monster_object in {monster_id:monster_object for monster_id,monster_object in monster_party.items() if monster_id <= 2}.items():
					self.create_monster(monster_object, monster_id, monster_id, entity_type)
			# remove opponent monster data 
			for i in range(len(self.opponent_sprites)):
				del self.monster_data['opponent'][i]

	@global_profiler.profile_func()
	def create_monster(self, monster_object, monster_id, position_index, entity_type):
		# flip frames
		monster_object.paused = False
		if entity_type == 'player':
			animation_frames = {state: [pygame.transform.flip(frame, True, False) for frame in frame_list] for state, frame_list in self.monster_frames['monsters'][monster_object.name].items()}
			outline_frames = {state: [pygame.transform.flip(frame, True, False) for frame in frame_list] for state, frame_list in self.monster_frames['outlines'][monster_object.name].items()}
			position = list(BATTLE_POSITIONS['left'].values())[position_index]
			groups = (self.battle_sprites, self.player_sprites)
		else:
			# original frames
			animation_frames = self.monster_frames['monsters'][monster_object.name]
			outline_frames = self.monster_frames['outlines'][monster_object.name]
			position = list(BATTLE_POSITIONS['right'].values())[position_index]
			groups = (self.battle_sprites, self.opponent_sprites)

		monster_sprite = MonsterSprite(position, animation_frames, groups, monster_object, monster_id, position_index, entity_type, self.apply_attack, self.create_monster)
		MonsterOutlineSprite(monster_sprite, self.battle_sprites, outline_frames)

		# ui sprites
		name_pos_offset = vector(16, -70) * self.scale if entity_type == 'player' else vector(-40, -70) * self.scale
		name_pos = monster_sprite.rect.midleft + name_pos_offset if entity_type == 'player' else monster_sprite.rect.midright + name_pos_offset
		name_sprite = MonsterNameSprite(name_pos, monster_sprite, self.battle_sprites, self.fonts['regular'])
		level_pos = name_sprite.rect.bottomleft if entity_type == 'player' else name_sprite.rect.bottomright 
		MonsterLevelSprite(entity_type, level_pos, monster_sprite, self.battle_sprites, self.fonts['small'])
		stats_pos = monster_sprite.rect.midbottom + vector(0, 20) * self.scale
		stats_size = (150, 48)
		MonsterStatsSprite(stats_pos, monster_sprite, stats_size, self.battle_sprites, self.fonts['small'])

	@global_profiler.profile_func()
	def input(self, joypad_input):
		if self.selection_mode and self.current_monster:
			input_state, just_pressed = self.get_input_state()

			# limiter for menu navigation
			menu_item_count = 0
			if self.selection_mode == 'general':
				menu_item_count = len(BATTLE_CHOICES['limited']) if self.opponent_character else len(BATTLE_CHOICES['full'])
			elif self.selection_mode == 'attacks':
				menu_item_count = len(self.current_monster.monster.get_abilities(include_all=False))
			elif self.selection_mode == 'switch':
				menu_item_count = len(self.available_monsters) if self.available_monsters else 0
			elif self.selection_mode == 'target':
				menu_item_count = len(self.opponent_sprites) if self.selection_side == 'opponent' else len(self.player_sprites)

			# keyboard input
			if just_pressed['down'] and menu_item_count > 0:
				self.indexes[self.selection_mode] = (self.indexes[self.selection_mode] + 1) % menu_item_count
			if just_pressed['up'] and menu_item_count > 0:
				self.indexes[self.selection_mode] = (self.indexes[self.selection_mode] - 1) % menu_item_count

			if just_pressed['A']:
				# touch input
				if joypad_input.last_touch_pos:
					for button_index, button_rect in self.ui_rects.items():
						if button_rect.collidepoint(joypad_input.last_touch_pos):
							self.indexes[self.selection_mode] = button_index
							break # Only select one button per press
				
				# switch selection
				if self.selection_mode == 'switch' and self.available_monsters:
					new_monster_id, new_monster_object = list(self.available_monsters.items())[self.indexes['switch']]
					self.current_monster.kill()
					self.create_monster(new_monster_object, new_monster_id, self.current_monster.pos_index, 'player')
					self.selection_mode = None
					self.current_monster = None
					self.update_all_monsters('resume')

				# target selection
				if self.selection_mode == 'target':
					sprite_group = self.opponent_sprites if self.selection_side == 'opponent' else self.player_sprites
					targetable_sprites = {sprite.pos_index: sprite for sprite in sprite_group}
					if not targetable_sprites:
						return
						
					monster_sprite = targetable_sprites[list(targetable_sprites.keys())[self.indexes['target']]]

					# attack
					if self.selected_attack:
						self.current_monster.activate_attack(monster_sprite, self.selected_attack)
						self.selected_attack, self.current_monster, self.selection_mode = None, None, None
					else:
						# catch
						if not self.opponent_character and monster_sprite.monster.health < monster_sprite.monster.get_stat('max_health') * 0.9:
							self.monster_data['player'][len(self.monster_data['player'])] = monster_sprite.monster
							monster_sprite.delayed_kill(None)
							self.update_all_monsters('resume')
						else:
							TimedSprite(monster_sprite.rect.center, self.monster_frames['ui']['cross'], self.battle_sprites, 1000)

				# attack selection
				if self.selection_mode == 'attacks':
					self.selection_mode = 'target'
					self.selected_attack = self.current_monster.monster.get_abilities(include_all = False)[self.indexes['attacks']]
					self.selection_side = ATTACK_DATA[self.selected_attack]['target']

				# general selection
				if self.selection_mode == 'general':
					if self.indexes['general'] == 0:
						abilities = self.current_monster.monster.get_abilities(include_all = False)
						if abilities:
							self.selection_mode = 'attacks'
					
					if self.indexes['general'] == 1:
						self.current_monster.monster.defending = True
						self.update_all_monsters('resume')
						self.current_monster, self.selection_mode = None, None
						self.indexes['general'] = 0
					
					if self.indexes['general'] == 2:
						active_monsters = [(monster_sprite.index, monster_sprite.monster) for monster_sprite in self.player_sprites]
						self.available_monsters = {index: monster for index, monster in self.monster_data['player'].items() if (index, monster) not in active_monsters and monster.health > 0}
						if self.available_monsters:
							self.selection_mode = 'switch'

					if self.opponent_character: # trainer battle
						if self.indexes['general'] == 3: # exit
							self.end_battle(self.opponent_character, was_wild_battle=False, forfeited=True)
					else: # wild battle
						if self.indexes['general'] == 3: # catch
							self.selection_mode = 'target'
							self.selection_side = 'opponent'
						if self.indexes['general'] == 4: # exit
							self.end_battle(None, was_wild_battle=True, forfeited=True)
				self.indexes = {key: 0 for key in self.indexes}
			
			# cancel selection
			if just_pressed['B']:
				if self.selection_mode in ('attacks', 'switch', 'target'):
					self.selection_mode = 'general'
				else:
					self.end_battle(self.opponent_character, was_wild_battle=self.opponent_character is None, forfeited=True)

	def update_timers(self):
		for timer in self.timers.values():
			timer.update()

	@global_profiler.profile_func()
	# battle system
	def check_active(self):
		for monster_sprite in chain(self.player_sprites, self.opponent_sprites):
			if monster_sprite.timers['kill'].active:
				continue

			# check initiative
			if monster_sprite.monster.initiative >= 100:
				monster_sprite.monster.defending = False
				self.update_all_monsters('pause')
				monster_sprite.monster.initiative = 0
				monster_sprite.set_highlight(True)
				self.current_monster = monster_sprite
				if self.player_sprites in monster_sprite.groups():
					# player turn
					self.selection_mode = 'general'
				else:
					# opponent turn
					self.timers['opponent delay'].activate()

	def update_all_monsters(self, option):
		for monster_sprite in chain(self.player_sprites, self.opponent_sprites):
			monster_sprite.monster.paused = True if option == 'pause' else False

	@global_profiler.profile_func()
	def apply_attack(self, target_monster_sprite, attack_name, base_damage):
		AttackSprite(target_monster_sprite.rect.center, self.monster_frames['attacks'][ATTACK_DATA[attack_name]['animation']], self.battle_sprites)
		self.sounds[ATTACK_DATA[attack_name]['animation']].play()

		# damage calculation
		attack_element = ATTACK_DATA[attack_name]['element']
		target_element = target_monster_sprite.monster.element

		# elemental multipliers
		if attack_element in TYPE_MULTIPLIERS and target_element in TYPE_MULTIPLIERS[attack_element]:
			base_damage *= TYPE_MULTIPLIERS[attack_element][target_element]

		# defense calculation
		target_defense = 1 - target_monster_sprite.monster.get_stat('defense') / DEFENSE_DIVISOR
		if target_monster_sprite.monster.defending:
			target_defense -= DEFENDING_DAMAGE_REDUCTION
		target_defense = max(0, min(1, target_defense))

		# update the monster health 
		target_monster_sprite.monster.health -= base_damage * target_defense
		self.check_death()

		# resume 
		self.update_all_monsters('resume')

	@global_profiler.profile_func()
	def check_death(self):
		for monster_sprite in chain(self.opponent_sprites, self.player_sprites):
			if monster_sprite.monster.health <= 0:
				# player monster
				if self.player_sprites in monster_sprite.groups():
					active_monsters = tuple((sprite.index, sprite.monster) for sprite in self.player_sprites.sprites())
					available_monsters = list((monster_id, monster_object) for monster_id, monster_object in self.monster_data['player'].items() if monster_object.health > 0 and (monster_id, monster_object) not in active_monsters)
					if available_monsters:
						# get replacement
						replacement_monster_data = (available_monsters[0][1], available_monsters[0][0], monster_sprite.pos_index, 'player')
					else:
						replacement_monster_data = None
				else:
					# opponent monster
					replacement_monster_data = (list(self.monster_data['opponent'].values())[0], monster_sprite.index, monster_sprite.pos_index, 'opponent') if self.monster_data['opponent'] else None
					if self.monster_data['opponent']:
						del self.monster_data['opponent'][min(self.monster_data['opponent'])]
					# xp
					xp_amount = monster_sprite.monster.level * 100 / len(self.player_sprites)
					for player_sprite in self.player_sprites:
						player_sprite.monster.update_xp(xp_amount)

				monster_sprite.delayed_kill(replacement_monster_data)

	@global_profiler.profile_func()
	def opponent_attack(self):
		if not self.current_monster:
			return

		# check for health
		if self.current_monster.monster.health <= 0:
			return

		target_sprites = self.opponent_sprites.sprites() if ATTACK_DATA[self.current_monster.monster.get_abilities()[0]]['target'] == 'player' else self.player_sprites.sprites()
		if not target_sprites:
			return

		available_abilities = self.current_monster.monster.get_abilities()
		if not available_abilities:
			return

		attack_name = choice(available_abilities)
		# select target
		if ATTACK_DATA[attack_name]['target'] == 'player':
			random_target = choice(self.opponent_sprites.sprites())
		else:
			random_target = choice(self.player_sprites.sprites())
		self.current_monster.activate_attack(random_target, attack_name)

	@global_profiler.profile_func()
	def check_end_battle(self):
		# opponents have been defeated 
		if len(self.opponent_sprites) == 0 and not self.battle_over:
			self.battle_over = True
			self.end_battle(self.opponent_character, was_wild_battle=self.opponent_character is None, player_won=True)
			for monster in self. monster_data['player'].values():
				monster.initiative = 0

		# player has been defeated 
		if len(self.player_sprites) == 0 and not self.battle_over:
			self.battle_over = True
			self.end_battle(self.opponent_character, was_wild_battle=self.opponent_character is None, player_won=False)

	# ui 
	@global_profiler.profile_func()
	def draw_ui(self):
		if self.current_monster:
			if self.selection_mode == 'general':
				self.draw_general()
			if self.selection_mode == 'attacks':
				self.draw_attacks()
			if self.selection_mode == 'switch':
				self.draw_switch()
		self.ui_rects.clear()

	@global_profiler.profile_func()
	def draw_general(self):
		choices = BATTLE_CHOICES['limited'] if self.opponent_character else BATTLE_CHOICES['full']
		for index, (choice_name, choice_data) in enumerate(choices.items()):
			
			# highlight
			if index == self.indexes['general']:
				icon_surf = self.monster_frames['scaled_ui'][f"{choice_data['icon']}_highlight"]
			else:
				original_icon_surf = self.monster_frames['scaled_ui'][choice_data['icon']]
				icon_surf = pygame.transform.grayscale(original_icon_surf)
			
			icon_rect = icon_surf.get_frect(center = self.current_monster.rect.midright + choice_data['pos'] * self.scale)
			self.display_surface.blit(icon_surf, icon_rect)
			self.ui_rects[index] = icon_rect

	@global_profiler.profile_func()
	def draw_attacks(self):
		# data
		available_abilities = self.current_monster.monster.get_abilities(include_all = False)
		width, height = 150 * self.scale, 200 * self.scale

		if not hasattr(self, 'attack_surfs'):
			self.attack_surfs = {}

		visible_attacks = 4
		item_height = height / visible_attacks
		v_offset = 0 if self.indexes['attacks'] < visible_attacks else -(self.indexes['attacks'] - visible_attacks + 1) * item_height

		# bg
		bg_rect = pygame.FRect((0,0), (width,height)).move_to(midleft = self.current_monster.rect.midright + vector(20,0) * self.scale)
		pygame.draw.rect(self.display_surface, COLORS['white'], bg_rect, 0, 5)

		for index, ability_name in enumerate(available_abilities):
			is_selected = index == self.indexes['attacks']

			# text 
			if is_selected:
				# selected color
				element = ATTACK_DATA[ability_name]['element']
				text_color = COLORS[element] if element!= 'normal' else COLORS['black']
			else:
				text_color = COLORS['light']
			
			# Caching font rendering
			if (ability_name, is_selected) not in self.attack_surfs:
				self.attack_surfs[(ability_name, is_selected)] = self.fonts['regular'].render(ability_name, False, text_color)
			text_surf = self.attack_surfs[(ability_name, is_selected)]
			
			# rect 
			text_rect = text_surf.get_frect(center = bg_rect.midtop + vector(0, item_height / 2 + index * item_height + v_offset))
			text_bg_rect = pygame.FRect((0,0), (width, item_height)).move_to(center = text_rect.center)

			# clipping
			if bg_rect.collidepoint(text_rect.center):
				if is_selected:
					if text_bg_rect.collidepoint(bg_rect.topleft):
						pygame.draw.rect(self.display_surface, COLORS['dark white'], text_bg_rect,0,0,5,5)
					elif text_bg_rect.collidepoint(bg_rect.midbottom + vector(0,-1)):
						pygame.draw.rect(self.display_surface, COLORS['dark white'], text_bg_rect,0,0,0,0,5,5)
					else:
						pygame.draw.rect(self.display_surface, COLORS['dark white'], text_bg_rect)

				# draw
				self.display_surface.blit(text_surf, text_rect)
				self.ui_rects[index] = text_bg_rect

	@global_profiler.profile_func()
	def draw_switch(self):
		# data 
		width, height = 300 * self.scale, 320 * self.scale
		visible_monsters = 4
		item_height = height / visible_monsters
		v_offset = 0 if self.indexes['switch'] < visible_monsters else -(self.indexes['switch'] - visible_monsters + 1) * item_height
		
		# background
		bg_rect = pygame.FRect((0,0), (width, height)).move_to(midleft = self.current_monster.rect.midright + vector(20,0) * self.scale)
		pygame.draw.rect(self.display_surface, COLORS['white'], bg_rect, 0, 5)

		# monsters 
		for index, monster_object in enumerate(self.available_monsters.values()):
			is_selected = index == self.indexes['switch']
			item_bg_rect = pygame.FRect((0,0), (width, item_height)).move_to(midleft = (bg_rect.left, bg_rect.top + item_height / 2 + index * item_height + v_offset))

			# text
			icon_surf = self.monster_frames['scaled_icons'][monster_object.name]
			icon_rect = icon_surf.get_frect(midleft = bg_rect.topleft + vector(10, item_height / 2 + index * item_height + v_offset))
			text_surf = self.fonts['regular'].render(f'{monster_object.name} ({monster_object.level})', False, COLORS['red'] if is_selected else COLORS['black'])
			text_rect = text_surf.get_frect(topleft = (icon_rect.right + 10, icon_rect.top))

			# selection bg
			if is_selected:
				if item_bg_rect.collidepoint(bg_rect.topleft):
					pygame.draw.rect(self.display_surface, COLORS['dark white'], item_bg_rect, 0, 0, 5, 5)
				elif item_bg_rect.collidepoint(bg_rect.midbottom + vector(0,-1)):
					pygame.draw.rect(self.display_surface, COLORS['dark white'], item_bg_rect, 0, 0, 0, 0, 5, 5)
				else:
					pygame.draw.rect(self.display_surface, COLORS['dark white'], item_bg_rect)

			# clipping
			if bg_rect.collidepoint(item_bg_rect.center):
				for item_surf, item_rect in ((icon_surf, icon_rect), (text_surf, text_rect)):
					self.display_surface.blit(item_surf, item_rect)
				health_rect = pygame.FRect((text_rect.bottomleft + vector(0,4)), (100 * self.scale, 4 * self.scale))
				energy_rect = pygame.FRect((health_rect.bottomleft + vector(0,2)), (80 * self.scale, 4 * self.scale))
				draw_bar(self.display_surface, health_rect, monster_object.health, monster_object.get_stat('max_health'), COLORS['red'], COLORS['black'])
				draw_bar(self.display_surface, energy_rect, monster_object.energy, monster_object.get_stat('max_energy'), COLORS['blue'], COLORS['black'])
				self.ui_rects[index] = item_bg_rect

	@global_profiler.profile_func()
	def update(self, delta_time, joypad_input):
		self.check_end_battle()
		
		# updates
		self.input(joypad_input)
		self.update_timers()
		self.battle_sprites.update(delta_time)
		self.check_active()

		# drawing
		self.display_surface.blit(self.bg_surf, (0,0))
		self.battle_sprites.draw(self.current_monster, self.selection_side, self.selection_mode, self.indexes['target'], self.player_sprites, self.opponent_sprites)
		self.draw_ui()
