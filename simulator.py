"""
Contiguous Memory Allocation Simulator
Operating Systems LEC - Midterm Output ("The Memory Allocation Laboratory")

Simulates First-Fit, Best-Fit and Worst-Fit on identical initial memory states.
Two memory models are supported:
  * dynamic : variable partitions. A hole is split on allocation (the remainder
              stays a hole) and adjacent holes are coalesced on deallocation.
  * fixed   : fixed partitions. A partition is never split, so the unused part
              of a partition given to a process is internal fragmentation.
"""

FIRST, BEST, WORST = "First-Fit", "Best-Fit", "Worst-Fit"
STRATEGIES = [FIRST, BEST, WORST]


class Block:
    def __init__(self, size, pid=None, used=0):
        self.size = size      # total size of the block/partition (KB)
        self.pid = pid        # None -> hole, otherwise owning process id
        self.used = used      # KB actually requested by the process

    @property
    def free(self):
        return self.pid is None


class Memory:
    def __init__(self, holes, strategy, mode="dynamic"):
        # Initial holes are separated by memory that is already in use (OS /
        # resident processes), so they must never be coalesced with each other.
        # A zero-size "wall" block models that separation.
        self.blocks = []
        for k, h in enumerate(holes):
            if k:
                self.blocks.append(Block(0, pid="<wall>"))
            self.blocks.append(Block(h))
        self.strategy = strategy
        self.mode = mode
        self.allocated, self.rejected = [], []

    # ---- choosing a hole ---------------------------------------------------
    def _choose(self, size):
        cands = [i for i, b in enumerate(self.blocks) if b.free and b.size >= size]
        if not cands:
            return None
        if self.strategy == FIRST:
            return cands[0]                                   # lowest address
        if self.strategy == BEST:
            return min(cands, key=lambda i: self.blocks[i].size)   # tightest fit
        return max(cands, key=lambda i: self.blocks[i].size)       # largest hole

    # ---- allocate / deallocate --------------------------------------------
    def allocate(self, pid, size):
        i = self._choose(size)
        if i is None:
            self.rejected.append(pid)
            return False
        b = self.blocks[i]
        if self.mode == "dynamic" and b.size > size:
            self.blocks.insert(i + 1, Block(b.size - size))    # leftover hole
            b.size = size
        b.pid, b.used = pid, size
        self.allocated.append(pid)
        return True

    def deallocate(self, pid):
        for b in self.blocks:
            if b.pid == pid:
                b.pid, b.used = None, 0
                break
        if self.mode == "dynamic":                             # coalesce
            merged = []
            for b in self.blocks:
                if merged and merged[-1].free and b.free:
                    merged[-1].size += b.size
                else:
                    merged.append(b)
            self.blocks = merged
        if pid in self.allocated:
            self.allocated.remove(pid)

    # ---- metrics -------------------------------------------------------------
    def holes(self):
        return [b.size for b in self.blocks if b.free and b.size > 0]

    def metrics(self):
        holes = self.holes()
        total_free = sum(holes)
        largest = max(holes) if holes else 0
        internal = sum(b.size - b.used for b in self.blocks if not b.free)
        return {
            "total_free": total_free,
            "largest_hole": largest,
            "unusable_free": total_free - largest,   # free KB outside the largest hole
            "ext_frag_pct": round(100 * (1 - largest / total_free), 1) if total_free else 0.0,
            "internal": internal,
            "num_holes": len(holes),
        }

    def memory_map(self):
        out = []
        for b in self.blocks:
            if b.size == 0:
                continue
            out.append(f"[{b.pid}:{b.used}" + (f"+{b.size - b.used}wasted" if b.size > b.used else "") + "]"
                       if not b.free else f"[hole:{b.size}]")
        return " ".join(out)


def run(holes, events, strategy, mode="dynamic", verbose=False):
    """events: ('alloc', pid, size) or ('free', pid)."""
    m = Memory(holes, strategy, mode)
    log = []
    for ev in events:
        if ev[0] == "alloc":
            ok = m.allocate(ev[1], ev[2])
            log.append(f"  alloc {ev[1]:>3} ({ev[2]:>4} KB) -> {'OK' if ok else 'REJECTED'}")
        else:
            m.deallocate(ev[1])
            log.append(f"  free  {ev[1]:>3}")
    if verbose:
        print("\n".join(log))
    return m, log


# ---------------------------------------------------------------------------
HOLES = [100, 500, 200, 300, 600]
EVENTS = [("alloc", "P1", 212), ("alloc", "P2", 417), ("alloc", "P3", 112),
          ("alloc", "P4", 426), ("free", "P2"), ("alloc", "P5", 200)]

# Part 1.3 counter-example: Best-Fit loses to First-Fit
CE_HOLES = [400, 250]
CE_EVENTS = [("alloc", "A", 50), ("alloc", "B", 210), ("alloc", "C", 250)]


def report(title, holes, events, mode):
    print("=" * 74)
    print(f"{title}  |  mode={mode}  |  initial holes={holes}")
    print("=" * 74)
    for s in STRATEGIES:
        m, _ = run(holes, events, s, mode, verbose=True)
        mt = m.metrics()
        print(f"  [{s}]")
        print(f"    allocated now : {m.allocated}   rejected: {m.rejected}")
        print(f"    final map     : {m.memory_map()}")
        print(f"    free={mt['total_free']} KB, largest hole={mt['largest_hole']} KB, "
              f"free outside largest={mt['unusable_free']} KB, "
              f"ext.frag={mt['ext_frag_pct']}%, internal={mt['internal']} KB")
        print()


if __name__ == "__main__":
    report("TEST 1 - Suggested data", HOLES, EVENTS, "dynamic")
    report("TEST 2 - Suggested data, fixed partitions", HOLES, EVENTS, "fixed")
    report("TEST 3 - Best-Fit worse than First-Fit", CE_HOLES, CE_EVENTS, "dynamic")
