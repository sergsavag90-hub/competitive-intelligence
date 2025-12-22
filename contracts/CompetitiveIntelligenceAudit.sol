// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title Immutable audit log for competitive intelligence scans
contract CompetitiveIntelligenceAudit {
    event ScanRecorded(address indexed sender, bytes32 competitorHash, bytes32 dataHash, uint256 timestamp);

    // Simple mapping for existence check; not storing raw data on-chain
    mapping(bytes32 => bool) public recorded;

    /// @notice Record a scan hash on-chain
    function recordScan(bytes32 competitorHash, bytes32 dataHash) external {
        bytes32 composite = keccak256(abi.encodePacked(competitorHash, dataHash, block.timestamp, msg.sender));
        recorded[composite] = true;
        emit ScanRecorded(msg.sender, competitorHash, dataHash, block.timestamp);
    }

    /// @notice Verify whether a given data hash has been recorded
    function verifyData(bytes32 dataHash) external view returns (bool) {
        // This example treats the dataHash itself as a key; in practice you may
        // store explicit mapping from dataHash => true as well.
        return recorded[dataHash];
    }
}
