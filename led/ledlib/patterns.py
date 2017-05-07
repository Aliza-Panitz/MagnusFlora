import random
import time
from ledlib.helpers import debugprint
from ledlib import ledmath

from ledlib import globalconfig
from ledlib import globaldata

def randomcolor(maxbright=.5):
	# not really random: everything over maxbright collapses to same intensity
	from ledlib import ledmath

	RGB_min = ledmath.RGB_min
	RGB_max = ledmath.RGB_max

	# TODO: add a parameter to control possible brightness
	red = random.randint(RGB_min,RGB_max)
	green = random.randint(RGB_min,RGB_max)
	blue = random.randint(RGB_min,RGB_max)

	debugprint ((red, green, blue))			# print the tuple, not 3 singles
	rgb = ledmath.dimmer((red,  green, blue),1.0,maxbright)
	debugprint (rgb)
	return rgb


def wake_up (first, size, rgb_color_triplet):
	debugprint ("Waking up "+ str(size) + " pixels")
	debugprint (rgb_color_triplet)

	if globalconfig.fastwake:
		for i in range(size):
			globaldata.all_the_pixels[first+i] = rgb_color_triplet
	else:
		shuffled_index = [ 0 ] * size
		for i in range (size):
			shuffled_index[i] = i
		random.shuffle (shuffled_index)

		for i in range (size):
			# even without a sleep this took visible time to run.  not a good sign.
			# but setting to a single color was very fast
			globaldata.all_the_pixels[first+shuffled_index[i]] = randomcolor()
			time.sleep (globalconfig.twinkle/4)

		time.sleep (10 * globalconfig.framedelay)

		# shuffle again
		random.shuffle (shuffled_index)
		for i in range (size):
			globaldata.all_the_pixels[first+shuffled_index[i]] = rgb_color_triplet
			time.sleep (globalconfig.twinkle)


def fade (list_of_pixel_numbers, rgb_color_triplet, fade_ratio=0.5, speed=0):
	# pixel 0 is at 100%; pixel last is at fade_ratio; if sleep defined
	# sleep after setting every pixel

	size = len(list_of_pixel_numbers)

	globaldata.all_the_pixels[list_of_pixel_numbers[0]]=rgb_color_triplet
	for i in range(1,size):
		fade = 1.0 - ((i/size)*fade_ratio)
		debugprint ((i,fade))
		globaldata.all_the_pixels[list_of_pixel_numbers[i]]= \
						dimmer(rgb_color_triplet,fade)
		if speed > 0:
			time.sleep(speed)

def parallel_blend (list_of_lists_of_pixel_numbers, \
										rgb1, rgb2, speed=0, steps=100):
	# pixel 0 is at 100%; pixel last is at fade_ratio;
	# smooth gradient along multiple strands of LEDs of different lengths.

	strand_count = len(list_of_lists_of_pixel_numbers)
	strand_sizes = [0] * strand_count
	strand_pointers = [0] * strand_count

	for strand in range(strand_count):
		strand_sizes[strand] = len(list_of_lists_of_pixel_numbers[strand])
		debugprint (("Strand ", strand, "size ", strand_sizes[strand]))
		globaldata.all_the_pixels \
					[list_of_lists_of_pixel_numbers[strand][0]]=rgb1


	for thisstep in range(steps):
		# ignore the fencepost errors.  not going for exactness here.
		# hue will vary due to rounding.  possibly a feature.
		progress = thisstep/steps
		newcolor = ledmath.mix(rgb1, progress, rgb2)
		debugprint (("blend", thisstep, newcolor))
		for strand in range(strand_count):
			while progress > (strand_pointers[strand] / strand_sizes[strand]):
				globaldata.all_the_pixels \
					[list_of_lists_of_pixel_numbers[strand][strand_pointers[strand]]] = \
							newcolor
				strand_pointers[strand] += 1
		if speed > 0:
			time.sleep(speed/steps)

	# nail in the last pixel in each strand
	for strand in range(strand_count):
		globaldata.all_the_pixels \
				[list_of_lists_of_pixel_numbers[strand][strand_sizes[strand]-1]]= \
				rgb2






def parallel_fade (list_of_lists_of_pixel_numbers, \
										rgb_color_triplet, fade_ratio=0.5, speed=0, steps=100):
	# pixel 0 is at 100%; pixel last is at fade_ratio;
	# smooth gradient along multiple strands of LEDs of different lengths.

	strand_count = len(list_of_lists_of_pixel_numbers)
	strand_sizes = [0] * strand_count
	strand_pointers = [0] * strand_count
	for strand in range(strand_count):
		strand_sizes[strand] = len(list_of_lists_of_pixel_numbers[strand])
		debugprint (("Strand ", strand, "size ", strand_sizes[strand]))
		globaldata.all_the_pixels \
					[list_of_lists_of_pixel_numbers[strand][0]]=rgb_color_triplet


	for thisstep in range(steps):
		# ignore the fencepost errors.  not going for exactness here.
		# hue will vary due to rounding.  possibly a feature.
		brightness = 1.0 - fade_ratio*thisstep/steps
		newcolor = ledmath.dimmer(rgb_color_triplet, brightness)
		debugprint (("fade", thisstep, brightness, newcolor))
		progress = thisstep/steps
		for strand in range(strand_count):
			while progress > (strand_pointers[strand] / strand_sizes[strand]):
				globaldata.all_the_pixels \
					[list_of_lists_of_pixel_numbers[strand][strand_pointers[strand]]] = \
							newcolor
				strand_pointers[strand] += 1
		if speed > 0:
			time.sleep(speed/steps)

	# nail in the last pixel in each strand
	newcolor = ledmath.dimmer(rgb_color_triplet, fade_ratio)
	for strand in range(strand_count):
		globaldata.all_the_pixels \
				[list_of_lists_of_pixel_numbers[strand][strand_sizes[strand-1]]]= \
				newcolor







