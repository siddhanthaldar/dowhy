import numpy as np
import networkx as nx

from . import get_library_class_object
from dowhy.graph_learners import GraphLearner
from dowhy.utils.graph_operations import *

class CDT(GraphLearner):

	def __init__(self, data, full_method_name, *args, **kwargs):
		super().__init__(data, full_method_name, *args, **kwargs)
		
		library_class = get_library_class_object(full_method_name)
		self._method = library_class(*args, **kwargs)
	
	def learn_graph(self, labels=None):
		'''
		Discover causal graph and return the graph in DOT format.

		'''
		graph = self._method.predict(self._data)
		
		# Get adjacency matrix
		self._adjacency_matrix = nx.to_numpy_matrix(graph)
		self._adjacency_matrix = np.asarray(self._adjacency_matrix)

		# If labels not provided
		if labels is not None:
			self._labels = labels

		self._graph_dot = adjacency_matrix_to_graph(self._adjacency_matrix, self._labels)
		
		# Obtain valid DOT format
		graph_str = str_to_dot(self._graph_dot.source)
		return graph_str
