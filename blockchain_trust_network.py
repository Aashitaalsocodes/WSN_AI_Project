"""
blockchain_trust_network.py
Decentralized, multi-node blockchain trust management for WSN.

Unlike a single-process chain, this simulates several independent
trust-evaluator nodes, each holding its own copy of the ledger.
New blocks are broadcast to peers, who validate them independently
before accepting (majority-vote consensus). Conflicting chains are
resolved via the longest-valid-chain rule.

This is what actually justifies the words "decentralized" and
"consensus-based validation" in a paper -- a single in-process
chain (see blockchain_trust.py) does not.
"""

import hashlib
import json
import time
import random
from copy import deepcopy


class Block:
    def __init__(self, index, timestamp, transactions, previous_hash, proposer):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.proposer = proposer
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "proposer": self.proposer,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine(self, difficulty=2):
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()

    def is_valid_transactions(self):
        """Basic sanity check a peer can run without trusting the proposer."""
        for tx in self.transactions:
            if tx == "Genesis Block":
                continue
            if not isinstance(tx, dict):
                return False
            score = tx.get("trust_score")
            if score is None or not (0.0 <= score <= 1.0):
                return False
            if "node_id" not in tx:
                return False
        return True

    def to_dict(self):
        return {
            "index": self.index, "timestamp": self.timestamp,
            "transactions": self.transactions, "previous_hash": self.previous_hash,
            "proposer": self.proposer, "nonce": self.nonce, "hash": self.hash
        }


class TrustEvaluatorNode:
    """
    One independent trust-evaluator node in the network.
    Holds its own full copy of the chain and validates
    everything it receives instead of trusting peers blindly.
    """

    def __init__(self, node_id, difficulty=2, malicious=False):
        self.node_id = node_id
        self.difficulty = difficulty
        self.malicious = malicious  # if True, will sometimes propose a bad block
        self.chain = [self._genesis_block()]
        self.pending = []
        self.peers = []  # other TrustEvaluatorNode instances
        self.rejected_blocks = 0
        self.accepted_blocks = 0

    def _genesis_block(self):
        # Fixed timestamp so every node in the network starts from an
        # identical genesis block (otherwise each node's genesis hash
        # differs by construction time and no two nodes ever agree).
        return Block(0, 0.0, ["Genesis Block"], "0", proposer="genesis")

    def connect(self, peer):
        if peer not in self.peers:
            self.peers.append(peer)

    def latest_block(self):
        return self.chain[-1]

    def add_trust_transaction(self, node_id, trust_score, evaluator=None):
        self.pending.append({
            "node_id": node_id,
            "trust_score": round(trust_score, 4),
            "evaluator": evaluator or self.node_id,
            "timestamp": time.time(),
            "transaction_id": hashlib.sha256(
                f"{node_id}{trust_score}{time.time()}{self.node_id}".encode()
            ).hexdigest()[:8]
        })

    def propose_block(self):
        """
        Mine a block from this node's pending transactions and
        broadcast it to peers for validation. Returns the block
        and whether the network (including self) accepted it.
        """
        if not self.pending:
            return None, False

        txs = self.pending.copy()

        if self.malicious:
            # Simulate a faulty/dishonest node injecting a fraudulent score
            txs.append({
                "node_id": "node_1", "trust_score": 999.0,  # invalid, out of range
                "evaluator": self.node_id, "timestamp": time.time(),
                "transaction_id": "FRAUD001"
            })

        prev = self.latest_block()
        block = Block(prev.index + 1, time.time(), txs, prev.hash, proposer=self.node_id)
        block.mine(self.difficulty)

        accepted = self._broadcast_and_validate(block)
        self.pending = []
        return block, accepted

    def _broadcast_and_validate(self, block):
        """
        Send the proposed block to every peer (and self) and require
        a majority to accept it before it's committed to any chain.
        This is the consensus step.
        """
        voters = self.peers + [self]
        votes_for = 0

        for peer in voters:
            if peer.validate_incoming_block(block):
                votes_for += 1

        majority_needed = len(voters) // 2 + 1
        accepted = votes_for >= majority_needed

        if accepted:
            for peer in voters:
                peer._commit_block(block)
        else:
            self.rejected_blocks += 1

        return accepted

    def validate_incoming_block(self, block):
        """
        A peer independently checks a proposed block before voting
        to accept it -- it does NOT trust the proposer, and it does
        NOT rely on knowing whether the proposer is 'malicious' (that
        label doesn't exist in a real network). Every check here is
        based only on the block's content and this node's own chain
        history.
        """
        prev = self.latest_block()
        if block.previous_hash != prev.hash:
            return False
        if block.hash != block.calculate_hash():
            return False
        if not block.is_valid_transactions():
            return False
        if block.hash[:self.difficulty] != "0" * self.difficulty:
            return False  # didn't actually do the proof-of-work
        if not self._transactions_pass_plausibility_check(block.transactions):
            return False
        return True

    def _transactions_pass_plausibility_check(self, transactions, max_jump=0.4):
        """
        Content-based fraud check: a trust score that is technically
        in [0,1] but jumps implausibly far from that node's last
        recorded score (as known from THIS peer's own chain history)
        is rejected. This catches subtler manipulation than an
        out-of-range value -- e.g. a compromised node's score being
        quietly inflated from 0.3 to 0.95 in one step.
        """
        for tx in transactions:
            if not isinstance(tx, dict):
                continue
            node_id = tx.get("node_id")
            new_score = tx.get("trust_score")
            last_score = self.get_trust(node_id)
            if last_score is not None and new_score is not None:
                if abs(new_score - last_score) > max_jump:
                    return False
        return True

    def _commit_block(self, block):
        self.chain.append(block)
        self.accepted_blocks += 1

    def is_chain_valid(self, chain=None):
        chain = chain or self.chain
        for i in range(1, len(chain)):
            cur, prev = chain[i], chain[i - 1]
            if cur.hash != cur.calculate_hash():
                return False
            if cur.previous_hash != prev.hash:
                return False
        return True

    def resolve_fork(self, other_chain):
        """
        Longest-valid-chain rule: if a peer's chain is longer and
        valid, adopt it in place of ours.
        """
        if len(other_chain) > len(self.chain) and self.is_chain_valid(other_chain):
            self.chain = deepcopy(other_chain)
            return True
        return False

    def get_trust(self, node_id):
        for block in reversed(self.chain):
            for tx in block.transactions:
                if isinstance(tx, dict) and tx.get("node_id") == node_id:
                    return tx.get("trust_score")
        return None


def build_network(n_nodes=5, difficulty=2, malicious_indices=None):
    malicious_indices = malicious_indices or []
    nodes = [
        TrustEvaluatorNode(f"evaluator_{i}", difficulty=difficulty,
                            malicious=(i in malicious_indices))
        for i in range(n_nodes)
    ]
    for i, node in enumerate(nodes):
        for j, other in enumerate(nodes):
            if i != j:
                node.connect(other)
    return nodes


if __name__ == "__main__":
    print("=" * 65)
    print("Decentralized Multi-Node Trust Network -- Consensus Demo")
    print("=" * 65)

    random.seed(7)

    # --- Scenario 1: honest network reaches consensus normally ---
    print("\n[Scenario 1] 5 honest evaluator nodes, one proposes a round of scores")
    nodes = build_network(n_nodes=5, difficulty=2)
    proposer = nodes[0]
    for i in range(6):
        proposer.add_trust_transaction(f"node_{i}", random.uniform(0.5, 1.0))
    block, accepted = proposer.propose_block()
    print(f"  Block proposed by {proposer.node_id}: accepted={accepted}")
    print(f"  All nodes chain length now: {[len(n.chain) for n in nodes]}")
    print(f"  Chains identical across all nodes: "
          f"{all(n.chain[-1].hash == nodes[0].chain[-1].hash for n in nodes)}")

    # --- Scenario 2: a malicious node tries to push a fraudulent score ---
    print("\n[Scenario 2] Same network, but evaluator_2 goes rogue and injects a "
          "fraudulent trust score (999.0, out of valid [0,1] range)")
    nodes2 = build_network(n_nodes=5, difficulty=2, malicious_indices=[2])
    rogue = nodes2[2]
    rogue.add_trust_transaction("node_7", 0.4)
    block, accepted = rogue.propose_block()
    print(f"  Malicious block proposed by {rogue.node_id}: accepted={accepted}")
    print(f"  Rejected-block count on rogue node: {rogue.rejected_blocks}")
    print(f"  Chain length across network (should be unchanged at 1): "
          f"{[len(n.chain) for n in nodes2]}")

    # --- Scenario 3: fork resolution ---
    print("\n[Scenario 3] Two nodes mine conflicting blocks concurrently (fork), "
          "then a third node needs to resolve it")
    nodes3 = build_network(n_nodes=3, difficulty=1)  # low difficulty for quick fork demo
    a, b, c = nodes3
    # Disconnect a and b temporarily to simulate a network partition
    a.peers = [x for x in a.peers if x.node_id != b.node_id]
    b.peers = [x for x in b.peers if x.node_id != a.node_id]

    a.add_trust_transaction("node_10", 0.9)
    a.propose_block()  # a mines on its own, c sees it (still connected to both)

    b.add_trust_transaction("node_11", 0.2)
    b.propose_block()  # b mines its own competing block

    print(f"  Chain lengths after partition: a={len(a.chain)}, b={len(b.chain)}, c={len(c.chain)}")
    # c reconnects a and b, and whichever chain is longer/valid wins on both sides
    a.peers.append(b)
    b.peers.append(a)
    resolved_a = a.resolve_fork(b.chain)
    resolved_b = b.resolve_fork(a.chain)
    print(f"  a adopted b's chain: {resolved_a} | b adopted a's chain: {resolved_b}")
    print(f"  Final chain lengths: a={len(a.chain)}, b={len(b.chain)}, c={len(c.chain)}")

    # --- Scenario 4: subtle in-range manipulation (not just out-of-range fraud) ---
    print("\n[Scenario 4] A node's real trust score is 0.30 (established over prior "
          "rounds). A dishonest evaluator proposes inflating it to 0.90 in one step "
          "-- a value that's perfectly VALID on its own (within [0,1]), so a naive "
          "range check would miss it. This is caught by comparing against this "
          "peer's own history, not by knowing who's 'malicious'.")
    nodes4 = build_network(n_nodes=5, difficulty=2)
    # Establish a real trust history for node_3 across all peers
    for n in nodes4:
        n.add_trust_transaction("node_3", 0.30)
    nodes4[0].propose_block()
    print(f"  Established trust for node_3 = {nodes4[1].get_trust('node_3')} "
          f"(chain length now {len(nodes4[0].chain)})")

    dishonest = nodes4[3]
    dishonest.add_trust_transaction("node_3", 0.90)  # implausible jump, in-range
    block, accepted = dishonest.propose_block()
    print(f"  Inflated-score block proposed by {dishonest.node_id}: accepted={accepted}")
    print(f"  node_3's trust score after attempt (should still be 0.30): "
          f"{nodes4[1].get_trust('node_3')}")

    print("\n" + "=" * 65)
    print("Summary: consensus rejects invalid/fraudulent blocks; "
          "honest network stays in agreement; forks resolve deterministically; "
          "even in-range implausible score jumps are caught via history comparison.")