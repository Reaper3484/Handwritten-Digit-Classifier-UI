import re
import pygame
from pygame.locals import *
import pygame.window
import numpy as np
import tensorflow as tf
from tensorflow import keras
import matplotlib.pyplot as plt

import pred


pygame.init()
grid_width = 28
grid_height = 28
cell_size = 25
padding = 1

output_rect_padding = 10
output_rect_color = 'grey'

output_screen_width = 500

width = grid_width * (cell_size + padding) + padding + output_screen_width
height = grid_height * (cell_size + padding) + padding 
bg_color = 'black'
screen = pygame.display.set_mode((width, height))

og_cell_color = 'white'
drawn_cell_color = 'black'


class GridCell:
    none = -1   
    drawn = 1
    erased = 0

    def __init__(self, x, y) -> None:
        self.surf = pygame.Surface((cell_size, cell_size))
        self.rect = self.surf.get_rect(topleft=(x, y))
        self.surf.fill(og_cell_color)
        self.value = GridCell.erased
        self.state = GridCell.erased

    def update(self):
        if self.state == GridCell.none:
            return self.value

        if self.state == GridCell.drawn:
            self.surf.fill(drawn_cell_color)
            self.state = GridCell.none
            self.value = GridCell.drawn
            return self.value

        elif self.state == GridCell.erased:
            self.surf.fill(og_cell_color)
            self.state = GridCell.none
            self.value = GridCell.erased
            return self.value

    def draw(self):
        screen.blit(self.surf, self.rect)


class Grid:
    isDrawing = False
    isErasing = False

    def __init__(self) -> None:
       self.grid_cells = [[(x, y) for x in range(grid_height)] for y in range(grid_height)] 
       self.grid_values = [[0 for x in range(grid_height)] for y in range(grid_height)] 
       self.initialise_cells()
    
    def initialise_cells(self):
        for i in range(grid_height):
            for j in range(grid_width):
                cell = GridCell(padding + i * (cell_size + padding), padding + j * (cell_size + padding))
                self.grid_cells[i][j] = cell

    def draw(self):
        for i in range(grid_height):
            for j in range(grid_width):
                cell = self.grid_cells[i][j]
                self.grid_values[i][j] = cell.update()
                cell.draw()

    def clear(self):
        for i in range(grid_height):
            for j in range(grid_width):
                cell = self.grid_cells[i][j]
                cell.state = GridCell.erased
                cell.value = GridCell.erased
                self.grid_values[i][j] = 0


class NeuralNetwork:
    def __init__(self, grid) -> None:
        self.model = keras.models.load_model('nn_model.h5') 
        self.grid = grid

    def predict(self):
        image_array = np.array(self.grid.grid_values)
        image_array = np.transpose(image_array)

        image_array = image_array.reshape(1, 28, 28)
        prediction = self.model.predict(image_array)

        predicted_digit = np.argmax(prediction[0])
        return prediction[0]


class UI:
    def __init__(self) -> None:
        self.probabilities = [0 for _ in range(10)]  # Initialize probabilities
        self.rect_height = (height) // 10
        self.rect_width = output_screen_width - 100  # Leave space for text on the right
        self.padding = padding
        self.font = pygame.font.SysFont(None, 24)  # Initialize font once
        
        # Pre-render digit surfaces (0-9), probabilities will be updated as needed
        self.digit_surfaces = [self.font.render(f"Digit: {i}", True, (255, 255, 255)) for i in range(10)]
        
        # List to store the probability surfaces for rendering
        self.prob_surfaces = [self.font.render(f"Prob: 0.00", True, (255, 255, 255)) for _ in range(10)]
        
        # Precompute static rect positions and store them
        self.rects = [(width - output_screen_width + self.padding, 
                      i * self.rect_height + output_rect_padding) for i in range(10)]

        # Pre-render empty rectangles so they can be reused without recalculating
        self.min_rect_width = 10  # Minimum bar width
        self.max_rect_width = self.rect_width  # Maximum width for scaling

    def update(self, new_probabilities):
        """ Update probabilities and probability surfaces when they change. """
        for i, prob in enumerate(new_probabilities):
            self.probabilities[i] = prob

            # Pre-render the probability surface only if the value changes
            prob_text = f"Prob: {prob:.2f}"
            self.prob_surfaces[i] = self.font.render(prob_text, True, (255, 255, 255))

    def draw(self):
        """ Draw rectangles and text on the screen every frame. """
        for i, prob in enumerate(self.probabilities):
            # Scale rectangle width based on probability, with a minimum width
            rect_width = max(int(prob * self.max_rect_width), self.min_rect_width)
            rect_x, rect_y = self.rects[i]

            # Draw the rectangle for each probability
            pygame.draw.rect(screen, output_rect_color, (rect_x, rect_y, rect_width, self.rect_height - output_rect_padding))

            # Draw pre-rendered digit surface and probability text
            screen.blit(self.digit_surfaces[i], (rect_x + rect_width + 10, rect_y))  # Digit label
            screen.blit(self.prob_surfaces[i], (rect_x + rect_width + 10, rect_y + 20))  # Probability text


ui = UI()
grid = Grid()
nn = NeuralNetwork(grid)

clock = pygame.time.Clock()
running = True

while (running):
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        
        any_change = False

        if event.type == MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                for i in range(grid_height):
                    for j in range(grid_height):
                        if grid.grid_cells[i][j].rect.collidepoint(event.pos):
                            grid.grid_cells[i][j].state = GridCell.drawn
                            if grid.grid_cells[i][j].value != GridCell.drawn: any_change = True

                Grid.isDrawing = True
                
            if event.button == 3: # Right click
                for i in range(grid_height):
                    for j in range(grid_height):
                        if grid.grid_cells[i][j].rect.collidepoint(event.pos):
                            grid.grid_cells[i][j].state = GridCell.erased
                            if grid.grid_cells[i][j].value != GridCell.erased: any_change = True
                Grid.isErasing = True

        if event.type == MOUSEMOTION:
            if Grid.isDrawing or Grid.isErasing:
                for i in range(grid_height):
                    for j in range(grid_height):
                        if grid.grid_cells[i][j].rect.collidepoint(event.pos):
                            if Grid.isDrawing:
                                grid.grid_cells[i][j].state = GridCell.drawn
                                if grid.grid_cells[i][j].value != GridCell.drawn: any_change = True
                            else:
                                grid.grid_cells[i][j].state = GridCell.erased
                                if grid.grid_cells[i][j].value != GridCell.erased: any_change = True
                                
        if event.type == MOUSEBUTTONUP:
            Grid.isErasing = False
            Grid.isDrawing = False

        if event.type == KEYDOWN:
            if event.key == K_c:
                any_change = True
                grid.clear()

        if any_change:
            output = nn.predict()
            ui.update(output)

    screen.fill(bg_color)

    ui.draw()
    grid.draw() 

    clock.tick(360)
    pygame.display.update()

pygame.quit()