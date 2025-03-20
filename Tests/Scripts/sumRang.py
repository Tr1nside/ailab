arr = [1,3,10,1,23]

class TestArray():
    def __init__(self, arr):
        self.arr = arr

    def sumRange(self, low, high):
        rangeArray = self.arr[low:high+1]
        return sum(rangeArray)

# testArray = TestArray(arr)

# print(testArray.sumRange(0, 3)) 


def binary_search(arr: list[int], target: int, left=0, right=None) -> int:
    if target not in arr:
        print(arr)
        arr.append(target)
        arr.sort()
        print(arr)

    if right is None:
        right = len(arr) - 1
    
    if left > right:
        return -1
    
    mid = (left + right) // 2

    if arr[mid] == target:
        return mid
    elif target < arr[mid]:
        return binary_search(arr, target, left, mid - 1)
    else:
        return binary_search(arr, target, mid + 1, right)
    
array = [1,3]
target = 1

print(binary_search(array, target))

