from game_data import MONSTER_DATA, ATTACK_DATA
from debug import global_profiler


class Monster:
	@global_profiler.profile_func()
	def __init__(self, name, level):
		self.name, self.level = name, level
		self.paused = False

		# stats 
		self.element = MONSTER_DATA[name]['stats']['element']
		self.base_stats = MONSTER_DATA[name]['stats']
		self.health = self.base_stats['max_health'] * self.level
		self.energy = self.base_stats['max_energy'] * self.level
		self.initiative = 0
		self.abilities = MONSTER_DATA[name]['abilities']
		self.defending = False

		# experience
		self.xp = 0
		self.level_up = self.level * 150
		self.evolution = MONSTER_DATA[self.name]['evolve']

	@global_profiler.profile_func()
	def __repr__(self):
		return f'monster: {self.name}, lvl: {self.level}'

	@global_profiler.profile_func()
	def get_stat(self, stat):
		# stat by level
		return self.base_stats[stat] * self.level

	@global_profiler.profile_func()
	def get_stats(self):
		return {
			'health': self.get_stat('max_health'),
			'energy': self.get_stat('max_energy'),
			'attack': self.get_stat('attack'),
			'defense': self.get_stat('defense'),
			'speed': self.get_stat('speed'),
			'recovery': self.get_stat('recovery'),
		}

	@global_profiler.profile_func()
	def get_abilities(self, include_all = True):
		# all abilities
		if include_all:
			return [ability for lvl, ability in self.abilities.items() if self.level >= lvl]
		
		# available abilities
		else:
			return [ability for lvl, ability in self.abilities.items() if self.level >= lvl and ATTACK_DATA[ability]['cost'] <= self.energy]

	@global_profiler.profile_func()
	def get_info(self):
		# for battle ui
		return ((self.health, self.get_stat('max_health')),
				(self.energy, self.get_stat('max_energy')),
				(self.initiative, 100))

	@global_profiler.profile_func()
	def reduce_energy(self, attack_name):
		# used in battle
		self.energy -= ATTACK_DATA[attack_name]['cost']

	@global_profiler.profile_func()
	def get_base_damage(self, attack_name):
		# used in battle
		return self.get_stat('attack') * ATTACK_DATA[attack_name]['amount']

	@global_profiler.profile_func()
	def update_xp(self, xp_amount):
		if self.level_up - self.xp > xp_amount:
			self.xp += xp_amount
		
		else:
			# level up
			self.level += 1
			self.xp = xp_amount - (self.level_up - self.xp)
			self.level_up = self.level * 150

	@global_profiler.profile_func()
	def stat_limiter(self):
		self.health = max(0, min(self.health, self.get_stat('max_health')))
		# limit stats
		self.energy = max(0, min(self.energy, self.get_stat('max_energy')))

	@global_profiler.profile_func()
	def update(self, delta_time):
		self.stat_limiter()
		# increase initiative
		if not self.paused:
			self.initiative += self.get_stat('speed') * delta_time
