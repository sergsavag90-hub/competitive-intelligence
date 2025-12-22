"""
Blockchain-backed audit trail helper.

Stores SHA256 hashes of scan results on-chain for immutability proofs.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Optional

from web3 import Web3
from web3.middleware import geth_poa_middleware

logger = logging.getLogger(__name__)


class AuditTrailClient:
    def __init__(
        self,
        rpc_url: Optional[str] = None,
        contract_address: Optional[str] = None,
        private_key: Optional[str] = None,
        chain_id: int = 137,  # default Polygon mainnet
        abi: Optional[list] = None,
    ):
        self.rpc_url = rpc_url or os.getenv("WEB3_RPC_URL", "")
        self.contract_address = contract_address or os.getenv("AUDIT_CONTRACT_ADDRESS", "")
        self.private_key = private_key or os.getenv("WEB3_PRIVATE_KEY", "")
        self.chain_id = chain_id
        self.abi = abi or [
            {
                "inputs": [
                    {"internalType": "bytes32", "name": "competitorHash", "type": "bytes32"},
                    {"internalType": "bytes32", "name": "dataHash", "type": "bytes32"},
                ],
                "name": "recordScan",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "bytes32", "name": "dataHash", "type": "bytes32"}],
                "name": "verifyData",
                "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function",
            },
        ]

        if not self.rpc_url or not self.contract_address:
            logger.warning("AuditTrailClient initialized without RPC URL or contract address; running in noop mode.")
            self.w3 = None
            self.contract = None
            return

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 10}))
        # Some networks (Polygon/BSC) need PoA middleware
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.contract = self.w3.eth.contract(address=Web3.to_checksum_address(self.contract_address), abi=self.abi)

    @staticmethod
    def sha256_bytes(payload: bytes) -> bytes:
        return hashlib.sha256(payload).digest()

    def record_scan_hash(self, competitor_name: str, data: bytes) -> Optional[str]:
        """
        Compute hash and submit to chain. Returns tx hash or None if noop.
        """
        if not self.contract or not self.private_key:
            logger.debug("AuditTrailClient noop (missing contract or private key).")
            return None

        competitor_hash = self.sha256_bytes(competitor_name.encode("utf-8"))
        data_hash = self.sha256_bytes(data)

        account = self.w3.eth.account.from_key(self.private_key)
        nonce = self.w3.eth.get_transaction_count(account.address)
        tx = self.contract.functions.recordScan(competitor_hash, data_hash).build_transaction(
            {
                "from": account.address,
                "nonce": nonce,
                "chainId": self.chain_id,
                "gas": 300000,
                "maxFeePerGas": self.w3.to_wei("50", "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei("2", "gwei"),
            }
        )
        signed = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        logger.info("Audit hash submitted: tx=%s", tx_hash.hex())
        return tx_hash.hex()

    def verify_hash(self, data: bytes) -> bool:
        if not self.contract:
            return False
        data_hash = self.sha256_bytes(data)
        return bool(self.contract.functions.verifyData(data_hash).call())
