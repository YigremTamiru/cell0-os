#!/usr/bin/env python3
"""
KULLU Coordinator - Autonomous Cell 0 OS Orchestration
Runs continuously, monitors all agents, coordinates work.
"""

import json
import time
import os
from datetime import datetime
from pathlib import Path

CELL0_ROOT = Path("/Users/yigremgetachewtamiru/.openclaw/workspace/cell0")

class KulluCoordinator:
    def __init__(self):
        self.iteration = 0
        self.agent_status = {}
        
    def read_agent_status(self):
        """Read status from all agents"""
        status_files = {
            "kernel": CELL0_ROOT / "kernel-status.json",
            "daemon": CELL0_ROOT / "daemon-status.json",
        }
        
        for agent, path in status_files.items():
            if path.exists():
                try:
                    with open(path) as f:
                        self.agent_status[agent] = json.load(f)
                except:
                    self.agent_status[agent] = {"error": "invalid json"}
            else:
                self.agent_status[agent] = {"status": "no-report-yet"}
                
    def check_kernel_health(self):
        """Run cargo check on kernel"""
        import subprocess
        result = subprocess.run(
            ["cargo", "check"],
            cwd=CELL0_ROOT / "kernel",
            capture_output=True,
            text=True
        )
        warnings = result.stdout.count("warning:") + result.stderr.count("warning:")
        errors = result.returncode != 0
        return {
            "compiles": not errors,
            "warnings": warnings,
            "timestamp": datetime.now().isoformat()
        }
        
    def update_manifest(self):
        """Update swarm manifest with current state"""
        manifest_path = CELL0_ROOT / "system" / "swarm-manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            manifest["last_coordinator_ping"] = datetime.now().isoformat()
            manifest["iteration"] = self.iteration
            manifest["agent_status"] = self.agent_status
            
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
                
    def coordinate(self):
        """Main coordination loop - run forever"""
        print(f"♾️ KULLU Coordinator starting...")
        
        while True:
            self.iteration += 1
            
            # Read agent statuses
            self.read_agent_status()
            
            # Check kernel health
            kernel_health = self.check_kernel_health()
            
            # Update manifest
            self.update_manifest()
            
            # Log status
            print(f"\n[Iteration {self.iteration}] {datetime.now().isoformat()}")
            print(f"  Kernel: {kernel_health['warnings']} warnings, compiles={kernel_health['compiles']}")
            print(f"  Agents: {len(self.agent_status)} reporting")
            
            # Sleep before next iteration
            time.sleep(60)  # 1 minute between checks

if __name__ == "__main__":
    coordinator = KulluCoordinator()
    coordinator.coordinate()
