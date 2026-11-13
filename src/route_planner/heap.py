"""Binary min heap"""

class MinHeap:
    """priority queue that insert items without order order and pop them starting from smallest one"""

    def __init__(self):
        self._items = []
    
    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    def peek(self):
        """return the smallest without removing it O(1)"""
        if not self._items:
            raise IndexError("pop from an empty heap")
        return self._items[0]

    def push(self, item) -> None:
        """heap insert O(logn)"""
        self._items.append(item)
        self._sift_up(len(self._items)-1)

    def pop(self):
        """remove and return the smallest item O(logn), heap extract"""
        if not self._items:
            raise IndexError("pop from an empty heap")

        last = self._items.pop()
        if not self._items:
            return last
        smallest = self._items[0]
        self._items[0] = last
        self._sift_down(0)
        return smallest

    # tree navigation with arithmetic calculus
    @staticmethod
    def _parent(i: int) -> int:
        return (i-1)//2

    @staticmethod
    def _children(i: int) -> tuple[int, int]:
        return 2*i +1, 2*i +2

    def _sift_up(self, i: int) -> None:
        """O(logn) per call"""
        items = self._items
        while i>0:
            parent = self._parent(i)
            if items[i] < items[parent]:
                items[i], items[parent] = items[parent], items[i]
                i = parent
            else:
                break
    
    def _sift_down(self, i: int) -> None:
        """O(logn) per call"""
        items = self._items
        n = len(items)

        while True:
            left, right = self._children(i)
            smallest = i
            if left < n and items[left] < items[smallest]:
                smallest = left
            if right < n and items[right] < items[smallest]:
                smallest = right
            if smallest==i:
                break

            items[i], items[smallest] = items[smallest], items[i]
            i = smallest