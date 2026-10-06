from pygame.time import get_ticks
from debug import global_profiler


class Timer:
	@global_profiler.profile_func()
	def __init__(self, duration, repeat = False, autostart = False, func = None):
		self.duration = duration
		self.start_time = 0
		self.active = False
		self.repeat = repeat
		self.func = func
		if autostart:
			self.activate()

	@global_profiler.profile_func()
	def activate(self):
		# start timer
		self.active = True
		self.start_time = get_ticks()

	@global_profiler.profile_func()
	def deactivate(self):
		# stop timer
		self.active = False
		self.start_time = 0
		if self.repeat:
			self.activate()

	@global_profiler.profile_func()
	def update(self):
		if self.active:
			# check time
			current_time = get_ticks()
			if current_time - self.start_time >= self.duration:
				if self.func: self.func()
				self.deactivate()
