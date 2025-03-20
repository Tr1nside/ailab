
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

# class Solution:
#     def __init__(self):
#         self.result = [[], []]

#     def pre_order(self, node, flag):  
#         if node:
#             self.result[flag].append(node.val)
#             self.pre_order(node.right, flag)  # Передаем k в рекурсивный вызов
#             self.pre_order(node.left, flag)   # Передаем k в рекурсивный вызов
#     def isSameTree(self, p: TreeNode, q: TreeNode) -> bool:
#         if not p and not q:
#             return True
#         if not p or not q:
#             return False

class Solution:
    def __init__(self):
        self.result = []
        pass
    def maxDepth(self, root: TreeNode) -> int:
        self.pre_order(self, root)
        if self.result:
            return max(self.result)
        return 0
    def pre_order(self, root, num=0):  
        if root:
            num += 1
            self.result.append(num)
            self.pre_order(root.right, num)
            self.pre_order(root.left, num)

            
                
         
            
        


# Создание дерева
tree = TreeNode(4)
tree.left = TreeNode(2)
tree.left.left = TreeNode(1)
tree.left.right = TreeNode(3)
tree.right = TreeNode(7)

# Создание дерева
tree2 = TreeNode(4)
tree2.left = TreeNode(2)
tree2.left.left = TreeNode(1)
tree2.left.right = TreeNode(3)
tree2.right = TreeNode(7)

# Создание экземпляра решения
solution = Solution()

print(solution.isSameTree(tree, tree2))