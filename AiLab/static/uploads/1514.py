from typing import List


class Solution:
    def maxProbability(
        self,
        n: int,
        edges: List[List[int]],
        succProb: List[float],
        start_node: int,
        end_node: int,
    ) -> float:
        graph = [[] for _ in range(n)]
        for i, (u, v) in enumerate(edges):
            prob = succProb[i]
            graph[u].append((v, prob))
            graph[v].append((u, prob))
        
        max_prob = [0.0] * n
        max_prob[start_node] = 1.0

        heap = [(-1.0, start_node)]

        while heap:
            neg_brop, u = self.pop_max(heap)
            current_prob = -neg_brop

            if u == end_node:
                return current_prob
            
            if current_prob < max_prob[u]:
                continue

            for v, prob in graph[u]:
                new_prob = current_prob * prob
                if new_prob > max_prob[v]:
                    max_prob[v] = new_prob
                    heap.append((-new_prob, v))

        return max_prob[end_node]
    
    def pop_max(self, heap):
        # Находим элемент с максимальной вероятностью
        max_idx = 0
        for i in range(1, len(heap)):
            if heap[i][0] < heap[max_idx][0]:
                max_idx = i
        return heap.pop(max_idx)

s = Solution()
print(s.maxProbability(3, [[0, 1], [1, 2], [0, 2]], [0.5, 0.5, 0.2], 0, 2))
