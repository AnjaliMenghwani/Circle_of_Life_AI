# -*- coding: utf-8 -*-
"""Circle_of_Life_BetterSmarterFaster.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1LgSNr6YhgJPoXbwzA9aKglvE3pwoEv9z

# Imports
"""

from collections import defaultdict
import random
import numpy as np
from collections import deque
from sys import maxsize
import math
import pickle
import pandas as pd
import copy

"""# Environment"""

class Environment:
  
  def __init__(self, N):
    self.graph = dict() # Graph with 50 nodes
    self.predator = Predator(N)
    self.prey = Prey(N)
    self.agent = Agent(self.predator.position, self.prey.position, N)
    self.make_graph(N)
    self.shortest_paths = self.all_shortest_paths(N)
    
    
  def make_graph(self, N):    
    self.add_loop(N) # Adding Circular Edges
    self.add_random_edges(N) # Adding Random Edges
  
  def add_loop(self, N):
    self.graph[1], self.graph[N] = [N, 2], [1, N - 1]
    for node in range(2, N):
      self.graph[node] = [(node + 1), (node - 1)]
    
  def add_random_edges(self, N):
    step = 4
    for i in range(1, N + 1):
        possible_neighbours = []
        for j in range(i + 1, i + step + 1):
            if j > N:
                possible_neighbours.append(j % N)
            else:
                possible_neighbours.append(j)

        if i - step < 1:
            back_iter = N + (i - step)
        else:
            back_iter = i - step

        for j in range(back_iter, back_iter + step):
            if j > N:
                possible_neighbours.append(j % N)
            else:
                possible_neighbours.append(j)

        while len(possible_neighbours) > 0:
            choice = random.choice(possible_neighbours)

            # check if there's already an edge
            neighbours = self.graph.get(i)
            if len(neighbours) < 3 and len(self.graph[choice]) < 3 and choice not in neighbours:
                self.graph[i].append(choice)
                self.graph[choice].append(i)
                break
            else:
              possible_neighbours.remove(choice)

  def check_agent_alive(self):
      return self.agent.position != self.predator.position  
  
  def find_paths(self, paths, path, parent, n, u):
      if u == -1:
          paths.append(path.copy())
          return

      for par in parent[u]:
          path.append(u)
          self.find_paths(paths, path, parent, n, par)
          path.pop()

  def bfs_for_all_paths(self, parent, n, start):

      dist = [maxsize for _ in range(n)]
      q = deque()
      q.append(start)
      parent[start] = [-1]
      dist[start] = 0

      while q:
          u = q[0]
          q.popleft()
          for v in self.graph[u]:
              if dist[v] > dist[u] + 1:
                  dist[v] = dist[u] + 1
                  q.append(v)
                  parent[v].clear()
                  parent[v].append(u)

              elif dist[v] == dist[u] + 1:
                  parent[v].append(u)

  def all_paths(self, n, start, end):
      paths, path, shortest_path = [], [], []
      parent = [[] for _ in range(n)]
      self.bfs_for_all_paths(parent, n, start)
      self.find_paths(paths, path, parent, n, end)
      for v in paths:
          v = list(reversed(v))
          shortest_path.append(v)
      return shortest_path  

  def all_shortest_paths(self, N):
    shortest_paths = dict()
    for i in range(1, N + 1):
      for j in range(1, N + 1):
        shortest_paths[(i, j)] = self.all_paths(N + 1, i, j)
    return shortest_paths


class Agent:
  def __init__(self, prey_pos, pred_pos, N):
    self.position = self.spawn(prey_pos, pred_pos, N)
  
  def spawn(self, prey_pos, pred_pos, N):
    position = random.randint(1, N)
    while(prey_pos == position or pred_pos == position):
      position = random.randint(1, N)
    return position
  
  def move_agent(self, utility, env):
    best_node, min_utility = env.agent.position, utility[(self.position, env.prey.position, env.predator.position)]
    for action in env.graph[env.agent.position]:
      if utility[(action, env.prey.position, env.predator.position)] < min_utility:
        min_utility = utility[(action, env.prey.position, env.predator.position)]
        best_node = action
    self.position = best_node


class Predator:

  def __init__(self, N):
    self.position = random.randint(1, N)

  def move_distracted_predator(self, env):
    movements = []
    for neighbor in env.graph.get(self.position):
        movements.append([len(env.shortest_paths[(neighbor, env.agent.position)][0]) - 1, neighbor])
    movements.sort()

    potential_neighbors = [movements[0][1]]

    for i in range(1, len(movements)):
        if movements[i][0] == movements[0][0]:
            potential_neighbors.append(movements[i][1])
        else:
            break
    random_number = random.randint(1, 100)
    if random_number <= 40:
        next_position = random.choice(env.graph.get(self.position))
    else:
        next_position = random.choice(potential_neighbors)
    self.position = next_position

  def probability_distracted_predator(self, env, pd, pd_neigh, ag_pos):
    all_shortest_paths = env.shortest_paths[(pd, ag_pos)]
    unique_nodes = set()
    for path in all_shortest_paths:
      if len(path) > 1:
        unique_nodes.add(path[1])
    if pd_neigh in unique_nodes:
      return 0.6/len(unique_nodes)
    return 0


class Prey:

  def __init__(self, N):
    self.position = random.randint(1, N)

  def move_prey(self, env):
    # randomly choosing among neighbours and current position
    neighbours = [self.position]
    for neighbour in env.graph[self.position]:
        neighbours.append(neighbour)
    self.prey_pos = random.choice(neighbours)

"""# MDP"""

class MDP:


  def __init__(self, N):
    self.state_ustar = dict() # Initialise all
    self.action = dict() # Best action  { key-value => state -> best action }


  def bellman_update(self, env, ag, prey_pos_list, predator_pos_list, pd):
    future_utility = 0
    for pr_neigh in prey_pos_list:
      for pd_neigh in predator_pos_list:
          probability = (1.0/len(prey_pos_list))*((0.4/len(predator_pos_list)) + env.predator.probability_distracted_predator(env, pd, pd_neigh, ag))
          future_utility += probability*(self.state_ustar[(ag, pr_neigh, pd_neigh)])
    return future_utility
    

  def ustar_heuristic(self, env, agent_pos, prey_pos, predator_pos):
    if agent_pos == predator_pos or abs(agent_pos - predator_pos) == 1:
      cost = math.inf
    elif agent_pos == prey_pos:
      cost = 0.0
    else:
      cost = len(env.shortest_paths[agent_pos, prey_pos][0]) - 1
    return cost
    
  def compute_reward(self, env, agent_pos, prey_pos, predator_pos):
    if agent_pos == predator_pos or abs(agent_pos - predator_pos) == 1:
      reward = math.inf
    elif agent_pos == prey_pos:
      reward = 0.0
    else: 
      reward = 1
    return reward

  def initialize_ustar(self, env):
    ustar = {}
    for agent_pos in range(1, len(env.graph) + 1): 
      for prey_pos in range(1, len(env.graph) + 1):
        for predator_pos in range(1, len(env.graph) + 1):
          ustar[(agent_pos, prey_pos, predator_pos)] = self.ustar_heuristic(env, agent_pos, prey_pos, predator_pos)
    return ustar


  def value_iteration(self, env):

    tolerence = 0.0001

    self.state_ustar = self.initialize_ustar(env)

    while True:

      current = copy.deepcopy(self.state_ustar)
      error_list = []
      for ag, pr, pd in self.state_ustar.keys():

        if current[(ag, pr, pd)] == 0.0 or current[(ag, pr, pd)] == math.inf:
          continue
        
        action_value = []
        for action in env.graph[ag]:
          if (action == pr) and (action != pd):
            action_value.append(0)
            continue
          if action == pd:
            action_value.append(math.inf)
            continue          
          
          prey_pos_list, predator_pos_list = [pr], []
          
          for neighbor in env.graph[pr]:
            prey_pos_list.append(neighbor)

          for neighbor in env.graph[pd]:
            predator_pos_list.append(neighbor)

          action_value.append(self.bellman_update(env, action, prey_pos_list, predator_pos_list, pd))  
        current[(ag, pr, pd)] = self.compute_reward(env, ag, pr, pd) + min(action_value)

        
      max_error = 0

      for ag, pr, pd in self.state_ustar.keys():
        max_error = max(max_error, abs(self.state_ustar[(ag, pr, pd)] - current[(ag, pr, pd)]))

      print('error', max_error)

      if max_error < tolerence:
        break
      self.state_ustar = current

"""# **U* for complete Information Setting**"""

N = 50
env = Environment(N) # Creating Instance for Environment
print('Initial Configuration(Pred, Prey, Agent): ', env.predator.position, env.prey.position, env.agent.position)
print(env.graph)
mdp = MDP(N) # Creating Instance for MDP

print(env.shortest_paths)

# Computing U*
mdp.value_iteration(env)

"""Dumping mdp, env instance to pickle files"""

# Dumping objects in temp file
with open('/content/drive/MyDrive/ustar/ustar.pickle', 'wb') as f:
    pickle.dump(mdp, f)

with open('/content/drive/MyDrive/ustar/graph.pickle', 'wb') as f:
    pickle.dump(env, f)

with open('/content/drive/MyDrive/ustar/ustar.pickle', 'rb') as f:
  mdp = pickle.load(f)

with open('/content/drive/MyDrive/ustar/graph.pickle', 'rb') as f:
  env = pickle.load(f)

from google.colab import drive
drive.mount('/content/drive')

"""**U* Agent** """

def UstarAgent(env, ustar):
  steps = 0
  while steps < 200:

    steps += 1

    env.agent.move_agent(ustar, env)    

    # check if agent caught prey
    if env.agent.position == env.prey.position:

      return 1, steps

    env.prey.move_prey(env)

    # check if agent caught prey
    if env.agent.position == env.prey.position:

      return 1, steps

    env.predator.move_distracted_predator(env)

    # check if agent is dead
    if not env.check_agent_alive():
      return 0, 0
  # Timeout
  return -1, 0

"""U* Simulations for Data Analysis"""

def run_simulations(env, ustar, runs):
  success, failure, timeout, average_steps = 0, 0, 0, 0
  for i in range(runs):
    # Resetting States
    prey, predator = Prey(len(env.graph)), Predator(len(env.graph))
    agent = Agent(prey.position, predator.position, len(env.graph))

    while(ustar[(agent.position, prey.position, predator.position)] == math.inf):
      prey, predator = Prey(len(env.graph)), Predator(len(env.graph))
      agent = Agent(prey.position, predator.position, len(env.graph))

    env.agent = agent
    env.prey = prey
    env.predator = predator

    result, steps = UstarAgent(env, ustar)
    
    average_steps += steps

    if result == 1:
      success += 1
    elif result == 0:
      failure += 1
    else:
      timeout += 1

  print('Success Rate: ',  success/(runs/100), '%',  ' Failure: ', failure/(runs/100), '%',  ' Timeout: ', timeout/(runs/100), '%', 'Average Steps: ', average_steps/(runs))

run_simulations(env, mdp.state_ustar, 10000)

mdp.state_ustar

lis = []
state = []
for k, v in mdp.state_ustar.items():
  if v != math.inf:
    lis.append(v)
    state.append(k)

index = lis.index(max(lis))
print('Max Finite utility:',lis[index], ', State:', state[index])
finite_max = max(lis)

env.shortest_paths[1, 7]

"""**U* Partial Setting**

# U* Partial Setting
"""

def pick_highest_probability_node(belief_prey):
    # choosing neighbours randomly from the highest belief list
    max_prob, prob = max(belief_prey[1:]), []

    for i in range(1, len(belief_prey)):
        if belief_prey[i] == max_prob:
            prob.append(i)

    return random.choice(prob)

def survey(node, env):
    return node == env.prey.position

def update_belief(belief_prey, survey_node, found_prey):
    # belief update for survey and agent movement
    if found_prey:
        belief_prey[survey_node] = 1.0
        for node in range(1, len(belief_prey)):
            if node != survey_node:
                belief_prey[node] = 0.0
    else:
        prob_survey_node = belief_prey[survey_node]
        belief_prey[survey_node] = 0.0
        for node in range(1, len(belief_prey)):
            belief_prey[node] = belief_prey[node] * (1.0 / (1 - prob_survey_node))

def compute_expected_utility(agent_pos, predator_pos, belief_prey, ustar):
  expected_utility = 0
  for prey_pos in range(1, len(belief_prey)):
    expected_utility += belief_prey[prey_pos]*ustar[(agent_pos, prey_pos, predator_pos)]
  return expected_utility

def move_agent(env, belief_prey, ustar, ustar_partial):


  # Computing Ustar_partial
  for agent_pos in env.graph[env.agent.position]:
    for predator_pos in env.graph[env.predator.position]:
      expected_utility = compute_expected_utility(agent_pos, predator_pos, belief_prey, ustar)
      ustar_partial[(agent_pos, predator_pos)] = (belief_prey, expected_utility)

  min_action_value = math.inf
  best_node = env.agent.position

  # Choosing the best action 
  for action in env.graph[env.agent.position]:
    for predator in env.graph[env.predator.position]:
      if(ustar_partial[(action, predator)][1] < min_action_value):
        min_action_value = ustar_partial[(action, predator)][1]
        best_node = action
  env.agent.position = best_node


def update_belief_prey(env, belief_prey):
    belief_prey_copy = copy.deepcopy(belief_prey)

    for node in range(1, len(belief_prey)):

        neighbors = env.graph.get(node)

        belief_prey[node] = belief_prey_copy[node] * (1.0 / (len(neighbors) + 1))

        for neighbor in neighbors:
            belief_prey[node] += belief_prey_copy[neighbor] * (1.0 / (len(env.graph.get(neighbor)) + 1))

def Ustar_partial_agent(env, ustar, ustar_partial, belief_prey):
  steps = 0
  
  # Prob of prey at agent position is 0
  belief_prey[env.agent.position] = 0.0

  while steps < 5000:

    steps += 1

    # Pick Highest Probable Node 
    highest_belief_node = pick_highest_probability_node(belief_prey)
    
    # Survey Highest Probable Node
    found_prey = survey(highest_belief_node, env)

    # Update Belief States of Prey
    update_belief(belief_prey, highest_belief_node, found_prey)

    # Move agent
    move_agent(env, belief_prey, ustar, ustar_partial)
    
    if env.agent.position == env.prey.position:
      return 1, steps
    
    # Update Belief States of Prey
    update_belief(belief_prey, env.agent.position, False)

    # Move prey
    env.prey.move_prey(env)

    if env.agent.position == env.prey.position:
      return 1, steps

    # Update Belief States of Prey
    update_belief_prey(env, belief_prey)

    # Move Predator
    env.predator.move_distracted_predator(env)

    if env.agent.position == env.predator.position:
      return 0, 0

  return -1, 0

def run_simulations_ustar_partial(env, ustar, ustar_partial, runs):
  success, failure, timeout, steps = 0, 0, 0, 0
  for i in range(runs):
    # Resetting States
    prey, predator = Prey(len(env.graph)), Predator(len(env.graph))
    agent = Agent(prey.position, predator.position, len(env.graph))
    belief_prey = [1/49]*(N + 1)

    while(ustar[(agent.position, prey.position, predator.position)] == math.inf):
      prey, predator = Prey(len(env.graph)), Predator(len(env.graph))
      agent = Agent(prey.position, predator.position, len(env.graph))

    env.agent = agent
    env.prey = prey
    env.predator = predator

    result, stepCount = Ustar_partial_agent(env, ustar, ustar_partial, belief_prey)
    steps += stepCount
    if result == 1:
      success += 1
    elif result == 0:
      failure += 1
    else:
      timeout += 1
  return [success, failure, timeout, steps]

# Reusing Environment & U* Values to compute U* partial
N = 50
mdp_partial = MDP(N)

def run_partial(runs):
  while(len(mdp_partial.state_ustar) != 2500):
    result = run_simulations_ustar_partial(env, mdp.state_ustar, mdp_partial.state_ustar, runs)
  print('Success Rate: ',  result[0]/(runs/100), '%',  ' Failure: ', result[1]/(runs/100), '%',  ' Timeout: ', result[2]/(runs/100), '%',  'Average Steps: ', result[3]/(runs))

run_partial(3000)

print(len(list(mdp_partial.state_ustar.items())))

lis = []
for k, v in mdp_partial.state_ustar.items():
  if(v[1] != math.inf):
    lis.append(v[1])
print(max(lis))

#Dumping objects in temp file
with open('/content/drive/MyDrive/ustar/ustar_partial.pickle', 'wb') as f:
    pickle.dump(mdp_partial, f)

with open('/content/drive/MyDrive/ustar/ustar_partial.pickle', 'rb') as f:
  mdp_partial = pickle.load(f)

"""# Create Feature Set"""

# [agent_pos, prey_pos, predator_pos, distance_from_agent_prey, distance_from_agent_predator]
def prepare_feature_set(env, mdp):
  features, target_util = [], []
  for agent_pos in range(1, 51):
    for prey_pos in range(1, 51):
      for predator_pos in range(1, 51):
        if mdp.state_ustar[(agent_pos, prey_pos, predator_pos)] < finite_max:
          features.append((agent_pos, prey_pos, predator_pos, len(env.shortest_paths[agent_pos, prey_pos][0]) - 1, len(env.shortest_paths[agent_pos, predator_pos][0]) - 1))
          target_util.append(mdp.state_ustar[(agent_pos, prey_pos, predator_pos)])
  return features, target_util


def prepare_feature_set_partial(env, mdp_partial):
  features, target_util = [], []
  for agent_pos in range(1, 51):
    for predator_pos in range(1, 51):
      if (agent_pos, predator_pos) in mdp_partial.state_ustar: 
        belief_util = mdp_partial.state_ustar[(agent_pos, predator_pos)]
        if belief_util[1] != math.inf:
            feature = [agent_pos, predator_pos, len(env.shortest_paths[agent_pos, predator_pos][0]) - 1]
            for i in range(1, 51):
              feature.append(belief_util[0][i])
            features.append(tuple(feature))
            target_util.append(belief_util[1])
  return features, target_util

"""# Neural Network"""

class NeuralNetwork:

  def __init__(self,X,Y):
    self.W1 = np.random.randn(36, 5)*0.01
    self.b1 = np.zeros((36, 1))
    self.W2 = np.random.randn(1, 36)*0.01
    self.b2 = np.zeros((1, 1))
    
    self.Z1 = None
    self.Z2 = None
    self.A1 = None
    self.A2 = None
    self.X = X.T
    self.Y = Y.T
    
  def relu(self,A1):
    return np.maximum(A1,0)
  
  def relu_prime(self,Z1):
    return 1. * (Z1 > 0)

  def forward_propagation(self):
    self.Z1 = np.dot(self.W1,self.X) + self.b1
    self.A1 = self.relu(self.Z1)
    self.Z2 = np.dot(self.W2,self.A1) + self.b2
    self.A2 = self.Z2
    
  def backward_propagation(self):
    dZ2 = (self.A2-self.Y)
    dW2 = (1/109990)*(np.dot(dZ2,self.A1.T))
    db2 = (1/109990) * np.sum(dZ2)
    dZ1 = np.multiply(np.dot(self.W2.T,dZ2), self.relu_prime(self.Z1))
    dW1 = (1/109990)*(np.dot(dZ1,self.X.T))
    db1 = (1/109990)*(np.sum(dZ1))
    return dW1, db1, dW2, db2
  
  def update_weights_bias(self,dW1, db1, dW2, db2):
    self.W1 = self.W1 - 0.001*dW1
    self.b1 = self.b1 - 0.001*db1
    self.W2 = self.W2 - 0.001*dW2
    self.b2 = self.b2 - 0.001*db2
    
  def run(self):
    loss = math.inf
    while(loss >= 2.0):
      self.forward_propagation()
      dW1, db1, dW2, db2 = self.backward_propagation()
      self.update_weights_bias(dW1, db1, dW2, db2)
      print("____________________________")
      loss = (np.mean((self.Y - self.A2)**2)*0.5)
      print(loss)

  def predict(self, X):
    Z1 = np.dot(self.W1,X) + self.b1
    A1 = self.relu(Z1)
    Z2 = np.dot(self.W2,A1) + self.b2
    A2 = Z2
    return A2[0][0]


class NeuralNetworkPartial:
  
  def __init__(self,X,Y):
    self.W1 = np.random.randn(53, 53)*0.01
    self.b1 = np.zeros((53, 1))
    self.W2 = np.random.randn(106, 53)*0.01
    self.b2 = np.zeros((106,1))
    self.W3 = np.random.randn(1, 106)*0.01
    self.b3 = np.zeros((1, 1))
    self.loss_list = []
    self.Z1 = None
    self.Z2 = None
    self.Z3 = None
    self.A1 = None
    self.A2 = None
    self.A3 = None
    self.X = X.T
    self.m = self.X.shape[1]
    self.Y = Y.T
    self.p = 0.3
    self.l2 = 0.7
    
  def relu(self,A1):
    return np.maximum(A1,0)
  
  def relu_prime(self,Z1):
    return 1. * (Z1 > 0)
  
  def forward(self):
    self.Z1 = np.dot(self.W1, self.X) + self.b1
    self.D1 = np.random.choice([0, 1], size=(53,1), p=[self.p, 1-self.p]) #Dropout
    self.Z1 = self.D1*self.Z1
    self.A1 = self.relu(self.Z1)
    self.Z2 = np.dot(self.W2,self.A1) + self.b2
    self.D2 = np.random.choice([0, 1], size=(106,1), p=[self.p, 1-self.p]) #Dropout
    self.Z2 = self.D2*self.Z2
    self.A2 = self.relu(self.Z2)
    self.Z3 = np.dot(self.W3, self.A2) + self.b3
    self.A3 = self.Z3
    
  def backward(self):
    
    dZ3 = (self.A3-self.Y)
    dW3 = (1/self.m)*(np.dot(dZ3,self.A2.T)) + (self.l2*self.W3)/self.m
    db3 = (1/self.m) * np.sum(dZ3)
    
    dZ2 = np.multiply(np.dot(self.W3.T,dZ3), self.relu_prime(self.Z2))
    dW2 = (1/self.m)*(np.dot(dZ2,self.A1.T)) + (self.l2*self.W2)/self.m
    db2 = (1/self.m) * np.sum(dZ2)
    
    dZ1 = np.multiply(np.dot(self.W2.T,dZ2), self.relu_prime(self.Z1))
    dW1 = (1/self.m)*(np.dot(dZ1,self.X.T)) + (self.l2*self.W1)/self.m
    db1 = (1/self.m)*(np.sum(dZ1))
    
    return dW1, db1, dW2, db2, dW3, db3
  
  def update_params(self,dW1, db1, dW2, db2, dW3, db3):
    self.W1 = self.W1 - 0.001*dW1
    self.b1 = self.b1 - 0.001*db1
    self.W2 = self.W2 - 0.001*dW2
    self.b2 = self.b2 - 0.001*db2
    self.W3 = self.W3 - 0.001*dW3
    self.b3 = self.b3 - 0.001*db3
    
  def run(self):
    for i in range(10000):
      self.forward()
      dW1, db1, dW2, db2, dW3, db3 = self.backward()
      self.update_params(dW1, db1, dW2, db2, dW3, db3)
      loss = (np.mean((self.Y - self.A3)**2)*0.5)
      self.loss_list.append(loss)
      print("Loss for iteration {} => {}".format(i,loss))
  
  def predict(self, X):
    Z1 = np.dot(self.W1,X) + self.b1
    D1 = np.random.choice([0, 1], size=(53,1), p=[self.p, 1-self.p]) #Dropout
    Z1 = D1*Z1
    A1 = self.relu(Z1)
    Z2 = np.dot(self.W2, A1) + self.b2
    D2 = np.random.choice([0, 1], size=(106,1), p=[self.p, 1-self.p]) #Dropout
    Z2 = D2*Z2
    A2 = self.relu(Z2)
    Z3 = np.dot(self.W3, A2) + self.b3
    A3 = Z3
    return A3[0][0]

# Training Features on V* 
features, target_util = prepare_feature_set(env, mdp)
print(len(features))
neural_network = NeuralNetwork(np.array(features), np.array(target_util))
neural_network.run()

for k, v in mdp_partial.state_ustar.items():
  print(k, v[1], v[0].index(max(v[0][1:])), min(v[0][1:]), max(v[0][1:]))

# Training Features on V* partial
features_partial, target_util_partial = prepare_feature_set_partial(env, mdp_partial)
print(len(features_partial))
neural_network_partial = NeuralNetworkPartial(np.array(features_partial), np.array(target_util_partial))
neural_network_partial.run()

# Dumping objects in temp file
with open('/content/drive/MyDrive/vstar/vstar.pickle', 'wb') as f:
    pickle.dump(neural_network, f)

# with open('/content/drive/MyDrive/vstar_partial/vstar_partial.pickle', 'wb') as f:
#     pickle.dump(neural_network_partial, f)

with open('/content/drive/MyDrive/vstar/vstar.pickle', 'rb') as f:
  neural_network = pickle.load(f)

# with open('/content/drive/MyDrive/vstar_partial/vstar_partial.pickle', 'rb') as f:
#   neural_network_partial = pickle.load(f)

"""# V* Agent"""

vstar_util = dict()
for i in range(1, 51):
  for j in range(1, 51):
    for k in range(1, 51):
      feature = [i, j, k, len(env.shortest_paths[i, j][0]), len(env.shortest_paths[i, k][0])]
      vstar_util[(i, j, k)] = neural_network.predict(feature)
run_simulations(env, vstar_util, 10000)

"""# V* Partial Agent"""

vstar_util_partial = dict()
for agent_pos in range(1, 51):
  for predator_pos in range(1, 51):
    if (agent_pos, predator_pos) in mdp_partial.state_ustar: 
      belief_util = mdp_partial.state_ustar[(agent_pos, predator_pos)]
      if belief_util[1] != math.inf:
          feature = [agent_pos, predator_pos, len(env.shortest_paths[agent_pos, predator_pos][0]) - 1]
          for i in range(1, 51):
            feature.append(belief_util[0][i])
          vstar_util_partial[(i, j)] = neural_network_partial.predict(np.array(tuple(feature)).T)
run_simulations_ustar_partial(env, vstar_util, 10000)