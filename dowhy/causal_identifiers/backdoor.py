import networkx as nx
from dowhy.utils.graph_operations import adjacency_matrix_to_adjacency_list

class NodePair:
    def __init__(self, node1, node2):
        self._node1 = node1
        self._node2 = node2
        self._is_blocked = None # To store if all paths between node1 and node2 are blocked
        self._condition_vars = [] #set() # To store variable to be conditioned on to block all paths between node1 and node2
        self._complete = False # To store to paths between node pair have been completely explored.
    
    def update(self, path, condition_vars=None):
        if condition_vars is None:
            '''path is a Path variable'''
            if self._is_blocked is None:
                self._is_blocked = path.is_blocked()
            else:
                self._is_blocked = self._is_blocked and path.is_blocked()
            if not path.is_blocked():
                # self._condition_vars = self._condition_vars.union(path.get_condition_vars())
                self._condition_vars.append(path.get_condition_vars())

        else:
            '''path is a list'''
            # self._condition_vars = self._condition_vars.union([*path[1:], *condition_vars])
            self._condition_vars.append(set([*path[1:], *condition_vars]))
            # self._condition_vars.append(set([*path, *condition_vars]))

    # def update(self, paths):
    #     self._is_blocked = all([path.is_blocked() for path in paths])
    #     if not self._is_blocked:
    #         for path in paths:
    #             self._condition_vars = self._condition_vars.union(path.get_condition_vars())
    
    def get_condition_vars(self):
        return self._condition_vars

    def set_complete(self):
        self._complete = True
    
    def is_complete(self):
        return self._complete

    def __str__(self):
        string = ""
        string += "Blocked: " + str(self._is_blocked) + "\n"
        if not self._is_blocked:
            condition_vars = [str(s) for s in self._condition_vars]
            string += "To block path, condition on: " + ",".join(condition_vars) + "\n"
            # string += "To block path, condition on: " + ",".join(self._condition_vars) + "\n"
        return string
    

class Path:
    def __init__(self):
        self._is_blocked = None # To store if path is blocked
        self._condition_vars = set() # To store variables needed to block the path
        # self._colliders = set() # Used to store colliders
    
    def update(self, path, is_blocked):
        '''
        path is a list
        '''
        self._is_blocked = is_blocked
        if not is_blocked:
            self._condition_vars = self._condition_vars.union(set(path[1:-1]))
    
    def is_blocked(self):
        return self._is_blocked
    
    def get_condition_vars(self):
        return self._condition_vars
    
    def __str__(self):
        string = ""
        string += "Blocked: " + str(self._is_blocked) + "\n"
        if not self._is_blocked:
            string += "To block path, condition on: " + ",".join(self._condition_vars) + "\n"
        return string

class Backdoor:

    def __init__(self, graph, nodes1, nodes2):
        self._graph = graph
        self._nodes1 = nodes1
        self._nodes2 = nodes2
        self._nodes12 = set(self._nodes1).union(self._nodes2)
        
    def get_backdoor_paths(self):
        undirected_graph = self._graph.to_undirected()
        
        # Get adjacency list
        adjlist = adjacency_matrix_to_adjacency_list(nx.to_numpy_matrix(undirected_graph), labels=list(undirected_graph.nodes))
        path_dict = {}

        for node1 in self._nodes1:
            for node2 in self._nodes2:
                if (node1, node2) in path_dict:
                    continue
                self._path_search(adjlist, node1, node2, path_dict)
        return path_dict

    def is_backdoor(self, path):
        return True if self._graph.has_edge(path[1], path[0]) else False

    def _path_search_util(self, graph, node1, node2, vis, path, path_dict, is_blocked=False, prev_arrow=None):
        '''
        :param prev_arrow: True if arrow incoming, False if arrow outgoing
        '''
        if is_blocked:
            return

        # If node pair has been fully explored
        if ((node1, node2) in path_dict) and (path_dict[(node1, node2).is_complete()]):
            for i in range(len(path)):
                if (path[i], node2) not in path_dict:
                    path_dict[(path[i], node2)] = NodePair(path[i], node2)
                path_dict[(path[i], node2)].update(path[i:], path_dict[(node1, node2)].get_condition_vars())

        else:
            path.append(node1)
            vis.add(node1)
            if node1 == node2:
                # Check if path is backdoor and does not have nodes1\node1 or nodes2\node2 as intermediate nodes
                if self.is_backdoor(path) and len(self._nodes12.intersection(set(path[1:-1])))==0:
                    for i in range(len(path)-1):
                        if (path[i], node2) not in path_dict:
                            path_dict[(path[i], node2)] = NodePair(path[i], node2)
                        path_var = Path()
                        path_var.update(path[i:].copy(), is_blocked)
                        path_dict[(path[i], node2)].update(path_var)
            else:
                for neighbour in graph[node1]:
                    if neighbour not in vis:
                        # True if arrow incoming, False if arrow outgoing
                        next_arrow = False if self._graph.has_edge(node1, neighbour) else True 
                        if next_arrow == True and prev_arrow == True:
                            is_blocked = True
                        self._path_search_util(graph, neighbour, node2, vis, path, path_dict, is_blocked, not next_arrow) # Since incoming for current node is outgoing for the next
            path.pop()
            vis.remove(node1)

        # Mark pair (node1, node2) complete
        if (node1, node2) in path_dict:
            path_dict[(node1, node2)].set_complete()

    def _path_search(self, graph, node1, node2, path_dict):
        '''
        Path search using DFS.
        '''
        vis = set()
        self._path_search_util(graph, node1, node2, vis, [], path_dict, is_blocked=False)

class HittingSetAlgorithm:

    def __init__(self, list_of_sets):
        self._list_of_sets = list_of_sets
        return self._find_set()
    
    def _find_set(self):
        var_set = set()
        all_set_indices = set([i for i in range(len(self._list_of_sets))])
        while not self._is_covered(var_set):
            set_index = all_set_indices - var_set
            var_dict = self._count_vars(set_index=set_index)
            max_el = self._max_occurence_var(var_dict=var_dict)
            var_set.insert(max_el)
        return var_set

    def _count_vars(self, set_index = None):
        '''
        set_index is a set.
        '''
        var_dict = {}

        if set_index = None:
            set_index = set([i for i in range(len(self._list_of_sets))])

        for idx in set_index:
            s = self._list_of_sets[idx]

            for el in s:
                if s not in var_dict:
                    var_dict[s] = 0
                var_dict[s] += 1
        
        return var_dict
    
    def _max_occurence_var(self, var_dict):
        max_el = None
        max_count = 0
        for key, val in var_dict.items():
            if val>max_count:
                max_count = val
                max_el = key
        return max_el

    def _is_covered(self, var_set):
        ''' List of sets is covered by the variable set.'''
        if len(var_set) == 0:
            return False
        for el in var_set:
            is_present = False
            for s in self._list_of_sets:
                if el in s:
                    is_present = True
                    break
            if not is_present:
                return False
        return True